"""
Jira-specific report profile configurations.

This module contains Jira-specific configurations for different report types,
separating domain logic from generic report generation.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


def build_jira_pm_issue_fact(
    document: dict,
    *,
    target_date: date,
    stale_threshold_hours: int,
) -> dict:
    """
    Build a PM-focused fact record from a Jira document.

    Args:
        document: Jira document
        target_date: Reference date for the report
        stale_threshold_hours: Hours threshold for staleness

    Returns:
        Fact dictionary with PM-relevant fields
    """
    from services.analysis.jira_issue_analysis import (
        _document_updated_at,
        _first_issue_field,
        _issue_field,
        _latest_comment,
        _pm_attention_signals,
    )

    updated_at = _document_updated_at(document)
    latest_comment = _latest_comment(document)
    reference_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    stale_cutoff = reference_end - timedelta(hours=stale_threshold_hours)
    updated_today = updated_at is not None and updated_at.date() == target_date
    stale = updated_at is None or updated_at < stale_cutoff
    attention_signals = _pm_attention_signals(document, stale=stale)

    return {
        "document_id": document["document_id"],
        "title": document.get("title", document["document_id"]),
        "owner": _first_issue_field(document, ["Assignee", "Owner"]) or "unknown",
        "priority": _issue_field(document, "Priority") or "unknown",
        "status": _issue_field(document, "Status") or "unknown",
        "updated_at": document.get("version") or "unknown",
        "updated_today": updated_today,
        "stale": stale,
        "latest_comment": latest_comment,
        "attention_signals": attention_signals,
    }


def render_jira_pm_issue_line(issue: dict) -> str:
    """
    Render a Jira issue as a multi-line PM report entry.

    Args:
        issue: Issue fact dictionary

    Returns:
        Formatted multi-line string
    """
    from services.analysis.jira_issue_analysis import _format_latest_comment

    return "\n".join(
        [
            f"- Issue: {issue['document_id']}",
            f"  Summary: {issue['title']}",
            f"  Owner: {issue['owner']}",
            f"  Priority: {issue['priority']}",
            f"  Status: {issue['status']}",
            f"  Updated: {issue['updated_at']}",
            f"  Latest comment: {_format_latest_comment(issue['latest_comment'])}",
            f"  Attention signals: {', '.join(issue['attention_signals']) or 'none'}",
        ]
    )


def render_jira_pm_attention_item(issue: dict) -> str:
    """
    Render a Jira issue as a one-line attention item.

    Args:
        issue: Issue fact dictionary

    Returns:
        Formatted one-line string
    """
    signals = ", ".join(issue["attention_signals"]) or "none"
    return f"{issue['document_id']}: {issue['title']} | owner={issue['owner']} | signals={signals}"


def build_jira_pm_executive_summary(
    *,
    reference_date: str,
    active_today: list[dict],
    in_progress_no_update: list[dict],
    attention_items: list[dict],
) -> list[str]:
    """
    Build executive summary for PM daily report.

    Args:
        reference_date: Reference date string
        active_today: List of issues updated today
        in_progress_no_update: List of in-progress issues without updates
        attention_items: List of issues needing attention

    Returns:
        List of summary bullet points
    """
    summary = [
        f"{len(active_today)} In Progress issue(s) were updated on {reference_date}.",
        f"{len(in_progress_no_update)} In Progress issue(s) had no same-day update.",
    ]
    if attention_items:
        summary.append(
            f"{len(attention_items)} issue(s) need manager attention: "
            + ", ".join(issue["document_id"] for issue in attention_items[:5])
            + "."
        )
    else:
        summary.append("No manager-attention signals were detected from deterministic rules.")
    return summary
