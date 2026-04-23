import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { apiJson } from './apiUtils';
import { Save, RefreshCw, Zap, Server, AlertCircle, Check } from 'lucide-react';

const modelConfigSchema = z.object({
  provider: z.string(),
  model: z.string(),
  api_key: z.string().optional(),
  base_url: z.string().optional(),
  temperature: z.number().optional(),
  max_tokens: z.number().optional(),
});

const configResponseSchema = z.object({
  config: modelConfigSchema,
});

type ModelConfig = z.infer<typeof modelConfigSchema>;

const LOCAL_PROVIDERS = [
  { value: 'ollama', label: 'Ollama', defaultUrl: 'http://localhost:11434/v1', needsKey: false },
  { value: 'lm-studio', label: 'LM Studio', defaultUrl: 'http://localhost:1234/v1', needsKey: false },
  { value: 'vllm', label: 'vLLM', defaultUrl: 'http://localhost:8000/v1', needsKey: false },
  { value: 'text-generation-webui', label: 'Text Generation WebUI', defaultUrl: 'http://localhost:5000/v1', needsKey: false },
];

const CLOUD_PROVIDERS = [
  { value: 'openai', label: 'OpenAI', defaultUrl: 'https://api.openai.com/v1', needsKey: true },
  { value: 'anthropic', label: 'Anthropic', defaultUrl: 'https://api.anthropic.com/v1', needsKey: true },
  { value: 'azure', label: 'Azure OpenAI', defaultUrl: '', needsKey: true },
];

