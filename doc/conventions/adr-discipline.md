# ADR discipline

Convention for writing and maintaining Architecture Decision Records under
`doc/adr/` (project-wide) and `apps/*/doc/adr/` (per-component).

ADR format follows Michael Nygard, *Documenting Architecture Decisions* (2011).
This document adds project-specific discipline.

## Core property: ADRs are immutable

An ADR records a decision at a point in time. Once **Accepted**, the body of
an ADR is treated as immutable. Permitted edits are limited to:

- Typos, broken links, formatting fixes.
- **Status transitions only** — Accepted → Deprecated → Superseded.
- Adding a back-reference to a superseding ADR (one line under "Status").

If the decision needs to change, write a **new ADR that supersedes it**. Do
not mutate the original. The git history of `doc/adr/` is the audit trail of
how the architecture evolved; in-place edits destroy that trail.

## What ADRs MUST NOT contain

These cause ADR rot. They belong elsewhere — see "Where mutable content
lives" below.

- **"Where the project stands today" / current-state notes.** The world
  changes; the ADR doesn't. Current state goes in `HARNESS.md`.
- **"Not yet configured" / "to be added" / "TODO" markers.** Forward work
  goes in [doc/todo/registry.yaml](../todo/registry.yaml).
- **Sequencing or work plans.** "Step 1: do X. Step 2: do Y." Work plans
  belong in the ToDo registry or in PR descriptions.
- **Quoted snippets of code, config, or JSON.** Snippets drift from the
  source they were copied from. Reference *concepts* and link to the file by
  path, not by content. If a code shape genuinely needs to be locked, lock
  it in a contract file (e.g. `harness/STEERING.md`) and reference the
  contract.
- **Concrete implementation file paths beyond stable, contractual ones.**
  Files move. Reference contracts (`harness/ORACLE.md`), package paths
  (`harness/`), or component roots (`apps/classification/`). Avoid line
  numbers. Avoid pointers into PR-volatile script bodies.
- **Progress markers** ("DONE", "in progress"). Use the registry status field.

## What ADRs MUST contain

- **Status** — Proposed | Accepted | Deprecated | Superseded by ADR-NNN.
- **Date** the decision was made.
- **Deciders** — operator(s) who locked it.
- **Context** — the *forces* at play (constraints, trade-offs already in
  evidence, demonstrated failure modes). Not what's happening this week.
- **Decision** — what was decided, in declarative voice. The lock.
- **Consequences** — what this enables, what it gives up. Both sides.
- **Trade-offs** (optional but recommended) — explicit named sacrifices and
  why each is acceptable.
- **References** — other ADRs by number, source documents, external prior art.

## Where mutable content lives

| Mutable thing | Lives in |
|---|---|
| Current state, "today the harness has X wired" | `HARNESS.md` (per component, regenerable inventory) |
| Forward work, "we should also do Y" | [doc/todo/registry.yaml](../todo/registry.yaml) |
| Implementation specifics that may change | Component README, contract docs (e.g. `harness/STEERING.md`) |
| Decision rationale that depends on volatile facts | Use a research note under `doc/research/` and link to it from the ADR |
| Open questions during decision-making | `doc/research/<adr-id>-open-questions.md` (resolved before the ADR is Accepted) |

## ADR lifecycle

1. **Proposed.** New ADR, status: Proposed. Open question; review wanted.
   Mutable while in this state.
2. **Accepted.** Operator commits. Status: Accepted. **Body becomes
   immutable** from this point forward. Date stamped.
3. **Deprecated.** Decision is no longer in force but no replacement exists
   yet. Single-line annotation under Status: "Deprecated YYYY-MM-DD —
   <one-line reason>." Body still immutable.
4. **Superseded.** New ADR replaces this one. Single-line annotation under
   Status: "Superseded by ADR-NNN on YYYY-MM-DD." Body still immutable.

A bug or missed nuance discovered after Accepted is *not* a license to edit.
Either the decision still stands and the limitation is captured in
`LIMITATIONS.md` per component, or it doesn't and a new superseding ADR is
written.

## Anti-patterns

- **Editing in place because "it's just a small clarification."** No. If the
  clarification matters, it changes meaning; write a superseding ADR. If it
  doesn't matter, leave it.
- **Adding "Update YYYY-MM-DD: …" sections to old ADRs.** Same problem.
  Write a new ADR.
- **Folding multiple decisions into one ADR.** Each decision should be
  separately superseable. If you can't supersede one without disturbing
  another, you have two ADRs masquerading as one.
- **ADRs as work-tracking documents.** The "Sequencing" section is a
  recurring offender. If the decision implies work, that work goes in the
  registry; the ADR locks the decision, not the schedule.

## Skill

The [`/adr-author`](../../.claude/skills/adr-author/SKILL.md) skill
operationalizes this convention. Invoke it when drafting an ADR or
reviewing changes to an existing one. It will refuse to add disallowed
content and will route forward work to the registry.