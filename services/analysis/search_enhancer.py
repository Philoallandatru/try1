from __future__ import annotations


SECTION_CUES = {
    "rca": ["root cause", "failure mechanism", "error code", "workaround"],
    "spec_impact": ["spec clause", "requirement", "component impact", "validation"],
    "decision_brief": ["decision", "risk", "tradeoff", "next step"],
    "general_summary": ["summary", "context", "status", "evidence"],
}
MAX_VALUES_PER_FIELD = 3
MAX_ADDITIONS = 18
MAX_QUERY_CHARS = 500


def _field_values(document: dict, field_names: tuple[str, ...], *, max_values_per_field: int) -> list[str]:
    issue_fields = document.get("metadata", {}).get("issue_fields", {})
    values: list[str] = []
    for field_name in field_names:
        value = issue_fields.get(field_name)
        if isinstance(value, list):
            values.extend(str(item) for item in value[:max_values_per_field] if item)
        elif value:
            values.append(str(value))
    return values


def _bounded_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip()


def build_enhanced_search_query(
    *,
    base_query: str,
    jira_document: dict,
    section_name: str,
    scope_hint: str,
) -> dict:
    if section_name not in SECTION_CUES:
        expected = ", ".join(sorted(SECTION_CUES))
        raise ValueError(f"Unsupported section for search enhancement: {section_name}. Expected one of: {expected}")

    metadata = jira_document.get("metadata", {})
    additions = [
        metadata.get("issue_family"),
        metadata.get("issue_route"),
        *_field_values(
            jira_document,
            ("Component/s", "Labels", "Fix Version/s", "Affects Version/s"),
            max_values_per_field=MAX_VALUES_PER_FIELD,
        ),
        *SECTION_CUES[section_name],
        scope_hint,
    ]
    normalized_additions = [str(value).strip() for value in additions if str(value or "").strip()][:MAX_ADDITIONS]
    query_parts = [base_query, *normalized_additions]
    seen: set[str] = set()
    deduped_parts: list[str] = []
    for part in query_parts:
        key = part.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped_parts.append(part)
    query = _bounded_text(" ".join(deduped_parts).strip(), MAX_QUERY_CHARS)
    return {
        "base_query": base_query,
        "section_name": section_name,
        "scope_hint": scope_hint,
        "additions": normalized_additions,
        "bounds": {
            "max_values_per_field": MAX_VALUES_PER_FIELD,
            "max_additions": MAX_ADDITIONS,
            "max_query_chars": MAX_QUERY_CHARS,
        },
        "query": query,
    }
