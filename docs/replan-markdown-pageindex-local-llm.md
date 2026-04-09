# Markdown + PageIndex + Local LLM Replan

## 1. Project Goal

The near-stage goal is no longer a broad "Phase 1" that bundles portal, ops hardening, rollout gates, and later intelligence modules into one milestone.

The current single priority is to make Jira, Confluence, PPTX, and PDF sources flow through one stable foundation:

1. Convert each source into a canonical document with provenance, ACL, and first-class structure metadata.
2. Export readable Markdown from the same canonical document.
3. Derive a unified PageIndex from the same canonical document.
4. Let local LLM workflows consume only retrieval results and citation-bearing evidence derived from PageIndex search.

The trust model is:

- Canonical document is the source of truth.
- Markdown is the human-readable projection.
- PageIndex is the retrieval projection.
- Local LLM output is a consumer of retrieved evidence, not a source of data truth.

## 2. Non-Goals

The following work is explicitly outside the current critical path:

- Hosted portal or richer portal UX.
- Ops hardening beyond the minimum needed to preserve existing snapshot compatibility.
- Rollout gate expansion.
- Hosted services or database-backed storage.
- Request-scoped or identity-aware ACL beyond preserving the current ACL contract.
- Clustering, topic discovery, document summaries, and cluster summaries.
- Production OCR or local vision caption backends for images.
- Jira or Confluence write-back workflows.

Clustering and summarization remain valid later work, but only as derived enrichment after the source conversion, PageIndex, and retrieval-consumption seams are stable.

## 3. Current Alignment Gaps

`spec.md` still describes Phase 1 as a broad internal knowledge platform milestone with portal and ops gates as completion requirements. That is now too wide for the near-stage goal. The broad contract should remain useful context, but the immediate acceptance criteria must move to Markdown + PageIndex + local LLM consumption.

`todo.md` still follows the old Task 1 through Task 15 plan and places portal, observability, rollout gate automation, and deferred module contracts in the same delivery sequence. That makes the critical path too diffuse.

`docs/implementation-status.md` correctly records that many skeleton features exist, but it overstates broad Phase 1 completion relative to the new goal. The key alignment gaps identified during replanning were:

- Jira and Confluence currently produce Markdown first and then call `normalize_markdown_text(...)`, which is a lossy long-term canonicalization path.
- PPTX and PDF are closer to the target shape because their adapters build canonical documents directly before Markdown/PageIndex export.
- `page_index.json` needed one consistent artifact shape. This has been normalized for the skill-ready CLIs to `{"entries": [...]}`.
- Retrieval CLIs needed a direct PageIndex input path. `scripts/retrieval/toolkit_cli.py` and `scripts/platform_cli.py` search/citation now support direct `--page-index` input while keeping corpus-oriented defaults.
- Local LLM support is currently Jira-specific plus a PDF validation harness, not a source-generic retrieval-consumption surface.

`docs/architecture-overview.md` should be updated to name the three projection boundaries directly: canonical truth, readable Markdown projection, and PageIndex retrieval projection.

## 4. New Execution Phases

### Phase A: Conversion Foundation

**Goal**  
Jira, Confluence, PPTX, and PDF all reliably produce canonical document + readable Markdown + PageIndex from one canonical document.

**Inputs**  
Existing connector payload fixtures, office/PDF fixtures, canonical document contract, ACL/citation/provenance constraints.

**Outputs**  
Source-specific conversion paths with deterministic Markdown and PageIndex export for all four source types.

**Validation**  
Each source has at least one happy-path and one failure-path test proving canonical document creation, Markdown readability, and PageIndex derivation.

**Blockers**  
Jira and Confluence currently rely on Markdown round-tripping for canonicalization. This is acceptable temporarily, but not as the target architecture.

**Exit Criteria**  
All four source types can be exported through one CLI/API contract into canonical document, Markdown, and PageIndex without weakening ACL, citation, or provenance fields.

