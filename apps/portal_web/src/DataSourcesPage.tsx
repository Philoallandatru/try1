import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import {
  Database,
  FileText,
  Plus,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Loader2,
  X,
  Upload,
  ExternalLink
} from 'lucide-react';
import { apiJson } from './apiUtils';

// Schemas
const sourceSchema = z.object({
  name: z.string(),
  kind: z.string(),
  connector_type: z.string(),
  mode: z.string().optional(),
  enabled: z.boolean().optional(),
  status: z.string().optional(),
  document_count: z.number().optional(),
  last_refresh: z.string().nullable().optional(),
});

const sourcesResponseSchema = z.object({
  sources: z.array(sourceSchema),
});

type Source = z.infer<typeof sourceSchema>;

interface DataSourcesPageProps {
  workspaceDir?: string;
}

export default function DataSourcesPage({ workspaceDir = '.tmp/workspace' }: DataSourcesPageProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState<'jira' | 'confluence'>('jira');
  const queryClient = useQueryClient();

  const sources = useQuery({
    queryKey: ['sources', workspaceDir],
    queryFn: () => apiJson(`/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`, sourcesResponseSchema),
    enabled: Boolean(workspaceDir),
  });

  const deleteSource = useMutation({
    mutationFn: (name: string) =>
      apiJson(`/api/workspace/sources/${name}`, z.unknown(), {
        method: 'DELETE',
        body: JSON.stringify({ workspace_dir: workspaceDir }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] });
    },
  });

  const sourcesData = sources.data?.sources || [];
  const jiraSources = sourcesData.filter(s => s.kind === 'jira');
  const confluenceSources = sourcesData.filter(s => s.kind === 'confluence');
  const fileSources = sourcesData.filter(s => s.kind === 'pdf');

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Data Sources</p>
          <h2>数据源管理</h2>
          <p>管理 Jira、Confluence 和文件数据源</p>
        </div>

        <div className="row-actions">
          <button
            className="primary-button"
            onClick={() => {
              setSelectedType('jira');
              setShowAddModal(true);
            }}
          >
            <Plus size={16} /> 添加 Jira
          </button>
          <button
            className="primary-button"
            onClick={() => {
              setSelectedType('confluence');
              setShowAddModal(true);
            }}
          >
            <Plus size={16} /> 添加 Confluence
          </button>
          <button
            onClick={() => sources.refetch()}
            disabled={sources.isLoading}
          >
            <RefreshCw size={16} className={sources.isLoading ? 'spin' : ''} />
            刷新
          </button>
        </div>

        {sources.isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={32} className="spin text-blue-500" />
          </div>
        )}

        {sources.error && (
          <div className="error" role="alert">
            <AlertCircle size={16} /> 加载失败: {String(sources.error)}
          </div>
        )}

        {!sources.isLoading && !sources.error && (
          <div className="space-y-6">
            {/* Jira Sources */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Database size={20} className="text-blue-500" />
                Jira 数据源 ({jiraSources.length})
              </h3>
              {jiraSources.length === 0 ? (
                <div className="empty-state">
                  <Database size={48} className="text-gray-300" />
                  <p>暂无 Jira 数据源</p>
                </div>
              ) : (
                <div className="config-list">
                  {jiraSources.map((source) => (
                    <SourceCard
                      key={source.name}
                      source={source}
                      onDelete={() => deleteSource.mutate(source.name)}
                      isDeleting={deleteSource.isPending}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Confluence Sources */}
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <FileText size={20} className="text-green-500" />
                Confluence 数据源 ({confluenceSources.length})
              </h3>
              {confluenceSources.length === 0 ? (
                <div className="empty-state">
                  <FileText size={48} className="text-gray-300" />
                  <p>暂无 Confluence 数据源</p>
                </div>
              ) : (
                <div className="config-list">
                  {confluenceSources.map((source) => (
                    <SourceCard
                      key={source.name}
                      source={source}
                      onDelete={() => deleteSource.mutate(source.name)}
                      isDeleting={deleteSource.isPending}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* File Sources */}
            {fileSources.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Upload size={20} className="text-purple-500" />
                  文件数据源 ({fileSources.length})
                </h3>
                <div className="config-list">
                  {fileSources.map((source) => (
                    <SourceCard
                      key={source.name}
                      source={source}
                      onDelete={() => deleteSource.mutate(source.name)}
                      isDeleting={deleteSource.isPending}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {deleteSource.error && (
          <div className="error mt-4">
            <AlertCircle size={16} /> 删除失败: {String(deleteSource.error)}
          </div>
        )}
      </div>

      <aside className="side-panel">
        <h3>数据源说明</h3>
        <div className="guide-content">
          <div className="guide-section">
            <strong>Jira</strong>
            <p>连接 Jira 实例获取 Issue 数据</p>
          </div>
          <div className="guide-section">
            <strong>Confluence</strong>
            <p>连接 Confluence 获取文档和页面</p>
          </div>
          <div className="guide-section">
            <strong>测试服务器</strong>
            <p>Mock Server: http://localhost:8888</p>
            <p>Token: mock-token</p>
          </div>
        </div>
      </aside>

      {showAddModal && (
        <AddSourceModal
          workspaceDir={workspaceDir}
          type={selectedType}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] });
          }}
        />
      )}
    </section>
  );
}

function SourceCard({
  source,
  onDelete,
  isDeleting
}: {
  source: Source;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  return (
    <div className="config-item">
      <div className="config-item-header">
        <div className="config-item-title">
          <Database size={18} />
          <strong>{source.name}</strong>
          <span className="badge">{source.kind}</span>
          <span className={`status-badge ${source.enabled !== false ? 'active' : 'inactive'}`}>
            {source.enabled !== false ? 'Enabled' : 'Disabled'}
          </span>
        </div>
        <div className="config-item-actions">
          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="danger"
            >
              <Trash2 size={14} /> 删除
            </button>
          ) : (
            <>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
              >
                取消
              </button>
              <button
                onClick={onDelete}
                disabled={isDeleting}
                className="danger"
              >
                {isDeleting ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />}
                确认删除
              </button>
            </>
          )}
        </div>
      </div>
      <div className="config-item-details">
        <div className="detail-row">
          <span>Mode:</span>
          <span>{source.mode || 'live'}</span>
        </div>
        <div className="detail-row">
          <span>Connector:</span>
          <span>{source.connector_type}</span>
        </div>
        {source.document_count !== undefined && (
          <div className="detail-row">
            <span>Documents:</span>
            <span>{source.document_count}</span>
          </div>
        )}
        {source.last_refresh && (
          <div className="detail-row">
            <span>Last Refresh:</span>
            <span>{new Date(source.last_refresh).toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function AddSourceModal({
  workspaceDir,
  type,
  onClose,
  onSuccess
}: {
  workspaceDir: string;
  type: 'jira' | 'confluence';
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: '',
    base_url: 'http://localhost:8888',
    token: 'mock-token',
    project_key: type === 'jira' ? 'TEST' : '',
    space_key: type === 'confluence' ? 'TEST' : '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const createSource = useMutation({
    mutationFn: (data: any) => {
      const payload: any = {
        workspace_dir: workspaceDir,
        name: data.name,
        connector_type: type === 'jira' ? 'jira.atlassian_api' : 'confluence.atlassian_api',
        base_url: data.base_url,
        token: data.token,
        policies: ['team:ssd', 'public'],
        enabled: true,
      };

      if (type === 'jira' && data.project_key) {
        payload.project_key = data.project_key;
      }
      if (type === 'confluence' && data.space_key) {
        payload.space_key = data.space_key;
      }

      return apiJson('/api/workspace/sources', z.unknown(), {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '名称不能为空';
    }
    if (!formData.base_url.trim()) {
      newErrors.base_url = 'URL 不能为空';
    }
    if (!formData.token.trim()) {
      newErrors.token = 'Token 不能为空';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    createSource.mutate(formData);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>添加 {type === 'jira' ? 'Jira' : 'Confluence'} 数据源</h3>
          <button onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form" noValidate>
          <label>
            数据源名称 *
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder={`my_${type}`}
            />
            {errors.name && <span className="error-text">{errors.name}</span>}
          </label>

          <label>
            Base URL *
            <input
              type="url"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder="http://localhost:8888"
            />
            {errors.base_url && <span className="error-text">{errors.base_url}</span>}
            <small className="text-gray-500">Mock Server: http://localhost:8888</small>
          </label>

          <label>
            API Token *
            <input
              type="text"
              value={formData.token}
              onChange={(e) => setFormData({ ...formData, token: e.target.value })}
              placeholder="mock-token"
            />
            {errors.token && <span className="error-text">{errors.token}</span>}
            <small className="text-gray-500">使用 "mock-token" 连接测试服务器</small>
          </label>

          {type === 'jira' && (
            <label>
              Project Key
              <input
                type="text"
                value={formData.project_key}
                onChange={(e) => setFormData({ ...formData, project_key: e.target.value })}
                placeholder="TEST"
              />
              <small className="text-gray-500">可选：指定 Jira 项目</small>
            </label>
          )}

          {type === 'confluence' && (
            <label>
              Space Key
              <input
                type="text"
                value={formData.space_key}
                onChange={(e) => setFormData({ ...formData, space_key: e.target.value })}
                placeholder="TEST"
              />
              <small className="text-gray-500">可选：指定 Confluence 空间</small>
            </label>
          )}

          {createSource.error && (
            <div className="error">
              <AlertCircle size={16} /> {String(createSource.error)}
            </div>
          )}

          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={createSource.isPending}>
              取消
            </button>
            <button type="submit" disabled={createSource.isPending} className="primary-button">
              {createSource.isPending ? (
                <><Loader2 size={16} className="spin" /> 创建中...</>
              ) : (
                <><Plus size={16} /> 创建数据源</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
