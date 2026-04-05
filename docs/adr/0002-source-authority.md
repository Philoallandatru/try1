# ADR 0002: Source Authority Model

## Status

Accepted

## Context

SSD knowledge retrieval must distinguish between normative evidence and background material. Ranking without an explicit authority model would allow non-normative or contextual content to outrank approved specifications and requirements.

## Authority Levels

- `canonical`: normative specifications, ratified standards, approved design baselines, approved product requirements.
- `supporting`: internal design notes, Jira discussions, Confluence explanations, design reviews, derived analyses.
- `contextual`: press releases, announcements, background articles, non-normative summaries.

## Ranking Rule

- Retrieval ranking must prefer `canonical` over `supporting`, and `supporting` over `contextual`.
- Contextual sources cannot outrank canonical sources unless the user explicitly requests background or non-normative context.
- A press release must never outrank a ratified NVMe or PCIe specification as the lead evidence source.

## Decision

The authority level is a first-class ranking signal and must be preserved through indexing, retrieval, reranking, and answer assembly.

