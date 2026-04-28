import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { api, queryKeys, type Profile, type Source, type Selector } from '../../api';

interface ProfilesPanelProps {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  selectors: Selector[];
  onRefresh: () => void;
}

export function ProfilesPanel({ workspaceDir, profiles, sources, selectors, onRefresh }: ProfilesPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const queryClient = useQueryClient();

  const deleteProfile = useMutation({
    mutationFn: (name: string) => api.profiles.delete(name, workspaceDir),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.profiles.all(workspaceDir) }),
  });

  return (
    <div className="config-panel">
      <div className="panel-header">
        <h3>Analysis Profiles</h3>
        <button className="primary-button" onClick={() => setShowAddModal(true)}>
          <Plus size={16} /> Add Profile
        </button>
      </div>

      <div className="config-list">
        {profiles.map((profile) => (
          <div key={profile.name} className="config-item">
            <div className="config-item-header">
              <div className="config-item-title">
                <Settings size={18} />
                <strong>{profile.name}</strong>
              </div>
              <div className="config-item-actions">
                <button onClick={() => deleteProfile.mutate(profile.name)} className="danger">
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>
            <div className="config-item-details">
              {profile.inputs && (
                <div className="detail-row">
                  <span>Inputs:</span>
                  <span>{Object.keys(profile.inputs).join(', ')}</span>
                </div>
              )}
              {profile.analysis && (
                <>
                  <div className="detail-row">
                    <span>LLM Backend:</span>
                    <span>{String((profile.analysis as any).llm_backend || 'none')}</span>
                  </div>
                  <div className="detail-row">
                    <span>Prompt Mode:</span>
                    <span>{String((profile.analysis as any).llm_prompt_mode || 'strict')}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Profile</h3>
              <button onClick={() => setShowAddModal(false)}>
                <X size={20} />
              </button>
            </div>
            <p>Use the Profiles page for detailed profile creation</p>
            <button onClick={() => setShowAddModal(false)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