### Phase B: PageIndex Artifact Contract

**Goal**  
Make PageIndex a stable first-class artifact and runtime input.

**Inputs**  
`build_page_index(...)`, snapshot `page_index.json`, sync-export PageIndex output, normalize CLI PageIndex output.

**Outputs**  
One canonical PageIndex artifact shape, `{"entries": [...]}`, used by all exporters and loaders.

**Validation**  
Tests prove that PageIndex artifacts written by normalize CLI, sync-export, and snapshots have the same shape and can be read by retrieval code.

**Blockers**  
The original normalize CLI wrote a bare list while snapshot/sync-export wrote `{"entries": [...]}`. The artifact shape is now standardized in the skill-ready normalizer and retrieval toolkit; keep future exporters aligned to `{"entries": [...]}`.

**Exit Criteria**  
Retrieval can search/cite from a PageIndex artifact directly, without rebuilding from documents as the only supported path.

### Phase C: Unified Retrieval Surface

**Goal**  
Provide source-agnostic search, citation, and source inspection over Jira, Confluence, PPTX, and PDF content.

**Inputs**  
Canonical documents, canonical PageIndex artifacts, existing hybrid search and citation assembly.

**Outputs**  
Retrieval CLI/API that can consume either canonical document corpora or PageIndex artifacts, while preserving ACL pre-filtering and citation payloads.

**Validation**  
Fixture-backed tests search and cite evidence from all four source types.

**Blockers**  
Current retrieval toolkit is document-corpus-first and rebuilds PageIndex internally.

**Exit Criteria**  
One retrieval entrypoint supports search/citation/inspection across the four sources and returns ACL-safe cited evidence.

### Phase D: Local LLM Consumption

**Goal**  
Let local LLM workflows consume retrieval results for all four sources through one generic path.

**Inputs**  
Retrieval results, assembled citations, evidence spans, `services/analysis/llm_backends.py`.

**Outputs**  
A generic retrieval -> prompt assembly -> local LLM answer service. Jira-specific analysis becomes a profile on top of this service instead of a separate path.

**Validation**  
Mock LLM tests prove prompt assembly for Jira, Confluence, PPTX, and PDF without network dependency. Tests assert that prompts only include retrieved evidence.

**Blockers**  
Current LLM support is bound to Jira reports/Jira-plus-spec QA and PDF validation, not a shared source-generic seam.

**Exit Criteria**  
One local LLM entrypoint can answer from retrieved evidence for all four source types, with extractive/no-LLM behavior still available by default.

### Phase E: Index Optimization

**Goal**  
Reduce redundant indexing and decide how PageIndex relates to chunk and embedding indexes.

**Inputs**  
Stable canonical document and PageIndex artifact contracts.

**Outputs**  
Snapshot/cache-based index reuse, contextual chunking plan, and a clear relationship between PageIndex and later embedding/chunk indexes.

**Validation**  
Regression tests prove index reuse does not change ACL filtering, ranking defaults, or citation payloads.

**Blockers**  
Do not optimize before the artifact contract is stable.

**Exit Criteria**  
Index reuse and chunking can be added without changing canonical truth or PageIndex citation semantics.

### Phase F: Enrichment

**Goal**  
Add corpus-level clustering and summarization after the foundation is stable.

**Inputs**  
Stable retrieval surface, local LLM consumption surface, and optional optimized chunk/index artifacts.

**Outputs**  
Topic clusters, document summaries, and cluster summaries as enrichment artifacts.

**Validation**  
Tests prove enrichment artifacts reference source citations and never overwrite canonical document content.

**Blockers**  
Clustering and summarization must not precede stable ingestion/retrieval contracts.

**Exit Criteria**  
Enrichment remains a derived layer and cannot pollute canonical truth, Markdown projection, or PageIndex retrieval projection.

## 5. Support Matrix

