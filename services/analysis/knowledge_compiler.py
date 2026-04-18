from __future__ import annotations


def build_confluence_update_proposal(
    *,
    jira_document: dict,
    shared_citations: list[dict],
    confluence_citations: list[dict],
) -> dict:
    issue_id = jira_document["document_id"]
    title = jira_document.get("title", issue_id)
    candidate_pages = [
        {
            "page_id": citation["document"],
            "title": citation.get("title") or citation["document"],
            "space_key": None,
            "selection_reason": "Existing Confluence evidence was retrieved for this Jira issue.",
        }
        for citation in confluence_citations
    ]
    if not candidate_pages:
        candidate_pages.append(
            {
                "page_id": f"candidate-{issue_id.lower()}",
                "title": f"Knowledge target for {issue_id}: {title}",
                "space_key": None,
                "selection_reason": (
                    "No existing Confluence page was retrieved; review is required to choose "
                    "whether to create or map a target page."
                ),
            }
        )
    if not shared_citations:
        action = "no_change"
    elif confluence_citations:
        action = "revise"
    else:
        action = "add"
    return {
        "proposal_id": f"proposal-{issue_id.lower()}-v1",
        "source_issue_key": issue_id,
        "candidate_pages": candidate_pages,
        "knowledge_action": action,
        "proposed_delta": (
            f"{action.title()} Confluence knowledge with findings from Jira issue {issue_id}: {title}."
            if shared_citations
            else f"No Confluence update proposed for Jira issue {issue_id} because no secondary evidence was retrieved."
        ),
        "supporting_evidence": shared_citations,
        "confidence": 0.75 if shared_citations else 0.25,
        "open_questions": [] if shared_citations else ["No secondary evidence was retrieved for this proposal."],
        "status": "draft",
        "version": "v1",
    }


def build_concept_cards(*, jira_document: dict, shared_citations: list[dict]) -> dict:
    issue_id = jira_document["document_id"]
    title = jira_document.get("title", issue_id)
    if not shared_citations:
        return {"cards": []}
    return {
        "cards": [
            {
                "card_id": f"card-{issue_id.lower()}-risk",
                "label": f"{issue_id} knowledge risk",
                "category": "risk",
                "summary": f"Evidence-backed concept card derived from Jira issue: {title}",
                "evidence": [shared_citations[0]],
            }
        ]
    }


def build_wiki_draft_markdown(
    *,
    jira_document: dict,
    composite_report: dict,
    proposal: dict,
    concept_cards: dict,
) -> str:
    issue_id = jira_document["document_id"]
    lines = [
        f"# Wiki Draft: {issue_id}",
        "",
        "## Confluence Update Proposal",
        "",
        f"- Action: `{proposal['knowledge_action']}`",
        f"- Confidence: `{proposal['confidence']}`",
        f"- Proposed delta: {proposal['proposed_delta']}",
        "",
        "## Concept Cards",
        "",
    ]
    cards = concept_cards.get("cards", [])
    if cards:
        for card in cards:
            lines.append(f"- `{card['card_id']}` — {card['summary']}")
    else:
        lines.append("- No concept cards generated.")
    lines.extend(["", "## Composite Report", "", composite_report["content"]])
    return "\n".join(lines).strip()


def build_knowledge_artifacts(
    *,
    jira_document: dict,
    shared_citations: list[dict],
    confluence_citations: list[dict],
    composite_report: dict,
) -> dict:
    proposal = build_confluence_update_proposal(
        jira_document=jira_document,
        shared_citations=shared_citations,
        confluence_citations=confluence_citations,
    )
    concept_cards = build_concept_cards(
        jira_document=jira_document,
        shared_citations=shared_citations,
    )
    wiki_draft = build_wiki_draft_markdown(
        jira_document=jira_document,
        composite_report=composite_report,
        proposal=proposal,
        concept_cards=concept_cards,
    )
    return {
        "confluence_update_proposal": proposal,
        "concept_cards": concept_cards,
        "wiki_draft": {
            "format": "markdown",
            "content": wiki_draft,
        },
    }
