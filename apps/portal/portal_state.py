from __future__ import annotations

from pathlib import Path
import json

from services.eval.harness import evaluate_dataset
from services.retrieval.citations.assembler import assemble_citation, build_source_inspection
from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index
from services.workspace.workspace import inspect_workspace_run, list_workspace_runs, load_workspace_run_artifact


DEFAULT_POLICIES = {"team:ssd", "public"}


def _fallback_task_workbench(search_workspace: list[dict], evaluation_health: dict) -> dict:
    selected_task_id = "run-ssd-102-v1"
    top_result = search_workspace[0] if search_workspace else {}
    return {
        "new_task_entry": {
            "default_task_type": "jira_deep_analysis",
            "input_hint": "Enter a Jira issue key and select reusable spec assets before running.",
            "available_task_types": ["jira_deep_analysis"],
        },
        "filters": {
            "status": ["queued", "running", "completed", "stopped", "failed"],
            "owner": ["alice", "ssd-team"],
            "project": ["SSD"],
            "issue_key": "SSD-102",
            "updated_time": "last_7_days",
        },
        "selected_task_id": selected_task_id,
        "tasks": [
            {
                "task_id": selected_task_id,
                "task_type": "jira_deep_analysis",
                "issue_key": "SSD-102",
                "project": "SSD",
                "owner": "alice",
                "status": "completed",
                "updated_at": "2026-04-15T00:00:00Z",
                "selected": True,
                "summary": "Cross-source analysis completed with reusable spec and Confluence evidence.",
            },
            {
                "task_id": "run-ssd-103-v1",
                "task_type": "jira_deep_analysis",
                "issue_key": "SSD-103",
                "project": "SSD",
                "owner": "ssd-team",
                "status": "stopped",
                "updated_at": "2026-04-14T18:15:00Z",
                "selected": False,
                "summary": "Stopped after retrieval; partial artifacts are preserved for resume.",
            },
        ],
        "task_details_by_id": {
            selected_task_id: {
                "detail_tabs": [
                    {
                        "id": "overview",
                        "label": "Overview",
                        "content": "Jira deep analysis run with checkpointed retrieval, analysis, and knowledge outputs.",
                    },
                    {
                        "id": "logs",
                        "label": "Logs",
                        "content": "retrieval_ready -> analysis_ready -> knowledge_ready",
                    },
                    {
                        "id": "runtime",
                        "label": "Runtime",
                        "content": _runtime_content({}, {}),
                    },
                    {
                        "id": "evidence",
                        "label": "Evidence",
                        "content": f"Top evidence: {top_result.get('document_id', 'none')}",
                    },
                    {
                        "id": "report",
                        "label": "Report",
                        "content": "Composite report is available with four section tabs.",
                    },
                    {
                        "id": "knowledge",
                        "label": "Knowledge",
                        "content": "Draft Confluence update proposal, wiki draft, and concept cards are ready for review.",
                    },
                ],
                "report_tabs": [
                    {"id": "rca", "label": "RCA", "status": "ready"},
                    {"id": "spec_impact", "label": "Spec Impact", "status": "ready"},
                    {"id": "decision_brief", "label": "Decision Brief", "status": "ready"},
                    {"id": "general_summary", "label": "General Summary", "status": "ready"},
                ],
                "knowledge_panels": [
                    {
                        "id": "confluence_update_proposal",
                        "label": "Confluence Update Proposal",
                        "status": "draft",
                    },
                    {"id": "wiki_draft", "label": "Wiki Draft", "status": "draft"},
                    {"id": "concept_cards", "label": "Concept Cards", "status": "draft"},
                ],
                "control_events": [],
                "artifact_inventory": [],
                "command_recipes": [],
                "retrieval_comparison": {
                    "engine": "pageindex",
                    "query": "SSD-102 NAND write telemetry",
                    "top_hits": [row["document_id"] for row in search_workspace[:3]],
                    "hit_quality": None,
                    "readability": None,
                    "citation_fidelity": evaluation_health.get("citation_fidelity"),
                },
                "controls": ["stop", "resume", "rerun"],
            }
        },
        "detail_tabs": [
            {
                "id": "overview",
                "label": "Overview",
                "content": "Jira deep analysis run with checkpointed retrieval, analysis, and knowledge outputs.",
            },
            {
                "id": "logs",
                "label": "Logs",
                "content": "retrieval_ready -> analysis_ready -> knowledge_ready",
            },
            {
                "id": "runtime",
                "label": "Runtime",
                "content": _runtime_content({}, {}),
            },
            {
                "id": "evidence",
                "label": "Evidence",
                "content": f"Top evidence: {top_result.get('document_id', 'none')}",
            },
            {
                "id": "report",
                "label": "Report",
                "content": "Composite report is available with four section tabs.",
            },
            {
                "id": "knowledge",
                "label": "Knowledge",
                "content": "Draft Confluence update proposal, wiki draft, and concept cards are ready for review.",
            },
        ],
        "report_tabs": [
            {"id": "rca", "label": "RCA", "status": "ready"},
            {"id": "spec_impact", "label": "Spec Impact", "status": "ready"},
            {"id": "decision_brief", "label": "Decision Brief", "status": "ready"},
            {"id": "general_summary", "label": "General Summary", "status": "ready"},
        ],
        "knowledge_panels": [
            {
                "id": "confluence_update_proposal",
                "label": "Confluence Update Proposal",
                "status": "draft",
            },
            {"id": "wiki_draft", "label": "Wiki Draft", "status": "draft"},
            {"id": "concept_cards", "label": "Concept Cards", "status": "draft"},
        ],
        "control_events": [],
        "artifact_inventory": [],
        "command_recipes": [],
        "retrieval_comparison": {
            "engine": "pageindex",
            "query": "SSD-102 NAND write telemetry",
            "top_hits": [row["document_id"] for row in search_workspace[:3]],
            "hit_quality": None,
            "readability": None,
            "citation_fidelity": evaluation_health.get("citation_fidelity"),
        },
        "controls": ["stop", "resume", "rerun"],
    }