| Source | Canonical doc | Markdown | PageIndex | Snapshot / ops | Local LLM |
| --- | --- | --- | --- | --- | --- |
| Jira | Current: direct payload-to-canonical builder implemented. Target: enrich structure fidelity further as needed. | Current: readable issue Markdown preserved as projection. Target: keep projection readable while canonical stays richer. | Current: buildable from document and artifact path is unified. Target: keep as direct retrieval input. | Current: supported through snapshot/ops flows. Target: support only, not critical path. | Current: Jira report and Jira-plus-spec QA, with spec QA already reusing the generic seam internally. Target: full profile over the generic retrieval-consumption service. |
| Confluence | Current: direct payload-to-canonical builder implemented for current storage-body fixture shapes. Target: expand fidelity for richer mixed-content pages. | Current: readable page Markdown preserved as projection. Target: keep projection readable while canonical stays richer. | Current: buildable from document and artifact path is unified. Target: keep as direct retrieval input. | Current: supported through snapshot/ops flows. Target: support only, not critical path. | Current: generic retrieval-consumption seam available through `retrieval-consume`. Target: richer source-specific profiles only where needed. |
| PPTX | Current: adapter builds canonical-like document directly. Target: stronger slide structure and metadata. | Current: exported through Markdown projection. Target: stable readable projection. | Current: buildable from document. Target: canonical `{"entries": [...]}` artifact and direct retrieval input. | Current: usable through corpus/snapshot paths. Target: support only, not critical path. | Current: no generic path. Target: generic retrieval-consumption profile. |
| PDF | Current: MinerU/pypdf path builds canonical-like document directly. Target: stable structural extractor with parser fallback documented. | Current: exported through Markdown projection. Target: stable readable projection. | Current: buildable from document. Target: canonical `{"entries": [...]}` artifact and direct retrieval input. | Current: usable through corpus/snapshot paths. Target: support only, not critical path. | Current: PDF validation harness only. Target: generic retrieval-consumption profile. |

## 6. Prioritized Roadmap

### P0: Must Do Now

- Update planning docs around Markdown + PageIndex + local LLM as the current milestone.
- Standardize PageIndex artifact shape to `{"entries": [...]}` everywhere. Current status: done for normalize CLI, sync-export, snapshot, and retrieval toolkit artifact loading.
- Add direct PageIndex load/search/citation support. Current status: done for `scripts/retrieval/toolkit_cli.py` and platform search/citation.
- Add four-source export tests for Markdown and PageIndex. Current status: done in the skill-ready CLI tests.
- Document Jira/Confluence Markdown-first canonicalization as temporary debt.

### P1: Foundation Closeout

- Done for current fixture-backed paths: direct Jira and Confluence payload-to-canonical builders are in place.
- Done: a source-generic retrieval-consumption service for local LLM answers is implemented.
- In progress: Jira-specific analysis commands are being reduced to profiles over the generic service. Jira spec QA and batch spec QA already reuse the generic seam internally.
- Done: mock-backed local LLM prompt tests for Confluence, PPTX, and PDF exist through generic retrieval-consumption tests.
- Remaining in this lane: richer fidelity for more complex Jira/Confluence source shapes and final cleanup of Jira orchestration/profile boundaries.

### P2: Later Enhancements

- Add snapshot/cache-based index reuse.
- Add contextual chunking.
- Decide PageIndex vs embedding/chunk index responsibilities.
- Add clustering and summarization as citation-backed enrichment artifacts.
- Revisit portal, ops hardening, and rollout gates once the foundation chain is stable.

## 7. Immediate Implementation Tasks

1. Add a generic retrieval-consumption service using existing LLM backends.
2. Refactor Jira analysis onto the generic retrieval-consumption seam.
3. Replace Jira/Confluence Markdown-first canonicalization with richer payload-to-canonical builders after artifact contracts are stable.
4. Add source-specific validation for richer page/table/clause extraction as those builders are introduced.
5. Add index reuse/contextual chunking only after the generic consumption seam is stable.
