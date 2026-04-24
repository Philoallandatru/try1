import React, { useState, useEffect } from 'react';
import { Upload, Database, FileText, Settings, Plus, Trash2, Edit, Download, Search } from 'lucide-react';
import { fetchWithRetry } from './apiUtils';

interface DataSource {
  id: string;
  name: string;
  type: 'file' | 'jira' | 'confluence';
  status: 'active' | 'pending' | 'error';
  itemCount?: number;
  lastSync?: string;
  config?: any;
}

interface FileUpload {
  file: File;
  progress: number;
  status: 'uploading' | 'processing' | 'complete' | 'error';
  id?: string;
}

export default function DataSourcesPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'files' | 'jira' | 'confluence'>('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState<'file' | 'jira' | 'confluence'>('file');

  useEffect(() => {
    loadDataSources();
  }, []);

  const loadDataSources = async () => {
    try {
      const response = await fetchWithRetry('/api/workspace/sources');
      setDataSources(response.sources || []);
    } catch (error) {
      console.error('Failed to load data sources:', error);
    }
  };

  const handleFileUpload = async (files: FileList) => {
    const newUploads: FileUpload[] = Array.from(files).map(file => ({
      file,
      progress: 0,
      status: 'uploading'
    }));

    setUploads(prev => [...prev, ...newUploads]);

    for (let i = 0; i < newUploads.length; i++) {
      const upload = newUploads[i];
      const formData = new FormData();
      formData.append('file', upload.file);

      try {
        const response = await fetch('/api/documents/upload', {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const result = await response.json();
          setUploads(prev => prev.map(u =>
            u.file === upload.file
              ? { ...u, status: 'complete', id: result.document_id }
              : u
          ));
          loadDataSources();
        } else {
          throw new Error('Upload failed');
        }
      } catch (error) {
        setUploads(prev => prev.map(u =>
          u.file === upload.file
            ? { ...u, status: 'error' }
            : u
        ));
      }
    }
  };

  const handleAddJira = async (config: any) => {
    try {
      await fetchWithRetry('/api/workspace/sources', {
        method: 'POST',
        body: JSON.stringify({
          type: 'jira',
          config
        })
      });
      loadDataSources();
      setShowAddModal(false);
    } catch (error) {
      console.error('Failed to add Jira source:', error);
    }
  };

  const handleAddConfluence = async (config: any) => {
    try {
      await fetchWithRetry('/api/workspace/sources', {
        method: 'POST',
        body: JSON.stringify({
          type: 'confluence',
          config
        })
      });
      loadDataSources();
      setShowAddModal(false);
    } catch (error) {
      console.error('Failed to add Confluence source:', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetchWithRetry(`/api/workspace/sources/${id}`, {
        method: 'DELETE'
      });
      loadDataSources();
    } catch (error) {
      console.error('Failed to delete source:', error);
    }
  };

  const filteredSources = dataSources.filter(source =>
    activeTab === 'all' || source.type === activeTab
  );

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Data Sources</h1>
          <p className="text-gray-600">Manage all your data sources in one place</p>
        </div>

        {/* Quick Upload Zone */}
        <div className="mb-6 bg-white rounded-lg border-2 border-dashed border-gray-300 p-8 text-center hover:border-blue-500 transition-colors">
          <input
            type="file"
            multiple
            onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
            className="hidden"
            id="file-upload"
            accept=".pdf,.doc,.docx,.txt"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-lg font-medium text-gray-700 mb-2">Drop files here or click to upload</p>
            <p className="text-sm text-gray-500">Supports PDF, DOC, DOCX, TXT</p>
          </label>
        </div>

        {/* Active Uploads */}
        {uploads.length > 0 && (
          <div className="mb-6 bg-white rounded-lg shadow p-4">
            <h3 className="font-medium mb-3">Uploading Files</h3>
            {uploads.map((upload, idx) => (
              <div key={idx} className="flex items-center gap-3 mb-2">
                <FileText className="w-5 h-5 text-gray-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium">{upload.file.name}</p>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div
                      className={`h-2 rounded-full ${
                        upload.status === 'complete' ? 'bg-green-500' :
                        upload.status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                      }`}
                      style={{ width: upload.status === 'complete' ? '100%' : '50%' }}
                    />
                  </div>
                </div>
                <span className="text-xs text-gray-500">{upload.status}</span>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-2 border-b">
          {[
            { key: 'all', label: 'All Sources', icon: Database },
            { key: 'files', label: 'Files', icon: FileText },
            { key: 'jira', label: 'Jira', icon: Database },
            { key: 'confluence', label: 'Confluence', icon: Database }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Add Source Button */}
        <div className="mb-6 flex justify-between items-center">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search data sources..."
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            Add Source
          </button>
        </div>

        {/* Data Sources Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSources.map(source => (
            <div key={source.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {source.type === 'file' && <FileText className="w-8 h-8 text-blue-500" />}
                  {source.type === 'jira' && <Database className="w-8 h-8 text-blue-600" />}
                  {source.type === 'confluence' && <Database className="w-8 h-8 text-purple-600" />}
                  <div>
                    <h3 className="font-semibold text-gray-900">{source.name}</h3>
                    <span className="text-xs text-gray-500 uppercase">{source.type}</span>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  source.status === 'active' ? 'bg-green-100 text-green-800' :
                  source.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {source.status}
                </span>
              </div>

              <div className="space-y-2 mb-4">
                {source.itemCount !== undefined && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">{source.itemCount}</span> items
                  </p>
                )}
                {source.lastSync && (
                  <p className="text-xs text-gray-500">
                    Last synced: {new Date(source.lastSync).toLocaleDateString()}
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50 transition-colors">
                  <Edit className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(source.id)}
                  className="flex items-center justify-center gap-2 px-3 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {filteredSources.length === 0 && (
          <div className="text-center py-12">
            <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No data sources yet</h3>
            <p className="text-gray-600 mb-4">Get started by adding your first data source</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Add Data Source
            </button>
          </div>
        )}

        {/* Add Source Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b">
                <h2 className="text-2xl font-bold">Add Data Source</h2>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-3 gap-4 mb-6">
                  {[
                    { type: 'file', label: 'Files', icon: FileText },
                    { type: 'jira', label: 'Jira', icon: Database },
                    { type: 'confluence', label: 'Confluence', icon: Database }
                  ].map(option => (
                    <button
                      key={option.type}
                      onClick={() => setSelectedType(option.type as any)}
                      className={`p-4 border-2 rounded-lg flex flex-col items-center gap-2 transition-colors ${
                        selectedType === option.type
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <option.icon className="w-8 h-8" />
                      <span className="font-medium">{option.label}</span>
                    </button>
                  ))}
                </div>

                {selectedType === 'file' && (
                  <div className="text-center py-8">
                    <input
                      type="file"
                      multiple
                      onChange={(e) => {
                        if (e.target.files) {
                          handleFileUpload(e.target.files);
                          setShowAddModal(false);
                        }
                      }}
                      className="hidden"
                      id="modal-file-upload"
                    />
                    <label htmlFor="modal-file-upload" className="cursor-pointer">
                      <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-lg font-medium mb-2">Choose files to upload</p>
                      <p className="text-sm text-gray-500">PDF, DOC, DOCX, TXT</p>
                    </label>
                  </div>
                )}

                {selectedType === 'jira' && (
                  <div className="space-y-4">
                    <input
                      type="text"
                      placeholder="Jira URL (e.g., https://company.atlassian.net)"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                    <input
                      type="email"
                      placeholder="Email"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                    <input
                      type="password"
                      placeholder="API Token"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                    <textarea
                      placeholder="JQL Query (optional)"
                      className="w-full px-4 py-2 border rounded-lg"
                      rows={3}
                    />
                  </div>
                )}

                {selectedType === 'confluence' && (
                  <div className="space-y-4">
                    <input
                      type="text"
                      placeholder="Confluence URL"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                    <input
                      type="email"
                      placeholder="Email"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                    <input
                      type="password"
                      placeholder="API Token"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                    <input
                      type="text"
                      placeholder="Space Key (optional)"
                      className="w-full px-4 py-2 border rounded-lg"
                    />
                  </div>
                )}
              </div>

              <div className="p-6 border-t flex justify-end gap-3">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Add Source
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