def _artifact_status(rows: list[dict], artifact_type: str) -> str:
    match = next((row for row in rows if row["artifact_type"] == artifact_type), None)
    if not match:
        return "missing"
    if match.get("stale"):
        return "stale"
    return "ready" if match.get("exists") else "missing"


def _artifact_path(rows: list[dict], artifact_type: str) -> str | None:
    match = next((row for row in rows if row["artifact_type"] == artifact_type), None)
    if not match:
        return None
    path = match.get("path")
    return str(path).replace("\\", "/") if path else None


def _artifact_preview(workspace_dir: str | Path, run_id: str, artifact_type: str) -> str | None:
    try:
        artifact = load_workspace_run_artifact(workspace_dir, run_id, artifact_type)
    except ValueError:
        return None

    if artifact["format"] == "text":
        content = str(artifact["content"]).strip()
        return "\n".join(content.splitlines()[:6]).strip() or None

    payload = artifact["payload"]
    if artifact_type.startswith("section_output_"):
        answer = payload.get("answer", {}).get("text", "")
        return answer.strip() or None
    if artifact_type == "confluence_update_proposal":
        action = payload.get("knowledge_action", "unknown")
        delta = payload.get("proposed_delta", "")
        return f"Action: {action} — {delta}".strip()
    if artifact_type == "concept_cards":
        cards = payload.get("cards", [])
        if not cards:
            return "No concept cards generated."
        return f"{len(cards)} card(s): {cards[0].get('summary', '')}".strip()
    return json.dumps(payload, ensure_ascii=False)[:240]


def _runtime_content(runtime: dict, prefect_runtime: dict) -> str:
    return (
        f"Adapter: {runtime.get('adapter', 'none')}.\n"
        f"Prefect state: {prefect_runtime.get('prefect_state', 'n/a')}.\n"
        f"Adapter state: {prefect_runtime.get('adapter_state', 'n/a')}.\n"
        f"Flow run id: {prefect_runtime.get('flow_run_id', 'n/a')}.\n"
        f"Deployment: {prefect_runtime.get('deployment_identifier') or prefect_runtime.get('deployment_name', 'n/a')}."
    )


