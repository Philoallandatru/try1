param(
    [Parameter(Mandatory = $true)]
    [string]$JiraBaseUrl,

    [string]$JiraToken = $env:JIRA_TOKEN,

    [Parameter(Mandatory = $true)]
    [string]$JiraIssueKey,

    [Parameter(Mandatory = $true)]
    [string]$ConfluenceBaseUrl,

    [string]$ConfluenceToken = $env:CONF_TOKEN,

    [Parameter(Mandatory = $true)]
    [string]$ConfluencePageId,

    [Parameter(Mandatory = $true)]
    [string]$SpecPdfPath,

    [string]$WorkspaceDir = ".tmp\real-workspace",
    [string]$SmokeOutputDir = ".tmp\real-data-smoke",
    [string]$PortalStateOutput,

    [ValidateSet("auto", "mineru", "pypdf")]
    [string]$PreferredParser = "pypdf",

    [string]$SpecAssetId = "real-spec",
    [string]$TopicSlug = "real-source-smoke",
    [string]$TopicTitle = "Real Source Smoke",
    [string]$MockResponse = "Real-source smoke content",
    [string]$PythonExe,

    [switch]$SkipConnectorSmoke,
    [switch]$SkipWorkspaceSmoke,
    [switch]$SkipWikiPublish,
    [switch]$RunRegressionTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Resolve-PythonExe {
    param([string]$RequestedPython)

    if ($RequestedPython) {
        if (-not (Get-Command $RequestedPython -ErrorAction SilentlyContinue)) {
            throw "Python executable was not found: $RequestedPython"
        }
        return $RequestedPython
    }

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }

    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        throw "Python executable was not found. Create .venv or pass -PythonExe."
    }
    return "python"
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$ShowCommand
    )

    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan
    if ($ShowCommand) {
        Write-Host ($Script:Python + " " + ($Arguments -join " "))
    }
    & $Script:Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)][object]$Payload,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $Payload | ConvertTo-Json -Depth 20 | Set-Content -Path $Path -Encoding UTF8
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    return Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Assert-RequiredInput {
    if (-not $JiraToken) {
        throw "Jira token is required. Set JIRA_TOKEN or pass -JiraToken."
    }
    if (-not $ConfluenceToken) {
        throw "Confluence token is required. Set CONF_TOKEN or pass -ConfluenceToken."
    }
    if (-not (Test-Path -LiteralPath $SpecPdfPath)) {
        throw "Spec PDF was not found: $SpecPdfPath"
    }
}

function Get-FirstDocumentIdByType {
    param(
        [Parameter(Mandatory = $true)][string]$SnapshotDocumentsPath,
        [Parameter(Mandatory = $true)][string]$SourceType,
        [string]$PreferredId
    )

    $snapshot = Read-JsonFile -Path $SnapshotDocumentsPath
    $documents = @($snapshot.documents)
    if ($PreferredId) {
        $preferred = $documents | Where-Object { $_.source_type -eq $SourceType -and $_.document_id -eq $PreferredId } | Select-Object -First 1
        if ($preferred) {
            return [string]$preferred.document_id
        }
    }

    $first = $documents | Where-Object { $_.source_type -eq $SourceType } | Select-Object -First 1
    if (-not $first) {
        throw "No document found in snapshot for source_type=$SourceType"
    }
    return [string]$first.document_id
}

Assert-RequiredInput
$Script:Python = Resolve-PythonExe -RequestedPython $PythonExe

$workspacePath = Join-Path $RepoRoot $WorkspaceDir
$smokePath = Join-Path $RepoRoot $SmokeOutputDir
$jiraSmokeJson = Join-Path $smokePath "jira-live.json"
$confluenceSmokeJson = Join-Path $smokePath "confluence-live.json"
if ($PortalStateOutput) {
    $portalStateJson = Join-Path $RepoRoot $PortalStateOutput
} else {
    $portalStateJson = Join-Path $workspacePath "portal_state.json"
}

New-Item -ItemType Directory -Force -Path $smokePath | Out-Null