const POPULAR_MODELS = {
  ollama: ['llama3.2', 'qwen2.5', 'deepseek-r1', 'mistral', 'phi3', 'gemma2'],
  'lm-studio': ['llama-3.2-3b', 'qwen2.5-7b', 'mistral-7b', 'phi-3-mini'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
};

export function ModelConfigPage() {
  const queryClient = useQueryClient();

  const [config, setConfig] = useState<ModelConfig>({
    provider: 'ollama',
    model: 'llama3.2',
    api_key: '',
    base_url: 'http://localhost:11434/v1',
    temperature: 0.7,
    max_tokens: 2000,
  });

  const [isLocal, setIsLocal] = useState(true);

  const configQuery = useQuery({
    queryKey: ['model-config'],
    queryFn: () => apiJson('/api/model-config', configResponseSchema),
  });

  React.useEffect(() => {
    if (configQuery.data) {
      setConfig(configQuery.data.config);
      const provider = LOCAL_PROVIDERS.find(p => p.value === configQuery.data.config.provider);
      setIsLocal(!!provider);
    }
  }, [configQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (newConfig: ModelConfig) =>
      apiJson('/api/model-config', configResponseSchema, {
        method: 'POST',
        body: JSON.stringify(newConfig),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-config'] });
      alert('配置已保存');
    },
  });

  const handleProviderChange = (provider: string) => {
    const providerInfo = [...LOCAL_PROVIDERS, ...CLOUD_PROVIDERS].find(p => p.value === provider);
    const isLocalProvider = LOCAL_PROVIDERS.some(p => p.value === provider);

    setIsLocal(isLocalProvider);
    setConfig({
      ...config,
      provider,
      base_url: providerInfo?.defaultUrl || '',
      api_key: providerInfo?.needsKey ? config.api_key : '',
      model: POPULAR_MODELS[provider as keyof typeof POPULAR_MODELS]?.[0] || '',
    });
  };

  const handleSave = () => {
    saveMutation.mutate(config);
  };

  const currentProvider = [...LOCAL_PROVIDERS, ...CLOUD_PROVIDERS].find(p => p.value === config.provider);
  const suggestedModels = POPULAR_MODELS[config.provider as keyof typeof POPULAR_MODELS] || [];

  return (
    <div className="page-container" style={{ maxWidth: '900px', margin: '0 auto' }}>
      <header className="page-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '0.5rem' }}>模型配置</h1>
        <p className="page-description" style={{ fontSize: '1rem', color: '#6b7280' }}>配置本地或云端 LLM 模型</p>
      </header>

      {/* Provider Type Selection */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div
          style={{
            cursor: 'pointer',
            padding: '1.5rem',
            borderRadius: '12px',
            border: isLocal ? '2px solid #3b82f6' : '2px solid #e5e7eb',
            backgroundColor: isLocal ? '#eff6ff' : '#fff',
            transition: 'all 0.2s ease',
            boxShadow: isLocal ? '0 4px 12px rgba(59, 130, 246, 0.15)' : '0 1px 3px rgba(0, 0, 0, 0.1)',
          }}
          onClick={() => {
            setIsLocal(true);
            handleProviderChange('ollama');
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '10px',
              backgroundColor: isLocal ? '#3b82f6' : '#f3f4f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Server size={24} color={isLocal ? '#fff' : '#6b7280'} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: '600' }}>本地模型</h3>
              {isLocal && <Check size={16} color="#3b82f6" style={{ marginTop: '2px' }} />}
            </div>
          </div>
          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0, lineHeight: '1.5' }}>
            使用 Ollama、LM Studio 等本地运行的模型，无需 API Key
          </p>
        </div>

        <div
          style={{
            cursor: 'pointer',
            padding: '1.5rem',
            borderRadius: '12px',
            border: !isLocal ? '2px solid #3b82f6' : '2px solid #e5e7eb',
            backgroundColor: !isLocal ? '#eff6ff' : '#fff',
            transition: 'all 0.2s ease',
            boxShadow: !isLocal ? '0 4px 12px rgba(59, 130, 246, 0.15)' : '0 1px 3px rgba(0, 0, 0, 0.1)',
          }}
          onClick={() => {
            setIsLocal(false);
            handleProviderChange('openai');
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '10px',
              backgroundColor: !isLocal ? '#3b82f6' : '#f3f4f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Zap size={24} color={!isLocal ? '#fff' : '#6b7280'} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: '600' }}>云端模型</h3>
              {!isLocal && <Check size={16} color="#3b82f6" style={{ marginTop: '2px' }} />}
            </div>
          </div>
          <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: 0, lineHeight: '1.5' }}>
            使用 OpenAI、Anthropic 等云端 API，需要 API Key
          </p>
        </div>
      </div>

      {/* Configuration Form */}
      <div className="card" style={{
        padding: '2rem',
        borderRadius: '12px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}>
        {isLocal && (
          <div style={{
            padding: '1rem',
            backgroundColor: '#f0f9ff',
            border: '1px solid #bae6fd',
            borderRadius: '8px',
            marginBottom: '1.5rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'start', gap: '0.75rem' }}>
              <AlertCircle size={20} color="#0284c7" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div style={{ fontSize: '0.875rem', color: '#0c4a6e', lineHeight: '1.6' }}>
                <strong>提示：</strong>请确保 {currentProvider?.label} 已在本地运行。
                {config.provider === 'ollama' && (
                  <div style={{ marginTop: '0.5rem' }}>
                    运行命令：<code style={{
                      backgroundColor: '#fff',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                    }}>ollama serve</code>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="form-group" style={{ marginBottom: '1.5rem' }}>
          <label style={{
            display: 'block',
            fontSize: '0.875rem',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '0.5rem'
          }}>
            Provider
          </label>
          <select
            value={config.provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            style={{
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: '#fff',
              cursor: 'pointer',
            }}
          >
            <optgroup label="本地模型">
              {LOCAL_PROVIDERS.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </optgroup>
            <optgroup label="云端模型">
              {CLOUD_PROVIDERS.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </optgroup>
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: '1.5rem' }}>
          <label style={{
            display: 'block',
            fontSize: '0.875rem',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '0.5rem'
          }}>
            Model
          </label>
          <input
            type="text"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            placeholder="输入模型名称"
            list="model-suggestions"
            style={{
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
            }}
          />
          <datalist id="model-suggestions">
            {suggestedModels.map(model => (
              <option key={model} value={model} />
            ))}
          </datalist>
          {suggestedModels.length > 0 && (
            <div style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>
              <span style={{ fontWeight: '500' }}>常用模型：</span>
              {suggestedModels.slice(0, 4).map((model, idx) => (
                <span key={model}>
                  <button
                    type="button"
                    onClick={() => setConfig({ ...config, model })}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#3b82f6',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      padding: 0,
                      marginLeft: idx === 0 ? '0.5rem' : 0,
                      fontSize: '0.875rem',
                    }}
                  >
                    {model}
                  </button>
                  {idx < Math.min(suggestedModels.length, 4) - 1 && ', '}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="form-group" style={{ marginBottom: '1.5rem' }}>
          <label style={{
            display: 'block',
            fontSize: '0.875rem',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '0.5rem'
          }}>
            Base URL
          </label>
          <input
            type="text"
            value={config.base_url || ''}
            onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
            placeholder={currentProvider?.defaultUrl}
            style={{
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontFamily: 'monospace',
            }}
          />
        </div>

        {currentProvider?.needsKey && (
          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              API Key
            </label>
            <input
              type="password"
              value={config.api_key || ''}
              onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
              placeholder="sk-..."
              style={{
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontFamily: 'monospace',
              }}
            />
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div className="form-group">
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Temperature
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={config.temperature || 0.7}
              onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
              style={{
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
              }}
            />
            <small style={{ color: '#6b7280', fontSize: '0.75rem', marginTop: '0.25rem', display: 'block' }}>
              控制输出随机性 (0-2)
            </small>
          </div>

          <div className="form-group">
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '0.5rem'
            }}>
              Max Tokens
            </label>
            <input
              type="number"
              step="100"
              min="100"
              max="32000"
              value={config.max_tokens || 2000}
              onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) })}
              style={{
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
              }}
            />
            <small style={{ color: '#6b7280', fontSize: '0.75rem', marginTop: '0.25rem', display: 'block' }}>
              最大输出长度
            </small>
          </div>
        </div>

        <div style={{
          display: 'flex',
          gap: '0.75rem',
          marginTop: '2rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e5e7eb',
        }}>
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1.5rem',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#fff',
              backgroundColor: saveMutation.isPending ? '#9ca3af' : '#3b82f6',
              border: 'none',
              borderRadius: '8px',
              cursor: saveMutation.isPending ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              if (!saveMutation.isPending) {
                e.currentTarget.style.backgroundColor = '#2563eb';
              }
            }}
            onMouseLeave={(e) => {
              if (!saveMutation.isPending) {
                e.currentTarget.style.backgroundColor = '#3b82f6';
              }
            }}
          >
            <Save size={16} />
            {saveMutation.isPending ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={() => configQuery.refetch()}
            disabled={configQuery.isRefetching}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1.5rem',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              backgroundColor: '#fff',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              cursor: configQuery.isRefetching ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              if (!configQuery.isRefetching) {
                e.currentTarget.style.backgroundColor = '#f9fafb';
              }
            }}
            onMouseLeave={(e) => {
              if (!configQuery.isRefetching) {
                e.currentTarget.style.backgroundColor = '#fff';
              }
            }}
          >
            <RefreshCw size={16} />
            刷新
          </button>
        </div>
      </div>
    </div>
  );
}