def _build_run_detail_bundle(
    *,
    workspace_dir: str | Path,
    run: dict,
    detail: dict,
    search_workspace: list[dict],
    evaluation_health: dict,
) -> dict:
    artifacts = detail["artifact_inventory"]
    result_summary = detail["result_summary"]
    control_events = detail["control_events"]
    reached_checkpoints = run["checkpoint_summary"]["reached"]
    runtime = detail["manifest"].get("runtime", {})
    prefect_runtime = runtime.get("prefect", {})
    top_result = search_workspace[0] if search_workspace else {}
    shared_retrieval_preview = _artifact_preview(workspace_dir, run["run_id"], "shared_retrieval_bundle")
    report_preview = _artifact_preview(workspace_dir, run["run_id"], "composite_report")
    proposal_preview = _artifact_preview(workspace_dir, run["run_id"], "confluence_update_proposal")
    wiki_draft_preview = _artifact_preview(workspace_dir, run["run_id"], "wiki_draft")
    concept_card_preview = _artifact_preview(workspace_dir, run["run_id"], "concept_cards")

    return {
        "detail_tabs": [
            {
                "id": "overview",
                "label": "Overview",
                "content": (
                    f"{run['task_type']} for {run.get('issue_key') or result_summary.get('issue_id')}.\n"
                    f"Checkpoints reached: {', '.join(reached_checkpoints) or 'none'}."
                ),
            },
            {
                "id": "logs",
                "label": "Logs",
                "content": (
                    f"{len(control_events)} control event(s) recorded."
                    + (
                        f" Last event: {control_events[-1]['action']} by {control_events[-1]['requested_by']}."
                        if control_events
                        else ""
                    )
                ),
            },
            {
                "id": "runtime",
                "label": "Runtime",
                "content": _runtime_content(runtime, prefect_runtime),
            },
            {
                "id": "evidence",
                "label": "Evidence",
                "content": shared_retrieval_preview or f"Top evidence: {top_result.get('document_id', 'none')}",
            },
            {
                "id": "report",
                "label": "Report",
                "content": (
                    (report_preview or f"Composite report is {_artifact_status(artifacts, 'composite_report')}.")
                    + (
                        f"\nArtifact: {_artifact_path(artifacts, 'section_output_rca')}"
                        if _artifact_path(artifacts, "section_output_rca")
                        else ""
                    )
                ),
            },
            {
                "id": "knowledge",
                "label": "Knowledge",
                "content": proposal_preview or f"Knowledge proposal is {_artifact_status(artifacts, 'confluence_update_proposal')}.",
            },
        ],
        "report_tabs": [
            {
                "id": "rca",
                "label": "RCA",
                "status": _artifact_status(artifacts, "section_output_rca"),
                "preview": _artifact_preview(workspace_dir, run["run_id"], "section_output_rca"),
            },
            {
                "id": "spec_impact",
                "label": "Spec Impact",
                "status": _artifact_status(artifacts, "section_output_spec_impact"),
                "preview": _artifact_preview(workspace_dir, run["run_id"], "section_output_spec_impact"),
            },
            {
                "id": "decision_brief",
                "label": "Decision Brief",
                "status": _artifact_status(artifacts, "section_output_decision_brief"),
                "preview": _artifact_preview(workspace_dir, run["run_id"], "section_output_decision_brief"),
            },
            {
                "id": "general_summary",
                "label": "General Summary",
                "status": _artifact_status(artifacts, "section_output_general_summary"),
                "preview": _artifact_preview(workspace_dir, run["run_id"], "section_output_general_summary"),
            },
        ],
        "knowledge_panels": [
            {
                "id": "confluence_update_proposal",
                "label": "Confluence Update Proposal",
                "status": _artifact_status(artifacts, "confluence_update_proposal"),
                "preview": proposal_preview,
            },
            {
                "id": "wiki_draft",
                "label": "Wiki Draft",
                "status": _artifact_status(artifacts, "wiki_draft"),
                "preview": wiki_draft_preview,
            },
            {
                "id": "concept_cards",
                "label": "Concept Cards",
                "status": _artifact_status(artifacts, "concept_cards"),
                "preview": concept_card_preview,
            },
        ],
        "control_events": [
            {
                "action": event.get("action", "unknown"),
                "created_at": event.get("created_at"),
                "requested_by": event.get("requested_by"),
                "summary": json.dumps(event.get("result", {}), ensure_ascii=False)[:240],
            }
            for event in control_events
        ],
        "artifact_inventory": [
            {
                "artifact_type": row["artifact_type"],
                "status": row["status"],
                "stale": row["stale"],
                "path": str(row["path"]).replace("\\", "/") if row.get("path") else "",
            }
            for row in artifacts
        ],
        "command_recipes": [
            {
                "label": "Run detail",
                "command": f"python scripts/workspace_cli.py run-detail {workspace_dir} {run['run_id']}",
            },
            {
                "label": "Show report",
                "command": f"python scripts/workspace_cli.py run-artifact {workspace_dir} {run['run_id']} composite_report",
            },
            {
                "label": "Stop run",
                "command": f"python scripts/workspace_cli.py control-run {workspace_dir} {run['run_id']} --action stop --step-name manual",
            },
            {
                "label": "Resume run",
                "command": f"python scripts/workspace_cli.py control-run {workspace_dir} {run['run_id']} --action resume",
            },
            {
                "label": "Rerun section RCA",
                "command": f"python scripts/workspace_cli.py control-run {workspace_dir} {run['run_id']} --action rerun-section --step-name rca --execute",
            },
            {
                "label": "Sync Prefect state",
                "command": f"python scripts/workspace_cli.py sync-prefect-state {workspace_dir} {run['run_id']} --prefect-state Running --flow-run-id flow-{run['run_id']}",
            },
        ],
        "retrieval_comparison": {
            "engine": "pageindex",
            "query": run.get("issue_key") or result_summary.get("issue_id") or "workspace run",
            "top_hits": [row["document_id"] for row in search_workspace[:3]],
            "hit_quality": None,
            "readability": None,
            "citation_fidelity": evaluation_health.get("citation_fidelity"),
        },
        "controls": ["stop", "resume", "rerun", "rerun-section"],
    }


