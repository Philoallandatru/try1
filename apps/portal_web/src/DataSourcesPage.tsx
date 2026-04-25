import React, { useState, useEffect } from 'react';
import { Upload, Database, FileText, Settings, Plus, Trash2, Edit, Download, Search, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
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

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface FormData {
  url: string;
  email: string;
  token: string;
  jql?: string;
  spaceKey?: string;
}

export default function DataSourcesPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'files' | 'jira' | 'confluence'>('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState<'file' | 'jira' | 'confluence'>('file');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    url: '',
    email: '',
    token: '',
    jql: '',
    spaceKey: ''
  });
  const [formErrors, setFormErrors] = useState<Partial<FormData>>({});

  useEffect(() => {
    loadDataSources();
  }, []);

  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const loadDataSources = async () => {
    setIsLoading(true);
    try {
      const response = await fetchWithRetry('/api/workspace/sources');
      setDataSources(response.sources || []);
    } catch (error) {
      console.error('Failed to load data sources:', error);
      showToast('error', '加载数据源失败');
    } finally {
      setIsLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const errors: Partial<FormData> = {};

    if (!formData.url.trim()) {
      errors.url = 'URL 不能为空';
    } else if (!formData.url.startsWith('http://') && !formData.url.startsWith('https://')) {
      errors.url = 'URL 必须以 http:// 或 https:// 开头';
    }

    if (!formData.email.trim()) {
      errors.email = '邮箱不能为空';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = '邮箱格式不正确';
    }

    if (!formData.token.trim()) {
      errors.token = 'API Token 不能为空';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const resetForm = () => {
    setFormData({
      url: '',
      email: '',
      token: '',
      jql: '',
      spaceKey: ''
    });
    setFormErrors({});
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
    if (!validateForm()) {
      showToast('error', '请填写所有必填字段');
      return;
    }

    setIsSubmitting(true);
    try {
      await fetchWithRetry('/api/workspace/sources', {
        method: 'POST',
        body: JSON.stringify({
          type: 'jira',
          config: {
            url: formData.url,
            email: formData.email,
            token: formData.token,
            jql: formData.jql
          }
        })
      });
      showToast('success', 'Jira 数据源添加成功');
      loadDataSources();
      setShowAddModal(false);
      resetForm();
    } catch (error) {
      console.error('Failed to add Jira source:', error);
      showToast('error', '添加 Jira 数据源失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddConfluence = async (config: any) => {
    if (!validateForm()) {
      showToast('error', '请填写所有必填字段');
      return;
    }

    setIsSubmitting(true);
    try {
      await fetchWithRetry('/api/workspace/sources', {
        method: 'POST',
        body: JSON.stringify({
          type: 'confluence',
          config: {
            url: formData.url,
            email: formData.email,
            token: formData.token,
            spaceKey: formData.spaceKey
          }
        })
      });
      showToast('success', 'Confluence 数据源添加成功');
      loadDataSources();
      setShowAddModal(false);
      resetForm();
    } catch (error) {
      console.error('Failed to add Confluence source:', error);
      showToast('error', '添加 Confluence 数据源失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    setIsSubmitting(true);
    try {
      await fetchWithRetry(`/api/workspace/sources/${id}`, {
        method: 'DELETE'
      });
      showToast('success', '数据源删除成功');
      loadDataSources();
      setDeleteConfirm(null);
    } catch (error) {
      console.error('Failed to delete source:', error);
      showToast('error', '删除数据源失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = () => {
    if (selectedType === 'jira') {
      handleAddJira(formData);
    } else if (selectedType === 'confluence') {
      handleAddConfluence(formData);
    }
  };

  const filteredSources = dataSources.filter(source => {
    const matchesTab = activeTab === 'all' || source.type === activeTab;
    const matchesSearch = !searchQuery ||
      source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      source.type.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  return (
    <div className="page-container" style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border ${
              toast.type === 'success' ? 'bg-green-50 border-green-200 text-green-800' :
              toast.type === 'error' ? 'bg-red-50 border-red-200 text-red-800' :
              'bg-blue-50 border-blue-200 text-blue-800'
            } animate-slide-in`}
          >
            {toast.type === 'success' && <CheckCircle className="w-5 h-5" />}
            {toast.type === 'error' && <AlertCircle className="w-5 h-5" />}
            <span className="font-medium">{toast.message}</span>
            <button
              onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
              className="ml-2 hover:opacity-70"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="page-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '0.5rem' }}>数据源管理</h1>
        <p className="page-description" style={{ fontSize: '1rem', color: '#6b7280' }}>统一管理文件、Jira 和 Confluence 数据源</p>
      </header>

      <div>
        {/* Quick Upload Zone */}
        <div className="mb-6 bg-white rounded-xl border-2 border-dashed border-gray-300 p-8 text-center hover:border-blue-500 hover:bg-blue-50 transition-all cursor-pointer shadow-sm">
          <input
            type="file"
            multiple
            onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
            className="hidden"
            id="file-upload"
            accept=".pdf,.doc,.docx,.txt"
          />
          <label htmlFor="file-upload" className="cursor-pointer block">
            <Upload className="w-12 h-12 text-blue-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-gray-900 mb-2">拖拽文件到此处或点击上传</p>
            <p className="text-sm text-gray-500">支持 PDF, DOC, DOCX, TXT 格式</p>
          </label>
        </div>

        {/* Active Uploads */}
        {uploads.length > 0 && (
          <div className="mb-6 bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">正在上传</h3>
            {uploads.map((upload, idx) => (
              <div key={idx} className="flex items-center gap-3 mb-3 last:mb-0">
                <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{upload.file.name}</p>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        upload.status === 'complete' ? 'bg-green-500' :
                        upload.status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                      }`}
                      style={{ width: upload.status === 'complete' ? '100%' : '50%' }}
                    />
                  </div>
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded ${
                  upload.status === 'complete' ? 'bg-green-100 text-green-700' :
                  upload.status === 'error' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                }`}>
                  {upload.status === 'complete' ? '完成' : upload.status === 'error' ? '失败' : '上传中'}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-2 border-b border-gray-200">
          {[
            { key: 'all', label: '全部', icon: Database },
            { key: 'files', label: '文件', icon: FileText },
            { key: 'jira', label: 'Jira', icon: Database },
            { key: 'confluence', label: 'Confluence', icon: Database }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition-all ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Add Source Button */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4 justify-between items-stretch sm:items-center">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="搜索数据源..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 shadow-sm hover:shadow-md transition-all"
          >
            <Plus className="w-5 h-5" />
            添加数据源
          </button>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            <span className="ml-3 text-gray-600">加载中...</span>
          </div>
        ) : (
          <>
            {/* Data Sources Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{filteredSources.map(source => (
              <div key={source.id} className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      source.type === 'file' ? 'bg-blue-100' :
                      source.type === 'jira' ? 'bg-indigo-100' : 'bg-purple-100'
                    }`}>
                      {source.type === 'file' && <FileText className="w-6 h-6 text-blue-600" />}
                      {source.type === 'jira' && <Database className="w-6 h-6 text-indigo-600" />}
                      {source.type === 'confluence' && <Database className="w-6 h-6 text-purple-600" />}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{source.name}</h3>
                      <span className="text-xs text-gray-500 uppercase font-medium">{source.type}</span>
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                    source.status === 'active' ? 'bg-green-100 text-green-700' :
                    source.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {source.status === 'active' ? '活跃' : source.status === 'pending' ? '待处理' : '错误'}
                  </span>
                </div>

                <div className="space-y-2 mb-4 text-sm">
                  {source.itemCount !== undefined && (
                    <p className="text-gray-600">
                      <span className="font-semibold text-gray-900">{source.itemCount}</span> 个项目
                    </p>
                  )}
                  {source.lastSync && (
                    <p className="text-xs text-gray-500">
                      最后同步: {new Date(source.lastSync).toLocaleDateString('zh-CN')}
                    </p>
                  )}
                </div>

                <div className="flex gap-2">
                  <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
                    <Edit className="w-4 h-4" />
                    编辑
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(source.id)}
                    className="flex items-center justify-center gap-2 px-3 py-2 border border-red-300 text-red-600 font-medium rounded-lg hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}</div>

            {filteredSources.length === 0 && (
              <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
                <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {searchQuery ? '未找到匹配的数据源' : '暂无数据源'}
                </h3>
                <p className="text-gray-600 mb-6">
                  {searchQuery ? '尝试其他搜索词' : '开始添加您的第一个数据源'}
                </p>
                {!searchQuery && (
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 shadow-sm hover:shadow-md transition-all"
                  >
                    <Plus className="w-5 h-5" />
                    添加数据源
                  </button>
                )}
              </div>
            )}
          </>
        )}

        {/* Add Source Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-2xl font-bold text-gray-900">添加数据源</h2>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-3 gap-4 mb-6">
                  {[
                    { type: 'file', label: '文件', icon: FileText },
                    { type: 'jira', label: 'Jira', icon: Database },
                    { type: 'confluence', label: 'Confluence', icon: Database }
                  ].map(option => (
                    <button
                      key={option.type}
                      onClick={() => setSelectedType(option.type as any)}
                      className={`p-4 border-2 rounded-xl flex flex-col items-center gap-3 transition-all ${
                        selectedType === option.type
                          ? 'border-blue-500 bg-blue-50 shadow-md'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <option.icon className={`w-8 h-8 ${
                        selectedType === option.type ? 'text-blue-600' : 'text-gray-400'
                      }`} />
                      <span className={`font-semibold ${
                        selectedType === option.type ? 'text-blue-600' : 'text-gray-700'
                      }`}>{option.label}</span>
                    </button>
                  ))}
                </div>

                {selectedType === 'file' && (
                  <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
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
                    <label htmlFor="modal-file-upload" className="cursor-pointer block">
                      <Upload className="w-12 h-12 text-blue-500 mx-auto mb-4" />
                      <p className="text-lg font-semibold text-gray-900 mb-2">选择文件上传</p>
                      <p className="text-sm text-gray-500">PDF, DOC, DOCX, TXT</p>
                    </label>
                  </div>
                )}

                {selectedType === 'jira' && (
                  <div className="space-y-4">
                    <div>
                      <input
                        type="text"
                        placeholder="Jira URL (例如: https://company.atlassian.net)"
                        value={formData.url}
                        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formErrors.url ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.url && <p className="text-red-500 text-sm mt-1">{formErrors.url}</p>}
                    </div>
                    <div>
                      <input
                        type="email"
                        placeholder="邮箱"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formErrors.email ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.email && <p className="text-red-500 text-sm mt-1">{formErrors.email}</p>}
                    </div>
                    <div>
                      <input
                        type="password"
                        placeholder="API Token"
                        value={formData.token}
                        onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formErrors.token ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.token && <p className="text-red-500 text-sm mt-1">{formErrors.token}</p>}
                    </div>
                    <textarea
                      placeholder="JQL 查询 (可选)"
                      value={formData.jql}
                      onChange={(e) => setFormData({ ...formData, jql: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      rows={3}
                    />
                  </div>
                )}

                {selectedType === 'confluence' && (
                  <div className="space-y-4">
                    <div>
                      <input
                        type="text"
                        placeholder="Confluence URL"
                        value={formData.url}
                        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formErrors.url ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.url && <p className="text-red-500 text-sm mt-1">{formErrors.url}</p>}
                    </div>
                    <div>
                      <input
                        type="email"
                        placeholder="邮箱"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formErrors.email ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.email && <p className="text-red-500 text-sm mt-1">{formErrors.email}</p>}
                    </div>
                    <div>
                      <input
                        type="password"
                        placeholder="API Token"
                        value={formData.token}
                        onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                        className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          formErrors.token ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.token && <p className="text-red-500 text-sm mt-1">{formErrors.token}</p>}
                    </div>
                    <input
                      type="text"
                      placeholder="空间键 (可选)"
                      value={formData.spaceKey}
                      onChange={(e) => setFormData({ ...formData, spaceKey: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                )}
              </div>

              <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    resetForm();
                  }}
                  className="px-5 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                  disabled={isSubmitting}
                >
                  取消
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || selectedType === 'file'}
                  className="px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {isSubmitting ? '添加中...' : '添加数据源'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
              <div className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-3 bg-red-100 rounded-full">
                    <AlertCircle className="w-6 h-6 text-red-600" />
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">确认删除</h2>
                </div>
                <p className="text-gray-600 mb-6">
                  确定要删除此数据源吗？此操作无法撤销。
                </p>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    disabled={isSubmitting}
                    className="px-4 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={() => handleDelete(deleteConfirm)}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    {isSubmitting ? '删除中...' : '确认删除'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
