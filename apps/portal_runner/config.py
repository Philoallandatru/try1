from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(".local/portal-runner/config.yaml")


class PortalRunnerConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ServerConfig:
    runner_token: str
    max_upload_mb: int = 100


@dataclass(frozen=True)
class SourceConfig:
    base_url: str
    token: str
    auth_mode: str = "auto"
    username: str | None = None
    password: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and (self.token or (self.username and self.password)))


@dataclass(frozen=True)
class WorkspaceConfig:
    root: Path = Path(".tmp/portal-runner/workspaces")
    uploads_root: Path = Path(".tmp/portal-runner/uploads")
    runs_root: Path = Path(".tmp/portal-runner/runs")


@dataclass(frozen=True)
class PipelineConfig:
    enabled: bool = True
    preferred_parser: str = "pypdf"
    publish_wiki: bool = True


@dataclass(frozen=True)
class PortalRunnerConfig:
    path: Path
    server: ServerConfig
    jira: SourceConfig
    confluence: SourceConfig
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    pipelines: dict[str, PipelineConfig] = field(default_factory=dict)

    def pipeline_config(self, pipeline_id: str) -> PipelineConfig:
        return self.pipelines.get(pipeline_id, PipelineConfig(enabled=False))

    def public_status(self) -> dict:
        return {
            "config_path": str(self.path),
            "server": {
                "runner_token_configured": bool(self.server.runner_token),
                "max_upload_mb": self.server.max_upload_mb,
            },
            "jira": {
                "configured": self.jira.configured,
                "base_url": self.jira.base_url,
                "auth_mode": self.jira.auth_mode,
            },
            "confluence": {
                "configured": self.confluence.configured,
                "base_url": self.confluence.base_url,
                "auth_mode": self.confluence.auth_mode,
            },
            "workspace": {
                "root": str(self.workspace.root),
                "uploads_root": str(self.workspace.uploads_root),
                "runs_root": str(self.workspace.runs_root),
            },
            "pipelines": {
                pipeline_id: {
                    "enabled": pipeline.enabled,
                    "preferred_parser": pipeline.preferred_parser,
                    "publish_wiki": pipeline.publish_wiki,
                }
                for pipeline_id, pipeline in self.pipelines.items()
            },
        }


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> PortalRunnerConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise PortalRunnerConfigError(
            f"Portal runner config not found: {config_path}. "
            "Copy config/portal-runner.example.yaml to .local/portal-runner/config.yaml."
        )

    try:
        import yaml
    except ImportError as exc:
        raise PortalRunnerConfigError("PyYAML is required. Install with .[portal-runner].") from exc

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise PortalRunnerConfigError("Portal runner config must be a YAML object.")

    server = _server_config(raw.get("server", {}))
    jira = _source_config(raw.get("jira", {}), name="jira")
    confluence = _source_config(raw.get("confluence", {}), name="confluence")
    workspace = _workspace_config(raw.get("workspace", {}))
    pipelines = _pipeline_configs(raw.get("pipelines", {}))

    return PortalRunnerConfig(
        path=config_path,
        server=server,
        jira=jira,
        confluence=confluence,
        workspace=workspace,
        pipelines=pipelines,
    )


def validate_bind_security(config: PortalRunnerConfig, host: str) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"} and not config.server.runner_token:
        raise PortalRunnerConfigError("server.runner_token is required when binding beyond localhost.")


def _server_config(raw: Any) -> ServerConfig:
    raw = _ensure_mapping(raw, "server")
    token = str(raw.get("runner_token") or "").strip()
    max_upload_mb = int(raw.get("max_upload_mb", 100))
    if max_upload_mb <= 0:
        raise PortalRunnerConfigError("server.max_upload_mb must be greater than 0.")
    return ServerConfig(runner_token=token, max_upload_mb=max_upload_mb)


def _source_config(raw: Any, *, name: str) -> SourceConfig:
    raw = _ensure_mapping(raw, name)
    return SourceConfig(
        base_url=str(raw.get("base_url") or "").strip(),
        token=str(raw.get("token") or "").strip(),
        auth_mode=str(raw.get("auth_mode") or "auto"),
        username=_optional_str(raw.get("username")),
        password=_optional_str(raw.get("password")),
    )


def _workspace_config(raw: Any) -> WorkspaceConfig:
    raw = _ensure_mapping(raw, "workspace")
    return WorkspaceConfig(
        root=Path(raw.get("root") or ".tmp/portal-runner/workspaces"),
        uploads_root=Path(raw.get("uploads_root") or ".tmp/portal-runner/uploads"),
        runs_root=Path(raw.get("runs_root") or ".tmp/portal-runner/runs"),
    )


def _pipeline_configs(raw: Any) -> dict[str, PipelineConfig]:
    raw = _ensure_mapping(raw, "pipelines")
    configs: dict[str, PipelineConfig] = {}
    for pipeline_id, payload in raw.items():
        payload = _ensure_mapping(payload or {}, f"pipelines.{pipeline_id}")
        configs[str(pipeline_id)] = PipelineConfig(
            enabled=bool(payload.get("enabled", True)),
            preferred_parser=str(payload.get("preferred_parser") or "pypdf"),
            publish_wiki=bool(payload.get("publish_wiki", True)),
        )
    return configs


def _ensure_mapping(value: Any, name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PortalRunnerConfigError(f"{name} must be a mapping.")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