def _run_task_workbench(
    *,
    workspace_dir: str | Path,
    search_workspace: list[dict],
    evaluation_health: dict,
) -> dict | None:
    runs_payload = list_workspace_runs(workspace_dir)
    runs = runs_payload["runs"]
    if not runs:
        return None

    selected = runs[0]
    details_by_run_id = {
        run["run_id"]: _build_run_detail_bundle(
            workspace_dir=workspace_dir,
            run=run,
            detail=inspect_workspace_run(workspace_dir, run["run_id"]),
            search_workspace=search_workspace,
            evaluation_health=evaluation_health,
        )
        for run in runs
    }
    tasks = [
        {
            "task_id": run["run_id"],
            "task_type": run["task_type"],
            "issue_key": run.get("issue_key"),
            "project": (run.get("issue_key") or "").split("-", 1)[0] if run.get("issue_key") else None,
            "owner": run["owner"],
            "status": run["status"],
            "updated_at": run.get("updated_at"),
            "selected": run["run_id"] == selected["run_id"],
            "summary": (
                f"{run['checkpoint_summary']['reached_count']}/{run['checkpoint_summary']['total_count']} "
                f"checkpoints reached; {run['stale_artifact_count']} stale artifact(s)."
                + (
                    f" Runtime: {next((tab['content'].splitlines()[2].replace('Adapter state: ', '') for tab in details_by_run_id[run['run_id']]['detail_tabs'] if tab['id'] == 'runtime'), 'n/a')}"
                    if any(tab["id"] == "runtime" for tab in details_by_run_id[run["run_id"]]["detail_tabs"])
                    else ""
                )
            ),
        }
        for run in runs
    ]
    return {
        "new_task_entry": {
            "default_task_type": "jira_deep_analysis",
            "input_hint": "Enter a Jira issue key and select reusable spec assets before running.",
            "available_task_types": ["jira_deep_analysis"],
        },
        "filters": {
            "status": sorted({run["status"] for run in runs}),
            "owner": sorted({run["owner"] for run in runs}),
            "project": sorted({task["project"] for task in tasks if task["project"]}),
            "issue_key": selected.get("issue_key"),
            "updated_time": "workspace_runs",
        },
        "selected_task_id": selected["run_id"],
        "tasks": tasks,
        "task_details_by_id": details_by_run_id,
        "detail_tabs": details_by_run_id[selected["run_id"]]["detail_tabs"],
        "report_tabs": details_by_run_id[selected["run_id"]]["report_tabs"],
        "knowledge_panels": details_by_run_id[selected["run_id"]]["knowledge_panels"],
        "control_events": details_by_run_id[selected["run_id"]]["control_events"],
        "artifact_inventory": details_by_run_id[selected["run_id"]]["artifact_inventory"],
        "command_recipes": details_by_run_id[selected["run_id"]]["command_recipes"],
        "retrieval_comparison": details_by_run_id[selected["run_id"]]["retrieval_comparison"],
        "controls": details_by_run_id[selected["run_id"]]["controls"],
    }


