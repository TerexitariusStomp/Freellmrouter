# README Consolidation Design

Date: 2026-04-02

## Goal
Create a single canonical README at the repository root by replacing the current root README with the more complete subproject README, and remove the subproject README to avoid duplication.

## Scope
- Replace `README.md` at repo root with the content from `hermes_free_router/README.md`.
- Delete `hermes_free_router/README.md`.

## Non-Goals
- No changes to code, configuration, or behavior.
- No rewording beyond necessary path adjustments (none expected).

## Approach
Use the existing subproject README as the canonical document since it is comprehensive. Copy its content into the root README and delete the subproject README. This keeps a single source of truth and avoids maintaining duplicates.

## Files
- Modify: `README.md`
- Delete: `hermes_free_router/README.md`

## Risks and Mitigations
- Risk: Loss of unique root README info. Mitigation: root README currently contains a brief subset; replacing it with a more complete document is intended.

## Testing
- No tests required for documentation-only changes.
