import React, { createContext, useContext, useState, useEffect } from 'react';

export enum PermissionLevel {
  OWNER = 'owner',
  ADMIN = 'admin',
  WRITE = 'write',
  READ = 'read',
}

export enum Permission {
  // 工作空间管理
  WORKSPACE_DELETE = 'workspace.delete',
  WORKSPACE_SETTINGS = 'workspace.settings',
  WORKSPACE_MEMBERS = 'workspace.members',

  // 数据源管理
  SOURCE_CREATE = 'source.create',
  SOURCE_UPDATE = 'source.update',
  SOURCE_DELETE = 'source.delete',
  SOURCE_SYNC = 'source.sync',
  SOURCE_VIEW = 'source.view',

  // 文档管理
  DOCUMENT_UPLOAD = 'document.upload',
  DOCUMENT_UPDATE = 'document.update',
  DOCUMENT_DELETE = 'document.delete',
  DOCUMENT_VIEW = 'document.view',

  // 分析功能
  ANALYSIS_RUN = 'analysis.run',
  ANALYSIS_VIEW = 'analysis.view',
  ANALYSIS_SHARE = 'analysis.share',

  // Profile 管理
  PROFILE_CREATE = 'profile.create',
  PROFILE_UPDATE = 'profile.update',
  PROFILE_DELETE = 'profile.delete',
  PROFILE_VIEW = 'profile.view',
}

interface WorkspacePermissions {
  workspace_dir: string;
  user_id: string;
  permission_level: PermissionLevel;
  permissions: {
    can_delete_workspace: boolean;
    can_manage_sources: boolean;
    can_upload_documents: boolean;
    can_run_analysis: boolean;
    can_manage_profiles: boolean;
  };
}

interface PermissionContextValue {
  permissions: WorkspacePermissions | null;
  hasPermission: (permission: Permission) => boolean;
  canDeleteWorkspace: () => boolean;
  canManageSources: () => boolean;
  canUploadDocuments: () => boolean;
  canRunAnalysis: () => boolean;
  canManageProfiles: () => boolean;
  setPermissions: (permissions: WorkspacePermissions | null) => void;
}

const PermissionContext = createContext<PermissionContextValue | undefined>(undefined);

// 权限矩阵
const PERMISSION_MATRIX: Record<PermissionLevel, Permission[]> = {
  [PermissionLevel.OWNER]: [
    Permission.WORKSPACE_DELETE,
    Permission.WORKSPACE_SETTINGS,
    Permission.WORKSPACE_MEMBERS,
    Permission.SOURCE_CREATE,
    Permission.SOURCE_UPDATE,
    Permission.SOURCE_DELETE,
    Permission.SOURCE_SYNC,
    Permission.SOURCE_VIEW,
    Permission.DOCUMENT_UPLOAD,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_DELETE,
    Permission.DOCUMENT_VIEW,
    Permission.ANALYSIS_RUN,
    Permission.ANALYSIS_VIEW,
    Permission.ANALYSIS_SHARE,
    Permission.PROFILE_CREATE,
    Permission.PROFILE_UPDATE,
    Permission.PROFILE_DELETE,
    Permission.PROFILE_VIEW,
  ],
  [PermissionLevel.ADMIN]: [
    Permission.WORKSPACE_SETTINGS,
    Permission.WORKSPACE_MEMBERS,
    Permission.SOURCE_CREATE,
    Permission.SOURCE_UPDATE,
    Permission.SOURCE_DELETE,
    Permission.SOURCE_SYNC,
    Permission.SOURCE_VIEW,
    Permission.DOCUMENT_UPLOAD,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_DELETE,
    Permission.DOCUMENT_VIEW,
    Permission.ANALYSIS_RUN,
    Permission.ANALYSIS_VIEW,
    Permission.ANALYSIS_SHARE,
    Permission.PROFILE_CREATE,
    Permission.PROFILE_UPDATE,
    Permission.PROFILE_DELETE,
    Permission.PROFILE_VIEW,
  ],
  [PermissionLevel.WRITE]: [
    Permission.SOURCE_VIEW,
    Permission.SOURCE_SYNC,
    Permission.DOCUMENT_UPLOAD,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_VIEW,
    Permission.ANALYSIS_RUN,
    Permission.ANALYSIS_VIEW,
    Permission.PROFILE_VIEW,
  ],
  [PermissionLevel.READ]: [
    Permission.SOURCE_VIEW,
    Permission.DOCUMENT_VIEW,
    Permission.ANALYSIS_VIEW,
    Permission.PROFILE_VIEW,
  ],
};