def _build_task_workbench(
    *,
    search_workspace: list[dict],
    evaluation_health: dict,
    workspace_dir: str | Path | None,
) -> dict:
    if workspace_dir:
        workbench = _run_task_workbench(
            workspace_dir=workspace_dir,
            search_workspace=search_workspace,
            evaluation_health=evaluation_health,
        )
        if workbench:
            return workbench
    return _fallback_task_workbench(search_workspace, evaluation_health)


def build_portal_state(
    corpus_path: str | Path = "fixtures/retrieval/pageindex_corpus.json",
    dataset_path: str | Path = "eval/gold_queries.yaml",
    query: str = "nvme flush",
    allowed_policies: set[str] | None = None,
    workspace_dir: str | Path | None = None,
) -> dict:
    policies = allowed_policies or DEFAULT_POLICIES
    documents = load_documents(corpus_path)
    index = build_page_index(documents)
    search_results = search_page_index(index, query, policies, top_k=5)
    eval_report = evaluate_dataset(corpus_path, dataset_path, policies)

    source_counts: dict[str, int] = {}
    for document in documents:
        source_counts[document["source_type"]] = source_counts.get(document["source_type"], 0) + 1

    ingestion_status = [
        {
            "source_type": source_type,
            "status": "healthy",
            "document_count": count,
        }
        for source_type, count in sorted(source_counts.items())
    ]

    corpus_inventory = [
        {
            "document_id": document["document_id"],
            "title": document["title"],
            "source_type": document["source_type"],
            "authority_level": document["authority_level"],
            "version": document["version"],
            "language": document["language"],
        }
        for document in documents
    ]

    search_workspace = [
        {
            "document_id": result["document_id"],
            "title": result["title"],
            "authority_level": result["authority_level"],
            "scores": result["scores"],
            "citation": assemble_citation(result),
            "inspection": build_source_inspection(result),
        }
        for result in search_results
    ]

    citation_inspection = search_workspace[0]["inspection"] if search_workspace else {}
    return {
        "ingestion_status": ingestion_status,
        "corpus_inventory": corpus_inventory,
        "search_query": query,
        "search_workspace": search_workspace,
        "citation_inspection": citation_inspection,
        "evaluation_health": eval_report["aggregate"],
        "task_workbench": _build_task_workbench(
            search_workspace=search_workspace,
            evaluation_health=eval_report["aggregate"],
            workspace_dir=workspace_dir,
        ),
    }


def write_portal_state(
    output_path: str | Path = "apps/portal/portal_state.json",
    *,
    corpus_path: str | Path = "fixtures/retrieval/pageindex_corpus.json",
    dataset_path: str | Path = "eval/gold_queries.yaml",
    query: str = "nvme flush",
    allowed_policies: set[str] | None = None,
    workspace_dir: str | Path | None = None,
) -> Path:
    path = Path(output_path)
    path.write_text(
        json.dumps(
            build_portal_state(
                corpus_path=corpus_path,
                dataset_path=dataset_path,
                query=query,
                allowed_policies=allowed_policies,
                workspace_dir=workspace_dir,
            ),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path
