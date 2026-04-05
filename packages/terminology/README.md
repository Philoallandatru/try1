# Terminology Package

Terminology handling is part of the normalized evidence model and must preserve lookup behavior across abbreviations, aliases, fields, commands, and error terms.

## Required Examples

- Abbreviation to full-term mapping, such as `FTL -> Flash Translation Layer`.
- Full-term to abbreviation lookup.
- Alias mapping for product, protocol, or subsystem names.
- Command names and parameter fields used in specifications.
- Error or status terms that must remain searchable.

## Contract Expectations

- Terminology must preserve the original term text and language.
- The normalized document model must be able to attach terminology metadata to source evidence.
- Retrieval and evaluation must support terminology lookups in both directions.

