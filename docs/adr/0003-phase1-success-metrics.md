# ADR 0003: Phase 1 Success Metrics

## Status

Accepted

## Context

Phase 1 completion requires measurable retrieval quality, citation correctness, and operator workflow readiness. Informal checks are insufficient for release gating.

## Quality Thresholds

- `recall@10 >= 0.90`
- `nDCG@10 >= 0.80`
- `citation fidelity >= 0.95`
- `ACL negative test pass rate = 100%`
- Freshness SLA for Jira and Confluence within the agreed internal sync budget.
- Portal search success rate where all seeded smoke queries return cited results.

## Gold Set Coverage

- Clause lookup questions.
- Field or parameter lookup questions.
- Table hit questions.
- Version-difference questions.
- Terminology mapping questions.
- Chinese query to English spec retrieval.
- English query to Chinese design or requirement retrieval.
- Abbreviation to full-term retrieval.
- Full-term to abbreviation retrieval.

## Decision

These metrics are release gates. Phase 1 is incomplete until the gates pass and the corresponding evidence has been recorded.

