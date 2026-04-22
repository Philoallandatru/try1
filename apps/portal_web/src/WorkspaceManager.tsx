import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { apiJson } from './apiUtils';
import {
  Folder,
  Star,
  Clock,
  Settings,
  Trash2,
  Edit2,
  Plus,
  X,
  Check,
  AlertCircle,
  Loader2,
} from 'lucide-react';

const workspaceSchema = z.object({
  name: z.string().optional(),
  workspace_dir: z.string(),
  created_at: z.string().optional(),
  last_accessed: z.string().optional(),
  description: z.string().optional(),
});

const workspacesSchema = z.object({
  workspaces: z.array(workspaceSchema),
});

type Workspace = z.infer<typeof workspaceSchema>;

interface WorkspacePreferences {
  favorites: string[];
  recentlyUsed: string[];
  workspaceSettings: Record<string, {
    description?: string;
    color?: string;
    icon?: string;
  }>;
}

const PREFERENCES_KEY = 'ssdPortal:workspacePreferences';

function getPreferences(): WorkspacePreferences {
  const stored = localStorage.getItem(PREFERENCES_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      // Fall through to default
    }
  }
  return {
    favorites: [],
    recentlyUsed: [],
    workspaceSettings: {},
  };
}

function savePreferences(prefs: WorkspacePreferences) {
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(prefs));
}

function addToRecent(workspaceDir: string) {
  const prefs = getPreferences();
  prefs.recentlyUsed = [
    workspaceDir,
    ...prefs.recentlyUsed.filter(dir => dir !== workspaceDir)
  ].slice(0, 5);
  savePreferences(prefs);
}

function toggleFavorite(workspaceDir: string) {
  const prefs = getPreferences();
  if (prefs.favorites.includes(workspaceDir)) {
    prefs.favorites = prefs.favorites.filter(dir => dir !== workspaceDir);
  } else {
    prefs.favorites.push(workspaceDir);
  }
  savePreferences(prefs);
}

function setWorkspaceDescription(workspaceDir: string, description: string) {
  const prefs = getPreferences();
  if (!prefs.workspaceSettings[workspaceDir]) {
    prefs.workspaceSettings[workspaceDir] = {};
  }
  prefs.workspaceSettings[workspaceDir].description = description;
  savePreferences(prefs);
}

