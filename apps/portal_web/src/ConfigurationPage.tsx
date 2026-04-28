import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Filter,
  Settings,
} from 'lucide-react';
import { queries } from './api';
import { SourcesPanel } from './components/configuration/SourceForm';
import { SelectorsPanel } from './components/configuration/SelectorForm';
import { ProfilesPanel } from './components/configuration/ProfileForm';

interface ConfigurationPageProps {
  workspaceDir: string;
}

type TabType = 'sources' | 'selectors' | 'profiles';

export default function ConfigurationPage({ workspaceDir }: ConfigurationPageProps) {
  const [activeTab, setActiveTab] = useState<TabType>('sources');
  const queryClient = useQueryClient();

  const sources = useQuery(queries.sources.list(workspaceDir));
  const profiles = useQuery(queries.profiles.list(workspaceDir));

  const sourcesData = sources.data?.sources || [];
  const selectorsData = sources.data?.selectors || [];
  const profilesData = profiles.data?.profiles || [];

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Configuration</p>
          <h2>Workspace Configuration</h2>
          <p>Manage data sources, selectors, and analysis profiles</p>
        </div>

        <div className="config-tabs">
          <button
            className={activeTab === 'sources' ? 'config-tab active' : 'config-tab'}
            onClick={() => setActiveTab('sources')}
          >
            <Database size={16} /> Sources ({sourcesData.length})
          </button>
          <button
            className={activeTab === 'selectors' ? 'config-tab active' : 'config-tab'}
            onClick={() => setActiveTab('selectors')}
          >
            <Filter size={16} /> Selectors ({selectorsData.length})
          </button>
          <button
            className={activeTab === 'profiles' ? 'config-tab active' : 'config-tab'}
            onClick={() => setActiveTab('profiles')}
          >
            <Settings size={16} /> Profiles ({profilesData.length})
          </button>
        </div>

        {activeTab === 'sources' && (
          <SourcesPanel
            workspaceDir={workspaceDir}
            sources={sourcesData}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] })}
          />
        )}

        {activeTab === 'selectors' && (
          <SelectorsPanel
            workspaceDir={workspaceDir}
            selectors={selectorsData}
            sources={sourcesData}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] })}
          />
        )}

        {activeTab === 'profiles' && (
          <ProfilesPanel
            workspaceDir={workspaceDir}
            profiles={profilesData}
            sources={sourcesData}
            selectors={selectorsData}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['profiles', workspaceDir] })}
          />
        )}
      </div>

      <aside className="side-panel">
        <h3>Configuration Guide</h3>
        <div className="guide-content">
          <div className="guide-section">
            <strong>1. Sources</strong>
            <p>Connect to Jira, Confluence, or PDF data sources</p>
          </div>
          <div className="guide-section">
            <strong>2. Selectors</strong>
            <p>Define filters to scope data from sources</p>
          </div>
          <div className="guide-section">
            <strong>3. Profiles</strong>
            <p>Create analysis profiles combining sources and settings</p>
          </div>
        </div>
      </aside>
    </section>
  );
}
