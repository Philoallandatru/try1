param(
    [string]$SpecPdfPath,
    [string]$SpecCorpusPath,
    [string]$SpecDocumentId,
    [string]$Clause,
    [string]$SectionHeading,
    [string]$ReferenceDate = "2026-04-05",
    [string]$OutputDir = ".tmp/demo",
    [string]$SnapshotDir,
    [switch]$UseFixtures = $true,
    [string]$JiraBaseUrl,
    [string]$JiraToken,
    [string]$ConfluenceBaseUrl,
    [string]$ConfluenceToken,
    [string]$MockResponse = "Mock demo output"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $SnapshotDir) {
    $SnapshotDir = Join-Path $OutputDir "snapshot"
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function New-SpecCorpusFromPdf {
    param(
        [Parameter(Mandatory = $true)][string]$PdfPath,
        [Parameter(Mandatory = $true)][string]$TargetDir
    )

    New-Item -ItemType Directory -Force $TargetDir | Out-Null

    $pythonScript = @"
import json
from pathlib import Path
from services.ingest.adapters.pdf.adapter import extract_pdf_structure

pdf_path = Path(r"$PdfPath")
target_dir = Path(r"$TargetDir")
target_dir.mkdir(parents=True, exist_ok=True)

doc = extract_pdf_structure(pdf_path)
(target_dir / "spec-doc.json").write_text(
    json.dumps(doc, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
(target_dir / "spec-corpus.json").write_text(
    json.dumps({"documents": [doc]}, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print("__SPEC_RESULT__" + json.dumps({
    "document_id": doc["document_id"],
    "spec_doc_json": str(target_dir / "spec-doc.json"),
    "spec_corpus_json": str(target_dir / "spec-corpus.json"),
    "section_count": len(doc.get("structure", {}).get("sections", [])),
    "content_block_count": len(doc.get("content_blocks", [])),
}, ensure_ascii=False))
"@

    $resultLines = $pythonScript | python -
    $resultLine = $resultLines | Where-Object { $_ -like "__SPEC_RESULT__*" } | Select-Object -Last 1
    if (-not $resultLine) {
        throw "Failed to build spec corpus from PDF: $PdfPath"
    }
    return ($resultLine -replace "^__SPEC_RESULT__", "") | ConvertFrom-Json
}

function Resolve-DefaultSection {
    param(
        [Parameter(Mandatory = $true)][string]$CorpusPath,
        [Parameter(Mandatory = $true)][string]$DocumentId
    )

    $pythonScript = @"
import json
from pathlib import Path

payload = json.loads(Path(r"$CorpusPath").read_text(encoding="utf-8"))
document = next(doc for doc in payload["documents"] if doc["document_id"] == r"$DocumentId")
sections = document.get("structure", {}).get("sections", [])

selected = None
for section in sections:
    if section.get("clause"):
        selected = {"clause": section.get("clause"), "section_heading": section.get("heading")}
        break
if selected is None and sections:
    selected = {"clause": None, "section_heading": sections[0].get("heading")}
print(json.dumps(selected or {}, ensure_ascii=False))
"@

    $result = $pythonScript | python -
    if (-not $result) {
        return @{}
    }
    return $result | ConvertFrom-Json
}

Require-Command python

Write-Host "== Demo pipeline starting ==" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"
Write-Host "Output dir: $OutputDir"
Write-Host "Snapshot dir: $SnapshotDir"

if ($SpecPdfPath) {
    $specBuildDir = Join-Path $OutputDir "spec-build"
    $specResult = New-SpecCorpusFromPdf -PdfPath $SpecPdfPath -TargetDir $specBuildDir
    $SpecCorpusPath = $specResult.spec_corpus_json
    if (-not $SpecDocumentId) {
        $SpecDocumentId = $specResult.document_id
    }
    Write-Host "Spec corpus generated from PDF:" -ForegroundColor Green
    Write-Host "  document_id: $SpecDocumentId"
    Write-Host "  spec_doc_json: $($specResult.spec_doc_json)"
    Write-Host "  spec_corpus_json: $SpecCorpusPath"
    Write-Host "  section_count: $($specResult.section_count)"
    Write-Host "  content_block_count: $($specResult.content_block_count)"
}

if (-not $SpecCorpusPath) {
    $SpecCorpusPath = "fixtures/retrieval/pageindex_corpus.json"
}

if (-not $SpecDocumentId) {
    $SpecDocumentId = "nvme-spec-v1"
}

if (-not $Clause -and -not $SectionHeading) {
    $defaultSection = Resolve-DefaultSection -CorpusPath $SpecCorpusPath -DocumentId $SpecDocumentId
    if ($defaultSection.clause) {
        $Clause = [string]$defaultSection.clause
    } elseif ($defaultSection.section_heading) {
        $SectionHeading = [string]$defaultSection.section_heading
    } else {
        throw "Could not resolve a default section from corpus: $SpecCorpusPath (document_id=$SpecDocumentId)"
    }
}

Write-Host "Spec corpus: $SpecCorpusPath"
Write-Host "Spec document_id: $SpecDocumentId"
if ($Clause) {
    Write-Host "Selected clause: $Clause"
}
if ($SectionHeading) {
    Write-Host "Selected section heading: $SectionHeading"
}

$demoArgs = @(
    "scripts/platform_cli.py",
    "demo-orchestrate",
    "--snapshot-dir", $SnapshotDir,
    "--spec-corpus", $SpecCorpusPath,
    "--spec-document-id", $SpecDocumentId,
    "--reference-date", $ReferenceDate,
    "--output-dir", $OutputDir,
    "--llm-backend", "mock",
    "--llm-mock-response", $MockResponse
)

if ($Clause) {
    $demoArgs += @("--clause", $Clause)
} else {
    $demoArgs += @("--section-heading", $SectionHeading)
}

if ($UseFixtures) {
    $demoArgs += @(
        "--jira-path", "fixtures/connectors/jira/incremental_sync.json",
        "--confluence-path", "fixtures/connectors/confluence/page_sync.json"
    )
} else {
    if (-not $JiraBaseUrl) {
        throw "JiraBaseUrl is required when -UseFixtures:`$false"
    }
    if (-not $JiraToken) {
        throw "JiraToken is required when -UseFixtures:`$false"
    }
    if (-not $ConfluenceBaseUrl) {
        throw "ConfluenceBaseUrl is required when -UseFixtures:`$false"
    }
    if (-not $ConfluenceToken) {
        throw "ConfluenceToken is required when -UseFixtures:`$false"
    }
    $demoArgs += @(
        "--jira-live",
        "--jira-base-url", $JiraBaseUrl,
        "--jira-token", $JiraToken,
        "--confluence-live",
        "--confluence-base-url", $ConfluenceBaseUrl,
        "--confluence-token", $ConfluenceToken
    )
}

Write-Host ""
Write-Host "Running demo-orchestrate..." -ForegroundColor Cyan
Write-Host ("python " + ($demoArgs -join " "))
Write-Host ""

& python @demoArgs
if ($LASTEXITCODE -ne 0) {
    throw "demo-orchestrate failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Demo outputs:" -ForegroundColor Green
Write-Host "  Jira daily:    $(Join-Path $OutputDir 'jira-daily.md')"
Write-Host "  Spec section:  $(Join-Path $OutputDir 'spec-section.md')"
Write-Host "  Wiki index:    $(Join-Path (Join-Path $OutputDir 'wiki') 'index.html')"
Write-Host "  Snapshot dir:  $SnapshotDir"