Write-Host "== Real data smoke configuration =="
Write-Host "Repo root: $RepoRoot"
Write-Host "Python: $Script:Python"
Write-Host "Workspace: $workspacePath"
Write-Host "Smoke output: $smokePath"
Write-Host "Jira issue: $JiraIssueKey"
Write-Host "Confluence page: $ConfluencePageId"
Write-Host "Spec PDF: $SpecPdfPath"
Write-Host "Preferred parser: $PreferredParser"
Write-Host "Tokens are not printed, but workspace spec files under .tmp will contain token values."

if (-not $SkipConnectorSmoke) {
    Invoke-Step -Name "Jira selective live fetch" -Arguments @(
        "scripts/platform_cli.py",
        "connector",
        "jira",
        "--live",
        "--base-url", $JiraBaseUrl,
        "--token", $JiraToken,
        "--fetch-backend", "atlassian-api",
        "--issue-key", $JiraIssueKey,
        "--output-json", $jiraSmokeJson
    )

    Invoke-Step -Name "Confluence selective live fetch" -Arguments @(
        "scripts/platform_cli.py",
        "connector",
        "confluence",
        "--live",
        "--base-url", $ConfluenceBaseUrl,
        "--token", $ConfluenceToken,
        "--fetch-backend", "atlassian-api",
        "--page-id", $ConfluencePageId,
        "--output-json", $confluenceSmokeJson
    )
}

if (-not $SkipWorkspaceSmoke) {
    Invoke-Step -Name "Initialize workspace" -Arguments @(
        "scripts/workspace_cli.py",
        "init",
        $WorkspaceDir
    )

    $jiraSpecPath = Join-Path $workspacePath "raw\jira\specs\one-issue.json"
    $confluenceSpecPath = Join-Path $workspacePath "raw\confluence\specs\one-page.json"

    Write-Host ""
    Write-Host "== Write live source specs =="
    Write-Host "Jira spec: $jiraSpecPath"
    Write-Host "Confluence spec: $confluenceSpecPath"

    $jiraSpec = @{
        kind = "jira"
        mode = "live"
        base_url = $JiraBaseUrl
        token = $JiraToken
        scope = @{
            type = "issue"
            issue_key = $JiraIssueKey
        }
        fetch = @{
            fetch_backend = "atlassian-api"
            include_comments = $true
            include_attachments = $true
            include_image_metadata = $true
            download_images = $false
        }
    }
    Write-JsonFile -Payload $jiraSpec -Path $jiraSpecPath

    $confluenceSpec = @{
        kind = "confluence"
        mode = "live"
        base_url = $ConfluenceBaseUrl
        token = $ConfluenceToken
        scope = @{
            type = "page"
            page_id = $ConfluencePageId
        }
        fetch = @{
            fetch_backend = "atlassian-api"
        }
    }
    Write-JsonFile -Payload $confluenceSpec -Path $confluenceSpecPath

    Invoke-Step -Name "Ingest PDF spec asset" -Arguments @(
        "scripts/workspace_cli.py",
        "ingest-spec-asset",
        $WorkspaceDir,
        "--spec-pdf", $SpecPdfPath,
        "--asset-id", $SpecAssetId,
        "--display-name", $TopicTitle,
        "--preferred-parser", $PreferredParser
    )

    Invoke-Step -Name "Run workspace real-source smoke-deep-analysis" -Arguments @(
        "scripts/workspace_cli.py",
        "smoke-deep-analysis",
        $WorkspaceDir,
        "--jira-spec", "one-issue",
        "--confluence-spec", "one-page",
        "--issue-key", $JiraIssueKey,
        "--spec-pdf", $SpecPdfPath,
        "--spec-asset-id", $SpecAssetId,
        "--preferred-parser", $PreferredParser,
        "--portal-state-output", $portalStateJson
    )

    Invoke-Step -Name "List workspace runs" -Arguments @(
        "scripts/workspace_cli.py",
        "runs",
        $WorkspaceDir
    )

    Invoke-Step -Name "Generate portal state from workspace runs" -Arguments @(
        "scripts/workspace_cli.py",
        "portal-state",
        $WorkspaceDir,
        "--output", $portalStateJson,
        "--query", $JiraIssueKey
    )
}