export function WorkspaceManager({
  currentWorkspace,
  onWorkspaceChange,
}: {
  currentWorkspace: string;
  onWorkspaceChange: (workspaceDir: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [editingWorkspace, setEditingWorkspace] = useState<string | null>(null);
  const [editDescription, setEditDescription] = useState('');
  const [preferences, setPreferences] = useState(getPreferences());

  const queryClient = useQueryClient();

  const workspaces = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => apiJson('/api/workspaces', workspacesSchema),
  });

  const createWorkspace = useMutation({
    mutationFn: (name: string) =>
      apiJson('/api/workspaces', workspaceSchema, {
        method: 'POST',
        body: JSON.stringify({ name }),
      }),
    onSuccess: (workspace) => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      onWorkspaceChange(workspace.workspace_dir);
      addToRecent(workspace.workspace_dir);
      setNewWorkspaceName('');
      setShowCreateForm(false);
      refreshPreferences();
    },
  });

  const deleteWorkspace = useMutation({
    mutationFn: (workspaceDir: string) =>
      apiJson(`/api/workspaces/${encodeURIComponent(workspaceDir)}`, z.unknown(), {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      refreshPreferences();
    },
  });

  const renameWorkspace = useMutation({
    mutationFn: ({ workspaceDir, newName }: { workspaceDir: string; newName: string }) =>
      apiJson(`/api/workspaces/${encodeURIComponent(workspaceDir)}`, workspaceSchema, {
        method: 'PATCH',
        body: JSON.stringify({ name: newName }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      setEditingWorkspace(null);
    },
  });

  const refreshPreferences = () => {
    setPreferences(getPreferences());
  };

  const handleWorkspaceSelect = (workspaceDir: string) => {
    onWorkspaceChange(workspaceDir);
    addToRecent(workspaceDir);
    refreshPreferences();
    setIsOpen(false);
  };

  const handleToggleFavorite = (workspaceDir: string, e: React.MouseEvent) => {
    e.stopPropagation();
    toggleFavorite(workspaceDir);
    refreshPreferences();
  };

  const handleSaveDescription = (workspaceDir: string) => {
    setWorkspaceDescription(workspaceDir, editDescription);
    refreshPreferences();
    setEditingWorkspace(null);
  };

  const handleDeleteWorkspace = (workspaceDir: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`Delete workspace "${workspaceDir}"? This cannot be undone.`)) {
      deleteWorkspace.mutate(workspaceDir);
    }
  };

  const allWorkspaces = workspaces.data?.workspaces || [];
  const favoriteWorkspaces = allWorkspaces.filter(ws =>
    preferences.favorites.includes(ws.workspace_dir)
  );
  const recentWorkspaces = preferences.recentlyUsed
    .map(dir => allWorkspaces.find(ws => ws.workspace_dir === dir))
    .filter((ws): ws is Workspace => ws !== undefined)
    .slice(0, 3);
  const otherWorkspaces = allWorkspaces.filter(ws =>
    !preferences.favorites.includes(ws.workspace_dir) &&
    !preferences.recentlyUsed.slice(0, 3).includes(ws.workspace_dir)
  );

  const currentWs = allWorkspaces.find(ws => ws.workspace_dir === currentWorkspace);

  return (
    <div className="workspace-manager">
      <button
        className="workspace-selector-button"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <Folder size={16} />
        <span>{currentWs?.name || currentWorkspace || 'Select workspace'}</span>
        <Settings size={14} />
      </button>

      {isOpen && (
        <div className="workspace-dropdown">
          <div className="workspace-dropdown-header">
            <h3>Workspaces</h3>
            <button
              className="icon-button"
              onClick={() => setIsOpen(false)}
              type="button"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </div>

          {/* Favorites */}
          {favoriteWorkspaces.length > 0 && (
            <div className="workspace-section">
              <div className="workspace-section-header">
                <Star size={14} />
                <span>Favorites</span>
              </div>
              {favoriteWorkspaces.map(workspace => (
                <WorkspaceItem
                  key={workspace.workspace_dir}
                  workspace={workspace}
                  isCurrent={workspace.workspace_dir === currentWorkspace}
                  isFavorite={true}
                  preferences={preferences}
                  onSelect={handleWorkspaceSelect}
                  onToggleFavorite={handleToggleFavorite}
                  onDelete={handleDeleteWorkspace}
                  onEdit={(dir) => {
                    setEditingWorkspace(dir);
                    setEditDescription(preferences.workspaceSettings[dir]?.description || '');
                  }}
                  isEditing={editingWorkspace === workspace.workspace_dir}
                  editDescription={editDescription}
                  onDescriptionChange={setEditDescription}
                  onSaveDescription={handleSaveDescription}
                  onCancelEdit={() => setEditingWorkspace(null)}
                />
              ))}
            </div>
          )}

          {/* Recent */}
          {recentWorkspaces.length > 0 && (
            <div className="workspace-section">
              <div className="workspace-section-header">
                <Clock size={14} />
                <span>Recent</span>
              </div>
              {recentWorkspaces.map(workspace => (
                <WorkspaceItem
                  key={workspace.workspace_dir}
                  workspace={workspace}
                  isCurrent={workspace.workspace_dir === currentWorkspace}
                  isFavorite={preferences.favorites.includes(workspace.workspace_dir)}
                  preferences={preferences}
                  onSelect={handleWorkspaceSelect}
                  onToggleFavorite={handleToggleFavorite}
                  onDelete={handleDeleteWorkspace}
                  onEdit={(dir) => {
                    setEditingWorkspace(dir);
                    setEditDescription(preferences.workspaceSettings[dir]?.description || '');
                  }}
                  isEditing={editingWorkspace === workspace.workspace_dir}
                  editDescription={editDescription}
                  onDescriptionChange={setEditDescription}
                  onSaveDescription={handleSaveDescription}
                  onCancelEdit={() => setEditingWorkspace(null)}
                />
              ))}
            </div>
          )}

          {/* All Workspaces */}
          {otherWorkspaces.length > 0 && (
            <div className="workspace-section">
              <div className="workspace-section-header">
                <Folder size={14} />
                <span>All Workspaces</span>
              </div>
              {otherWorkspaces.map(workspace => (
                <WorkspaceItem
                  key={workspace.workspace_dir}
                  workspace={workspace}
                  isCurrent={workspace.workspace_dir === currentWorkspace}
                  isFavorite={preferences.favorites.includes(workspace.workspace_dir)}
                  preferences={preferences}
                  onSelect={handleWorkspaceSelect}
                  onToggleFavorite={handleToggleFavorite}
                  onDelete={handleDeleteWorkspace}
                  onEdit={(dir) => {
                    setEditingWorkspace(dir);
                    setEditDescription(preferences.workspaceSettings[dir]?.description || '');
                  }}
                  isEditing={editingWorkspace === workspace.workspace_dir}
                  editDescription={editDescription}
                  onDescriptionChange={setEditDescription}
                  onSaveDescription={handleSaveDescription}
                  onCancelEdit={() => setEditingWorkspace(null)}
                />
              ))}
            </div>
          )}

          {/* Create New */}
          <div className="workspace-section">
            {showCreateForm ? (
              <div className="workspace-create-form">
                <input
                  type="text"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  placeholder="Workspace name"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newWorkspaceName.trim()) {
                      createWorkspace.mutate(newWorkspaceName);
                    } else if (e.key === 'Escape') {
                      setShowCreateForm(false);
                      setNewWorkspaceName('');
                    }
                  }}
                />
                <div className="workspace-create-actions">
                  <button
                    type="button"
                    onClick={() => createWorkspace.mutate(newWorkspaceName)}
                    disabled={!newWorkspaceName.trim() || createWorkspace.isPending}
                  >
                    {createWorkspace.isPending ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      <Check size={14} />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewWorkspaceName('');
                    }}
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>
            ) : (
              <button
                className="workspace-create-button"
                onClick={() => setShowCreateForm(true)}
                type="button"
              >
                <Plus size={16} />
                <span>Create new workspace</span>
              </button>
            )}
            {createWorkspace.error && (
              <div className="workspace-error">
                <AlertCircle size={14} />
                <span>{String(createWorkspace.error)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function WorkspaceItem({
  workspace,
  isCurrent,
  isFavorite,
  preferences,
  onSelect,
  onToggleFavorite,
  onDelete,
  onEdit,
  isEditing,
  editDescription,
  onDescriptionChange,
  onSaveDescription,
  onCancelEdit,
}: {
  workspace: Workspace;
  isCurrent: boolean;
  isFavorite: boolean;
  preferences: WorkspacePreferences;
  onSelect: (dir: string) => void;
  onToggleFavorite: (dir: string, e: React.MouseEvent) => void;
  onDelete: (dir: string, e: React.MouseEvent) => void;
  onEdit: (dir: string) => void;
  isEditing: boolean;
  editDescription: string;
  onDescriptionChange: (desc: string) => void;
  onSaveDescription: (dir: string) => void;
  onCancelEdit: () => void;
}) {
  const settings = preferences.workspaceSettings[workspace.workspace_dir];
  const description = settings?.description;

  return (
    <div className={`workspace-item ${isCurrent ? 'current' : ''}`}>
      <button
        className="workspace-item-main"
        onClick={() => onSelect(workspace.workspace_dir)}
        type="button"
      >
        <div className="workspace-item-content">
          <div className="workspace-item-header">
            <span className="workspace-item-name">
              {workspace.name || workspace.workspace_dir}
            </span>
            {isCurrent && <Check size={14} className="current-indicator" />}
          </div>
          {description && !isEditing && (
            <span className="workspace-item-description">{description}</span>
          )}
        </div>
      </button>

      {isEditing ? (
        <div className="workspace-item-edit">
          <input
            type="text"
            value={editDescription}
            onChange={(e) => onDescriptionChange(e.target.value)}
            placeholder="Add description..."
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onSaveDescription(workspace.workspace_dir);
              } else if (e.key === 'Escape') {
                onCancelEdit();
              }
            }}
          />
          <div className="workspace-item-edit-actions">
            <button
              type="button"
              onClick={() => onSaveDescription(workspace.workspace_dir)}
            >
              <Check size={14} />
            </button>
            <button type="button" onClick={onCancelEdit}>
              <X size={14} />
            </button>
          </div>
        </div>
      ) : (
        <div className="workspace-item-actions">
          <button
            className={`icon-button ${isFavorite ? 'active' : ''}`}
            onClick={(e) => onToggleFavorite(workspace.workspace_dir, e)}
            type="button"
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star size={14} fill={isFavorite ? 'currentColor' : 'none'} />
          </button>
          <button
            className="icon-button"
            onClick={() => onEdit(workspace.workspace_dir)}
            type="button"
            title="Edit description"
          >
            <Edit2 size={14} />
          </button>
          <button
            className="icon-button danger"
            onClick={(e) => onDelete(workspace.workspace_dir, e)}
            type="button"
            title="Delete workspace"
          >
            <Trash2 size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
