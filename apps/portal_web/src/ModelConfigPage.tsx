import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { apiJson } from './apiUtils';
import { Save, RefreshCw, Zap, Server, AlertCircle, Check } from 'lucide-react';
import './model-config.css';

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
    <div className="page-container model-config-container">
      <header className="page-header model-config-header">
        <h1>模型配置</h1>
        <p className="page-description">配置本地或云端 LLM 模型</p>
      </header>

      {/* Provider Type Selection */}
      <div className="provider-type-grid">
        <div
          className={`provider-card ${isLocal ? 'active' : ''}`}
          onClick={() => {
            setIsLocal(true);
            handleProviderChange('ollama');
          }}
        >
          <div className="provider-card-header">
            <div className="provider-icon">
              <Server size={24} color={isLocal ? '#fff' : '#6b7280'} />
            </div>
            <div>
              <h3 className="provider-card-title">本地模型</h3>
              {isLocal && <Check size={16} color="#3b82f6" className="provider-check-icon" />}
            </div>
          </div>
          <p className="provider-card-description">
            使用 Ollama、LM Studio 等本地运行的模型，无需 API Key
          </p>
        </div>

        <div
          className={`provider-card ${!isLocal ? 'active' : ''}`}
          onClick={() => {
            setIsLocal(false);
            handleProviderChange('openai');
          }}
        >
          <div className="provider-card-header">
            <div className="provider-icon">
              <Zap size={24} color={!isLocal ? '#fff' : '#6b7280'} />
            </div>
            <div>
              <h3 className="provider-card-title">云端模型</h3>
              {!isLocal && <Check size={16} color="#3b82f6" className="provider-check-icon" />}
            </div>
          </div>
          <p className="provider-card-description">
            使用 OpenAI、Anthropic 等云端 API，需要 API Key
          </p>
        </div>
      </div>

      {/* Configuration Form */}
      <div className="card model-config-form">
        {isLocal && (
          <div className="model-config-alert">
            <div className="model-config-alert-content">
              <AlertCircle size={20} color="#0284c7" className="model-config-alert-icon" />
              <div className="model-config-alert-text">
                <strong>提示：</strong>请确保 {currentProvider?.label} 已在本地运行。
                {config.provider === 'ollama' && (
                  <div className="model-config-alert-command">
                    运行命令：<code>ollama serve</code>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="model-config-form-group">
          <label className="model-config-label">
            Provider
          </label>
          <select
            value={config.provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            className="model-config-select"
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

        <div className="model-config-form-group">
          <label className="model-config-label">
            Model
          </label>
          <input
            type="text"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            placeholder="输入模型名称"
            list="model-suggestions"
            className="model-config-input"
          />
          <datalist id="model-suggestions">
            {suggestedModels.map(model => (
              <option key={model} value={model} />
            ))}
          </datalist>
          {suggestedModels.length > 0 && (
            <div className="model-suggestions">
              <span className="model-suggestions-label">常用模型：</span>
              {suggestedModels.slice(0, 4).map((model, idx) => (
                <span key={model}>
                  <button
                    type="button"
                    onClick={() => setConfig({ ...config, model })}
                    className="model-suggestion-button"
                    style={{ marginLeft: idx === 0 ? '0.5rem' : 0 }}
                  >
                    {model}
                  </button>
                  {idx < Math.min(suggestedModels.length, 4) - 1 && ', '}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="model-config-form-group">
          <label className="model-config-label">
            Base URL
          </label>
          <input
            type="text"
            value={config.base_url || ''}
            onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
            placeholder={currentProvider?.defaultUrl}
            className="model-config-input"
          />
        </div>

        {currentProvider?.needsKey && (
          <div className="model-config-form-group">
            <label className="model-config-label">
              API Key
            </label>
            <input
              type="password"
              value={config.api_key || ''}
              onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
              placeholder="sk-..."
              className="model-config-input"
            />
          </div>
        )}

        <div className="model-config-two-col">
          <div className="model-config-form-group">
            <label className="model-config-label">
              Temperature
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={config.temperature || 0.7}
              onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
              className="model-config-input"
            />
            <small className="model-config-hint">
              控制输出随机性 (0-2)
            </small>
          </div>

          <div className="model-config-form-group">
            <label className="model-config-label">
              Max Tokens
            </label>
            <input
              type="number"
              step="100"
              min="100"
              max="32000"
              value={config.max_tokens || 2000}
              onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) })}
              className="model-config-input"
            />
            <small className="model-config-hint">
              最大输出长度
            </small>
          </div>
        </div>

        <div className="model-config-actions">
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="model-config-button-primary"
          >
            <Save size={16} />
            {saveMutation.isPending ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={() => configQuery.refetch()}
            disabled={configQuery.isRefetching}
            className="model-config-button-secondary"
          >
            <RefreshCw size={16} />
            刷新
          </button>
        </div>
      </div>
    </div>
  );
}