if ((-not $SkipWorkspaceSmoke) -and (-not $SkipWikiPublish)) {
    $snapshotDocuments = Join-Path $workspacePath "snapshots\current\documents.json"
    $jiraDocumentId = Get-FirstDocumentIdByType -SnapshotDocumentsPath $snapshotDocuments -SourceType "jira" -PreferredId $JiraIssueKey
    $confluenceDocumentId = Get-FirstDocumentIdByType -SnapshotDocumentsPath $snapshotDocuments -SourceType "confluence" -PreferredId $ConfluencePageId
    $routeManifestPath = Join-Path $workspacePath "route-manifest.json"

    Write-Host ""
    Write-Host "== Write wiki route manifest =="
    Write-Host "Route manifest: $routeManifestPath"
    Write-Host "Jira document id: $jiraDocumentId"
    Write-Host "Confluence document id: $confluenceDocumentId"

    $routeManifest = @{
        topics = @(
            @{
                slug = $TopicSlug
                title = $TopicTitle
                description = "Real-source smoke topic for Jira, Confluence, and spec evidence."
            }
        )
        confluence = @(
            @{
                document_id = $confluenceDocumentId
                topic = $TopicSlug
                mode = "summarize"
            }
        )
        jira = @(
            @{
                document_id = $jiraDocumentId
                topic = $TopicSlug
                mode = "analyze"
                promote = $true
            }
        )
    }
    Write-JsonFile -Payload $routeManifest -Path $routeManifestPath

    Invoke-Step -Name "Publish topic-routed wiki" -Arguments @(
        "scripts/workspace_cli.py",
        "publish-wiki",
        $WorkspaceDir,
        "--manifest", $routeManifestPath,
        "--renderer", "vitepress",
        "--llm-backend", "mock",
        "--llm-mock-response", $MockResponse
    )
}

if ($RunRegressionTests) {
    Invoke-Step -Name "Run focused regression tests" -Arguments @(
        "-m",
        "unittest",
        "tests.connectors.test_jira_atlassian_api_fetch",
        "tests.connectors.test_live_connectors",
        "tests.ops.test_platform_cli_live_orchestration",
        "tests.ops.test_workspace_cli",
        "tests.portal.test_portal_state",
        "tests.portal.test_portal_ui_contract",
        "-v"
    )
}

Invoke-Step -Name "Compile changed runtime surfaces" -Arguments @(
    "-m",
    "py_compile",
    "scripts/workspace_cli.py",
    "scripts/platform_cli.py",
    "services/workspace/workspace.py",
    "apps/portal/portal_state.py"
)

Write-Host ""
Write-Host "== Real data smoke complete ==" -ForegroundColor Green
Write-Host "Connector outputs:"
Write-Host "  $jiraSmokeJson"
Write-Host "  $confluenceSmokeJson"
Write-Host "Workspace outputs:"
Write-Host "  Snapshot: $(Join-Path $workspacePath 'snapshots\current')"
Write-Host "  Runs:     $(Join-Path $workspacePath 'runs')"
Write-Host "  Portal:   $portalStateJson"
Write-Host "  Wiki:     $(Join-Path $workspacePath 'wiki\vitepress_site')"
Write-Host ""
Write-Host "To preview the portal:"
Write-Host "  .\.venv\Scripts\python.exe scripts\workspace_cli.py portal-state $WorkspaceDir --output apps\portal\portal_state.json --query $JiraIssueKey"
Write-Host "  cd apps\portal"
Write-Host "  python -m http.server 8787"
Write-Host ""
Write-Host "To preview the VitePress wiki:"
Write-Host "  cd $(Join-Path $workspacePath 'wiki\vitepress_site')"
Write-Host "  npm install"
Write-Host "  npm run docs:dev"
