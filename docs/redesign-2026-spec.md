# SSD Knowledge Portal - 2026 Redesign Specification

**Version:** 2.0
**Date:** 2026-04-20
**Status:** Design Phase
**Supersedes:** `replan-markdown-pageindex-local-llm.md`, `architecture-overview.md` (Phase 1 sections)

---

## Executive Summary

This document defines the redesigned architecture for the SSD Knowledge Portal, focusing on:

1. **User Experience First** - Web UI as primary interface, not CLI
2. **Simplified Architecture** - Remove redundant layers, keep only what's essential
3. **Unified Data Sources** - All sources (Jira, Confluence, PDF, Office) flow through one consistent pipeline
4. **Improved Retrieval** - Data-driven optimization with measurable quality metrics
5. **Two Core Features** - Single Jira deep analysis + Daily Report with progressive generation

### Key Design Principles

- **Canonical Document as Truth** - Lightweight intermediate layer for cross-source retrieval
- **MinerU for All Files** - Unified file processing with intelligent fallback
- **Incremental Sync** - Hybrid strategy (initial cursor pagination + time-based increments)
- **System Internal Wiki** - Analysis results stored in structured knowledge base
- **Progressive Generation** - Fast initial reports, background deep analysis, automatic upgrades
- **Measurable Quality** - Golden Dataset evaluation with multi-strategy comparison

---

## 1. Architecture Overview

### 1.1 System Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      Web UI (Primary)                        │
│              Source Config | Analysis | Reports              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│   RESTful Resources + Task Endpoints + WebSocket Updates    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Source Connectors Layer                    │
│  Jira | Confluence | File Upload (PDF/Office/Images)        │
│         Unified Interface + Incremental Sync                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Processing Layer                          │
│  MinerU (Primary) → Canonical Document → Markdown/PageIndex │
│         Intelligent Fallback + Structure Preservation        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Retrieval Layer                           │
│    BM25 + Semantic + Hybrid + Structure-Aware + Reranking   │
│         Golden Dataset Evaluation + Strategy Comparison      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Layer                            │
│  Deep Analysis | Daily Report | Question Answering          │
│         Local LLM (LM Studio) + Progressive Generation       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Knowledge Base (Internal Wiki)              │
│    workspace/knowledge/{issues|reports}                      │
│         Structured Storage + Cross-Type Retrieval            │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
Source → Connector → Canonical Doc → Projections → Retrieval → Analysis → Wiki
                                    ↓
                          Markdown (readable)
                          PageIndex (retrieval)
```

**Trust Model:**
- Canonical Document = Source of Truth
- Markdown = Human-readable projection
- PageIndex = Retrieval projection
- Analysis Results = Derived knowledge (stored in wiki)

---

## 2. Core Concepts

### 2.1 Unified Source Model

All data sources are represented as **Source** entities with type-specific configuration:

```python
class Source:
    id: str
    name: str
    type: SourceType  # jira | confluence | file_upload
    config: SourceConfig  # Type-specific
    sync_state: SyncState
    created_at: datetime
    last_synced_at: Optional[datetime]

class SourceType(Enum):
    JIRA = "jira"
    CONFLUENCE = "confluence"
    FILE_UPLOAD = "file_upload"

class JiraSourceConfig:
    base_url: str
    credential_ref: str
    scope: JiraScope  # single_issue | project | jql

class ConfluenceSourceConfig:
    base_url: str
    credential_ref: str
    scope: ConfluenceScope  # single_page | space

class FileUploadSourceConfig:
    file_path: str
    file_type: str  # pdf | docx | xlsx | pptx | image
    parser: str = "mineru"  # mineru | pypdf | python-docx
```

### 2.2 Simplified Canonical Document

**Keep only retrieval-essential fields:**

```python
class CanonicalDocument:
    # Identity
    document_id: str

    # Provenance
    source_type: str
    source_id: str
    source_url: Optional[str]
    fetched_at: datetime

    # Access Control
    acl: ACL

    # Structure (for retrieval)
    structure: DocumentStructure  # sections | pages | slides | clauses

    # Content
    content_blocks: List[ContentBlock]

    # Removed: terminology, complex metadata, redundant fields
```

### 2.3 Incremental Sync Strategy

**Hybrid Approach:**

1. **Initial Sync** - Cursor-based pagination
   - Fetch all items in batches
   - Store cursor for next batch
   - Build complete initial index

2. **Subsequent Syncs** - Time-based increments
   - Query `updated >= last_sync_time`
   - Fetch only changed items
   - Update/add to existing index

```python
class SyncState:
    last_sync_time: Optional[datetime]
    cursor: Optional[str]  # For initial sync
    total_items: int
    sync_status: SyncStatus  # initial | incremental | failed
