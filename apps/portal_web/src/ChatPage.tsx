import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { z } from 'zod';
import { apiJson } from './apiUtils';
import { Send, Loader2 } from 'lucide-react';

const workspacesSchema = z.object({
  workspaces: z.array(z.record(z.unknown())),
});

const chatResponseSchema = z.object({
  answer: z.string(),
  sources: z.array(z.object({
    title: z.string(),
    url: z.string().optional(),
    snippet: z.string().optional(),
  })).optional(),
});

type Message = {
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ title: string; url?: string; snippet?: string }>;
};

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [selectedSource, setSelectedSource] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const workspacesQuery = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const response = await fetch('/api/workspaces');
      const data = await response.json();
      console.log('RAW API RESPONSE:', JSON.stringify(data, null, 2));
      return data;
    },
  });

  const chatMutation = useMutation({
    mutationFn: (params: { question: string; source: string }) =>
      apiJson('/api/chat', chatResponseSchema, {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.answer, sources: data.sources },
      ]);
    },
  });

  const handleSend = () => {
    if (!input.trim() || !selectedSource) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    chatMutation.mutate({ question: input, source: selectedSource });
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const allSources = workspacesQuery.data?.workspaces
    .filter((ws) => ws.spec_asset)
    .map((ws) => ({
      workspace: ws.name,
      name: ws.spec_asset!.display_name,
      kind: 'spec',
    })) || [];

  // Debug logging
  console.log('ChatPage - workspacesQuery.data:', workspacesQuery.data);
  console.log('ChatPage - workspaces detail:', JSON.stringify(workspacesQuery.data?.workspaces, null, 2));
  console.log('ChatPage - allSources:', allSources);
  console.log('ChatPage - isLoading:', workspacesQuery.isLoading);
  console.log('ChatPage - error:', workspacesQuery.error);

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <header className="page-header">
        <h1>Chat</h1>
        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label>
            选择数据源
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              disabled={workspacesQuery.isLoading}
            >
              <option value="">-- 请选择 --</option>
              {allSources.map((source, idx) => (
                <option key={idx} value={`${source.workspace}/${source.name}`}>
                  {source.workspace} / {source.name} ({source.kind})
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '1rem', backgroundColor: '#f9fafb' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#6b7280', marginTop: '2rem' }}>
            选择数据源并开始提问
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: '1rem',
              padding: '1rem',
              borderRadius: '8px',
              backgroundColor: msg.role === 'user' ? '#dbeafe' : '#fff',
              border: msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
            }}
          >
            <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
              {msg.role === 'user' ? '你' : 'AI'}
            </div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280' }}>
                <strong>来源：</strong>
                {msg.sources.map((src, i) => (
                  <div key={i} style={{ marginTop: '0.25rem' }}>
                    {src.url ? (
                      <a href={src.url} target="_blank" rel="noopener noreferrer">
                        {src.title}
                      </a>
                    ) : (
                      src.title
                    )}
                    {src.snippet && <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{src.snippet}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {chatMutation.isPending && (
          <div style={{ textAlign: 'center', color: '#6b7280' }}>
            <Loader2 size={24} className="animate-spin" style={{ display: 'inline-block' }} />
            <span style={{ marginLeft: '0.5rem' }}>思考中...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input" style={{ padding: '1rem', borderTop: '1px solid #e5e7eb', backgroundColor: '#fff' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入你的问题..."
            disabled={!selectedSource || chatMutation.isPending}
            style={{ flex: 1, padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '4px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !selectedSource || chatMutation.isPending}
            className="button-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Send size={16} />
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
