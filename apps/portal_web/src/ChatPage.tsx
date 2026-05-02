import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { z } from 'zod';
import { apiJson } from './apiUtils';
import { Send, Loader2 } from 'lucide-react';
import './chat-page.css';

const workspaceSchema = z.object({
  name: z.string(),
  spec_asset: z.object({
    display_name: z.string(),
  }).optional(),
});

const workspacesSchema = z.object({
  workspaces: z.array(workspaceSchema),
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
      return workspacesSchema.parse(data);
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
    .filter((ws: z.infer<typeof workspaceSchema>) => ws.spec_asset)
    .map((ws: z.infer<typeof workspaceSchema>) => ({
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
    <div className="page-container chat-page-container">
      <header className="page-header">
        <h1>Chat</h1>
        <div className="form-group chat-source-selector">
          <label>
            选择数据源
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              disabled={workspacesQuery.isLoading}
            >
              <option value="">-- 请选择 --</option>
              {allSources.map((source: { workspace: string; name: string; kind: string }, idx: number) => (
                <option key={idx} value={`${source.workspace}/${source.name}`}>
                  {source.workspace} / {source.name} ({source.kind})
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="chat-messages chat-messages-container">
        {messages.length === 0 && (
          <div className="chat-empty-state">
            选择数据源并开始提问
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-message ${msg.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'}`}
          >
            <div className="chat-message-role">
              {msg.role === 'user' ? '你' : 'AI'}
            </div>
            <div className="chat-message-content">{msg.content}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="chat-message-sources">
                <strong>来源：</strong>
                {msg.sources.map((src, i) => (
                  <div key={i} className="chat-source-item">
                    {src.url ? (
                      <a href={src.url} target="_blank" rel="noopener noreferrer">
                        {src.title}
                      </a>
                    ) : (
                      src.title
                    )}
                    {src.snippet && <div className="chat-source-snippet">{src.snippet}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {chatMutation.isPending && (
          <div className="chat-loading">
            <Loader2 size={24} className="animate-spin chat-loading-spinner" />
            <span className="chat-loading-text">思考中...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input chat-input-container">
        <div className="chat-input-row">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入你的问题..."
            disabled={!selectedSource || chatMutation.isPending}
            className="chat-input-field"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !selectedSource || chatMutation.isPending}
            className="button-primary chat-send-button"
          >
            <Send size={16} />
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
