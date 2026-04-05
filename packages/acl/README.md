# ACL Package

This package defines the ACL propagation and enforcement contract for all knowledge documents.

## Contract Rules

- Deny by default.
- ACL metadata is required on every normalized document.
- Child objects inherit ACL from the nearest explicit parent when not overridden.
- Retrieval must filter unauthorized content before reranking.
- Answer assembly must never include evidence from filtered candidates.

## Enforcement Expectations

- ACL inheritance must be explicit and testable.
- Negative tests must confirm unauthorized users cannot retrieve protected evidence.
- The ACL contract must remain independent from ranking and retrieval implementation details.