```

### 2.4 Knowledge Base Organization

**Mixed Hierarchy:**

```
workspace/
  knowledge/
    issues/
      {issue_id}/
        analysis.md          # Deep analysis result
        metadata.json        # Provenance, timestamp, citations
    reports/
      daily/
        {date}/
          report.md          # Daily report
          metadata.json
      weekly/
        {date}/
          report.md          # Future: weekly rollup
          metadata.json
```

**Features:**
- Cross-type retrieval (search across issues and reports)
- Citation tracking (link back to source documents)
- Version history (keep analysis evolution)

---

## 3. Source Connectors

### 3.1 Unified Connector Interface

All connectors implement:

```python
class SourceConnector(ABC):
    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Verify credentials and connectivity"""
        pass

    @abstractmethod
    async def fetch_initial(self, cursor: Optional[str] = None) -> FetchResult:
        """Initial sync with cursor pagination"""
        pass

    @abstractmethod
    async def fetch_incremental(self, since: datetime) -> FetchResult:
        """Incremental sync based on update time"""
        pass

    @abstractmethod
    def to_canonical(self, raw_data: Any) -> CanonicalDocument:
        """Convert source format to canonical document"""
        pass
```

### 3.2 Jira Connector

**Scope Options:**
- Single Issue: `issue_key = "SSD-777"`
- Project: `project = "SSD"`
- JQL Query: `jql = "project = SSD AND updated >= -7d"`

**Incremental Strategy:**
```python
# Initial: Paginate through all issues
GET /rest/api/3/search?jql=project=SSD&startAt=0&maxResults=100

# Incremental: Query by update time
GET /rest/api/3/search?jql=project=SSD AND updated >= '2026-04-19'
```

### 3.3 Confluence Connector

**Scope Options:**
- Single Page: `page_id = "123456"`
- Space: `space_key = "ENG"`

**Incremental Strategy:**
```python
# Initial: Paginate through space
GET /rest/api/content?spaceKey=ENG&limit=100&start=0

# Incremental: Query by update time
GET /rest/api/content?spaceKey=ENG&expand=version&lastModified>=2026-04-19
```

### 3.4 File Upload Connector

**Processing:**
1. User uploads file via Web UI
2. File saved to workspace storage
3. MinerU processes file automatically
4. Canonical document created
5. Markdown/PageIndex generated

**Supported Types:**
- PDF (MinerU primary, pypdf fallback)
- Office (DOCX, XLSX, PPTX via MinerU)
- Images (OCR via MinerU)

**Intelligent Fallback:**
```python
def process_file(file_path: str) -> CanonicalDocument:
    try:
        # Try MinerU first
        return mineru_parser.parse(file_path)
    except MinerUError as e:
        logger.warning(f"MinerU failed: {e}, falling back")
        if file_path.endswith('.pdf'):
            return pypdf_parser.parse(file_path)
        elif file_path.endswith('.docx'):
            return python_docx_parser.parse(file_path)
        else:
            raise UnsupportedFileTypeError()
```

---

## 4. Retrieval System

### 4.1 Multi-Strategy Retrieval

**Available Strategies:**

1. **BM25 Only** - Fast keyword matching
2. **Semantic Only** - Dense vector similarity
3. **Hybrid** - Weighted combination (current default)
4. **Structure-Aware** - Boost by document structure (sections, clauses, tables)
5. **LLM Reranking** - Use local LLM to reorder top-K results

### 4.2 Golden Dataset Evaluation

**Purpose:** Measure and improve retrieval quality

**Dataset Structure:**
```yaml
golden_queries:
  - id: "jira-root-cause-1"
    query: "Why did the NVMe flush command fail?"
    source_type: "jira"
    expected_documents:
      - document_id: "SSD-777"
        relevance: 1.0
      - document_id: "SSD-778"
        relevance: 0.8

  - id: "spec-lookup-1"
    query: "What is the NVMe flush command format?"
    source_type: "pdf"
    expected_documents:
      - document_id: "nvme-spec-1.4.pdf#page=123"
        relevance: 1.0
```

**Evaluation Metrics:**
- **Recall@5** - Are relevant docs in top 5?
- **Precision@5** - How many top 5 are relevant?
- **MRR (Mean Reciprocal Rank)** - Position of first relevant doc

**Evaluation Levels:**

```
Level 1: Automated Evaluation
  - Run Golden Dataset queries
  - Compute Recall@5, Precision@5, MRR
  - Compare across strategies
  - Fast iteration (< 1 minute)

Level 2: Strategy Comparison
  - BM25 vs Semantic vs Hybrid vs Structure-Aware vs Reranking
  - Identify best strategy per query type
  - Tune weights and parameters

Level 3: Human Validation
  - Real engineer scenarios
  - Collect feedback on result quality
  - Expand Golden Dataset
  - Continuous improvement
```

### 4.3 Retrieval API

```python
class RetrievalService:
    async def search(
        self,
        query: str,
        strategy: RetrievalStrategy = "hybrid",
        top_k: int = 5,
        filters: Optional[SearchFilters] = None
    ) -> SearchResult:
        """Execute search with specified strategy"""
        pass

    async def evaluate(
        self,
        golden_dataset: GoldenDataset,
        strategies: List[RetrievalStrategy]
    ) -> EvaluationReport:
        """Evaluate retrieval quality"""
        pass
```

---

## 5. Analysis Features

### 5.1 Single Jira Deep Analysis

**User Flow:**
1. User selects a Jira issue in Web UI
2. Clicks "Deep Analysis" button
3. System retrieves related context (specs, related issues, Confluence pages)
4. Local LLM generates comprehensive analysis
5. Result saved to `workspace/knowledge/issues/{issue_id}/analysis.md`

**Analysis Structure:**
```markdown
# Deep Analysis: SSD-777

**Issue:** NVMe flush command failure
**Analyzed:** 2026-04-20 10:30:00
**Analyst:** LM Studio (qwen-9b)

## Summary
[One-paragraph executive summary]

## Root Cause Analysis
[Detailed technical analysis with citations]

## Related Context
- Spec Reference: NVMe 1.4 Spec §5.3.2 [citation]
- Related Issues: SSD-778, SSD-779 [citations]
- Design Docs: Confluence page "Flush Command Design" [citation]

## Recommendations
[Actionable next steps]

## Citations
[Full citation list with source links]
```

### 5.2 Daily Report (Progressive Generation)

**User Flow:**
1. User clicks "Generate Daily Report" in Web UI
2. System immediately returns **fast report** (< 5 seconds)
3. Background task starts **deep analysis** for each issue
4. UI shows progress indicator
5. Report **auto-upgrades** as deep analysis completes
6. Final report saved to `workspace/knowledge/reports/daily/{date}/report.md`

**Progressive Generation:**

```python
async def generate_daily_report(date: str) -> DailyReport:
    # Phase 1: Fast Report (< 5 seconds)
    issues = fetch_issues_updated_today(date)
    fast_report = generate_fast_summary(issues)
    yield fast_report  # Return immediately to user

    # Phase 2: Background Deep Analysis
    for issue in issues:
        deep_analysis = await analyze_issue_deep(issue)
        fast_report.upgrade_issue(issue.id, deep_analysis)
        yield fast_report  # Push update to UI via WebSocket

    # Phase 3: Final Summary
    final_summary = await generate_executive_summary(fast_report)
    fast_report.set_summary(final_summary)
    yield fast_report  # Final version
```

**Report Structure:**
```markdown
# Daily Report - 2026-04-20

**Generated:** 10:00:00 (Fast) → 10:15:00 (Complete)
**Issues Analyzed:** 12

## Executive Summary
[Auto-generated summary of key findings]

## Issues Updated Today

### SSD-777: NVMe flush command failure
**Status:** In Progress → Resolved
**Priority:** P0
**Quick Summary:** [Fast extraction from issue fields]
**Deep Analysis:** [Background analysis result - auto-upgraded]
**Citations:** [Spec references, related issues]

### SSD-778: ...
[Similar structure]

## Metrics
- Issues closed: 5
- Issues opened: 3
- P0 issues: 2
- Average resolution time: 3.2 days

## Citations
[Full citation list]
```

---

## 6. API Design

### 6.1 RESTful Resources

**Sources:**
```
GET    /api/sources              # List all sources
POST   /api/sources              # Create new source
GET    /api/sources/{id}         # Get source details
PUT    /api/sources/{id}         # Update source config
DELETE /api/sources/{id}         # Delete source
POST   /api/sources/{id}/test    # Test connection
POST   /api/sources/{id}/sync    # Trigger sync
GET    /api/sources/{id}/status  # Get sync status
```

**Knowledge Base:**
```
GET    /api/knowledge/issues                    # List issue analyses
GET    /api/knowledge/issues/{issue_id}         # Get issue analysis
GET    /api/knowledge/reports/daily             # List daily reports
GET    /api/knowledge/reports/daily/{date}      # Get daily report
```

### 6.2 Task Endpoints

**Complex Operations:**
```
POST   /api/analysis/deep-analyze
  Body: { issue_id: "SSD-777", include_specs: true }
  Returns: { task_id: "...", status: "running" }

POST   /api/reports/daily
  Body: { date: "2026-04-20", auto_analyze: true }
  Returns: { task_id: "...", status: "running" }

GET    /api/tasks/{task_id}
  Returns: { status: "running|completed|failed", progress: 0.75, result: {...} }
```

### 6.3 WebSocket Updates

**Real-time Progress:**
```javascript
ws://localhost:8000/ws/tasks/{task_id}

// Messages:
{ type: "progress", value: 0.25, message: "Analyzing issue 3/12" }
{ type: "partial_result", data: { ... } }
{ type: "completed", result: { ... } }
{ type: "error", error: "..." }
```

---

## 7. Web UI Design

### 7.1 Smart Configuration Wizard

**Jira/Confluence Flow:**
```
Step 1: Basic Info
  - Name: "Production Jira"
  - Type: [Jira | Confluence]

Step 2: Authentication
  - Base URL: https://jira.example.com
  - Token: [secure input]
  - [Test Connection] button

Step 3: Scope Configuration
  For Jira:
    - ( ) Single Issue: [SSD-777]
    - ( ) Project: [SSD]
    - ( ) JQL Query: [custom query]

  For Confluence:
    - ( ) Single Page: [123456]
    - ( ) Space: [ENG]

Step 4: Initial Sync
  - [Start Sync] button
  - Progress bar with live updates
  - "Fetched 150/500 items..."
```

**File Upload Flow:**
```
Step 1: Upload File
  - Drag & drop or file picker
  - Supported: PDF, DOCX, XLSX, PPTX, Images

Step 2: Auto-Processing
  - "Processing with MinerU..."
  - Progress indicator
  - "Extracted 45 pages, 12 tables, 8 images"

Step 3: Complete
  - Preview Markdown
  - [Add to Knowledge Base] button
```

### 7.2 Analysis Dashboard

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  [Sources] [Analysis] [Reports] [Search]                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Recent Issues                    Quick Actions         │
│  ┌──────────────────────┐        ┌──────────────────┐  │
│  │ SSD-777: Flush fail  │        │ [Deep Analysis]  │  │
│  │ Status: In Progress  │        │ [Daily Report]   │  │
│  │ Updated: 2h ago      │        │ [Search Specs]   │  │
│  └──────────────────────┘        └──────────────────┘  │
│                                                          │
│  Daily Report - 2026-04-20                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ⏳ Generating... (8/12 issues analyzed)            │ │
│  │                                                     │ │
│  │ ✅ SSD-777: Analysis complete                      │ │
│  │ ⏳ SSD-778: Analyzing...                           │ │
│  │ ⏳ SSD-779: Queued                                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Simplifications

### 8.1 Removed Complexity

**Cache/Snapshot Mechanism:**
- **Before:** Complex multi-layer caching with manifest.json, documents.json, page_index.json
- **After:** Simple sync state tracking, rebuild indexes on demand
- **Rationale:** Premature optimization, adds complexity without proven benefit

**Export Formats:**
- **Before:** Multiple export formats (Markdown, JSON, custom)
- **After:** Internal format only, export on demand
- **Rationale:** YAGNI - no current use case for multiple formats

**Canonical Document Fields:**
- **Before:** Rich metadata, terminology, complex structure
- **After:** Minimal fields for retrieval (provenance, ACL, structure, content)
- **Rationale:** Keep only what's needed for search and citation

### 8.2 Deferred Features

**Not in Scope (Current Phase):**
- Confluence write-back
- Multi-team orchestration
- Hosted service / SaaS
- Advanced clustering and summarization
- Production OCR pipeline
- Real-time collaboration

**Rationale:** Focus on core value first, expand later based on user feedback

---

## 9. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Basic source management and sync

**Deliverables:**
- [ ] Unified Source model and API
- [ ] Jira connector with incremental sync
- [ ] Confluence connector with incremental sync
- [ ] File upload with MinerU integration
- [ ] Smart configuration wizard UI
- [ ] Basic sync status dashboard

**Acceptance Criteria:**
- User can add Jira/Confluence sources via UI
- User can upload PDF and see parsed content
- Incremental sync works correctly
- All sources produce canonical documents

### Phase 2: Retrieval (Weeks 3-4)

**Goal:** Multi-strategy retrieval with evaluation

**Deliverables:**
- [ ] Golden Dataset (20-50 queries)
- [ ] BM25, Semantic, Hybrid strategies
- [ ] Structure-aware retrieval
- [ ] LLM reranking
- [ ] Automated evaluation framework
- [ ] Strategy comparison dashboard

**Acceptance Criteria:**
- Recall@5 > 0.8 on Golden Dataset
- User can compare retrieval strategies
- Evaluation runs in < 1 minute

### Phase 3: Analysis (Weeks 5-6)

**Goal:** Deep analysis and daily reports

**Deliverables:**
- [ ] Single Jira deep analysis
- [ ] Daily report with progressive generation
- [ ] Knowledge base storage
- [ ] WebSocket real-time updates
- [ ] Analysis results UI

**Acceptance Criteria:**
- Deep analysis completes in < 30 seconds
- Daily report fast version in < 5 seconds
- Background analysis auto-upgrades report
- Results saved to knowledge base

### Phase 4: Polish (Week 7)

**Goal:** Production-ready UX

**Deliverables:**
- [ ] Error handling and retry logic
- [ ] Loading states and progress indicators
- [ ] Comprehensive documentation
- [ ] End-to-end testing
- [ ] Performance optimization

**Acceptance Criteria:**
- All error cases handled gracefully
- UI feels responsive and polished
- Documentation complete
- E2E tests pass

---

## 10. Success Metrics

### 10.1 Technical Metrics

**Retrieval Quality:**
- Recall@5 > 0.8 (80% of relevant docs in top 5)
- Precision@5 > 0.6 (60% of top 5 are relevant)
- MRR > 0.7 (first relevant doc in top 2 on average)

**Performance:**
- Source sync: < 1 minute for 100 issues
- Deep analysis: < 30 seconds per issue
- Daily report (fast): < 5 seconds
- Daily report (complete): < 5 minutes for 20 issues

**Reliability:**
- Sync success rate > 95%
- MinerU fallback rate < 10%
- API uptime > 99%

### 10.2 User Experience Metrics

**Ease of Use:**
- Time to first analysis: < 5 minutes (from zero)
- Configuration steps: < 5 clicks
- Error recovery: < 2 clicks

**Value Delivery:**
- Deep analysis provides actionable insights
- Daily report saves > 30 minutes of manual work
- Search finds relevant docs in < 3 tries

---

## 11. Open Questions

### 11.1 To Be Defined

**Golden Dataset:**
- Exact query set (need real engineer input)
- Relevance scoring methodology
- Update frequency

**MinerU Fallback:**
- Specific error conditions for fallback
- Quality comparison metrics
- User notification strategy

**Knowledge Base:**
- Retention policy (how long to keep analyses?)
- Version history depth
- Search indexing strategy

### 11.2 Future Considerations

**Scalability:**
- How many sources can one workspace handle?
- Index size limits?
- Background job queue capacity?

**Multi-User:**
- Shared workspaces?
- Access control per source?
- Collaboration features?

---

## 12. Migration from Current System

### 12.1 Compatibility

**Preserve:**
- Canonical document format (simplified but compatible)
- PageIndex format (`{"entries": [...]}`)
- ACL model
- Source authority hierarchy

**Deprecate:**
- Complex snapshot/cache mechanism
- CLI-first workflows (keep CLI but secondary)
- Multiple export formats

### 12.2 Migration Path

**Phase 1: Parallel Run**
- New system runs alongside old
- Validate output equivalence
- Gradual user migration

**Phase 2: Feature Parity**
- All old features available in new system
- Documentation updated
- Training materials ready

**Phase 3: Cutover**
- Old system deprecated
- Data migrated to new format
- Old code archived

---

## 13. Appendix

### 13.1 Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (API framework)
- SQLite (local storage)
- MinerU (PDF/Office parsing)
- BM25 + Sentence Transformers (retrieval)
- LM Studio (local LLM)

**Frontend:**
- React 18
- TypeScript
- TanStack Query (data fetching)
- Tailwind CSS (styling)
- WebSocket (real-time updates)

**Infrastructure:**
- Local-first (no cloud dependency)
- Git-based workspace storage
- File-based knowledge base

### 13.2 References

**Inspiration:**
- Onyx: Unified connector interface, incremental sync
- Perplexity: Progressive answer generation
- Notion: Smart configuration wizards

**Prior Art:**
- `replan-markdown-pageindex-local-llm.md` - Phase A-D foundation
- `architecture-overview.md` - Original architecture
- `P0-completion-status.md` - Current implementation status

---

## Document History

- **2026-04-20:** Initial version based on 15-question design session
- **Future:** To be updated as implementation progresses