export function PermissionProvider({ children }: { children: React.ReactNode }) {
  const [permissions, setPermissions] = useState<WorkspacePermissions | null>(null);

  // 默认权限（所有者）
  useEffect(() => {
    if (!permissions) {
      setPermissions({
        workspace_dir: '',
        user_id: 'default',
        permission_level: PermissionLevel.OWNER,
        permissions: {
          can_delete_workspace: true,
          can_manage_sources: true,
          can_upload_documents: true,
          can_run_analysis: true,
          can_manage_profiles: true,
        },
      });
    }
  }, [permissions]);

  const hasPermission = (permission: Permission): boolean => {
    if (!permissions) return false;
    const allowedPermissions = PERMISSION_MATRIX[permissions.permission_level] || [];
    return allowedPermissions.includes(permission);
  };

  const canDeleteWorkspace = (): boolean => {
    return permissions?.permissions.can_delete_workspace ?? false;
  };

  const canManageSources = (): boolean => {
    return permissions?.permissions.can_manage_sources ?? false;
  };

  const canUploadDocuments = (): boolean => {
    return permissions?.permissions.can_upload_documents ?? false;
  };

  const canRunAnalysis = (): boolean => {
    return permissions?.permissions.can_run_analysis ?? false;
  };

  const canManageProfiles = (): boolean => {
    return permissions?.permissions.can_manage_profiles ?? false;
  };

  const value: PermissionContextValue = {
    permissions,
    hasPermission,
    canDeleteWorkspace,
    canManageSources,
    canUploadDocuments,
    canRunAnalysis,
    canManageProfiles,
    setPermissions,
  };

  return (
    <PermissionContext.Provider value={value}>
      {children}
    </PermissionContext.Provider>
  );
}

export function usePermissions(): PermissionContextValue {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissions must be used within a PermissionProvider');
  }
  return context;
}

// 权限保护的按钮组件
export function ProtectedButton({
  permission,
  children,
  fallback,
  ...props
}: {
  permission: Permission;
  children: React.ReactNode;
  fallback?: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { hasPermission } = usePermissions();

  if (!hasPermission(permission)) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return (
      <button {...props} disabled title="权限不足">
        {children}
      </button>
    );
  }

  return <button {...props}>{children}</button>;
}

// 权限保护的内容组件
export function ProtectedContent({
  permission,
  children,
  fallback,
}: {
  permission: Permission;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasPermission } = usePermissions();

  if (!hasPermission(permission)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// 权限级别徽章组件
export function PermissionBadge({ level }: { level: PermissionLevel }) {
  const labels: Record<PermissionLevel, string> = {
    [PermissionLevel.OWNER]: '所有者',
    [PermissionLevel.ADMIN]: '管理员',
    [PermissionLevel.WRITE]: '读写',
    [PermissionLevel.READ]: '只读',
  };

  const colors: Record<PermissionLevel, string> = {
    [PermissionLevel.OWNER]: 'permission-badge-owner',
    [PermissionLevel.ADMIN]: 'permission-badge-admin',
    [PermissionLevel.WRITE]: 'permission-badge-write',
    [PermissionLevel.READ]: 'permission-badge-read',
  };

  return (
    <span className={`permission-badge ${colors[level]}`}>
      {labels[level]}
    </span>
  );
}

// 权限不足提示组件
export function PermissionDenied({ message }: { message?: string }) {
  return (
    <div className="permission-denied">
      <div className="permission-denied-icon">🔒</div>
      <h3>权限不足</h3>
      <p>{message || '您没有权限执行此操作'}</p>
    </div>
  );
}
