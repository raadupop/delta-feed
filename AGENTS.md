# INVEX

Volatility-exploitation trading system. Research vehicle measuring how AI agents handle six architecture patterns.

**Thesis:** "We don't know how to architect systems that are built, maintained, and evolved by AI agents."

## Repository Structure

- `doc/` — SRS v2.3.2 (Markdown-native, see `doc/srs/`), INVEX-API-v1.yaml, project context
- `apps/classification/` — Python classification service (constant across all iterations)
- .NET iteration projects will be added starting at Iteration 1

## Document Hierarchy

| Document | Role |
|---|---|
| [SRS v2.3.2](doc/srs/INVEX-SRS-v2.3.2.md) | Requirements — what the system must do |
| INVEX-API-v1.yaml | External interface contract — message content, format, schemas |
| AGENTS.md (per component) | Agent context. `CLAUDE.md` exists at each level as a pointer stub so Claude Code's auto-discovery still resolves. |

Three separate artifacts. SRS references the OpenAPI spec, not the other way around.

## Architecture Iterations

1. Transaction Script (baseline) — all Must requirements
2. Vertical Slice Architecture (refactor from 1)
3. Clean Architecture with Rich Domain Model (rewrite)
4. Clean Architecture + Event Sourcing (refactor from 3)
5. Modular Monolith (sourced from Iteration 3)
6. Service Extraction (Decision Engine)

## Python Classification Service

Constant external dependency across all six .NET iterations. Lives in `apps/classification/`. Has its own `AGENTS.md`. The .NET app calls `POST /classify` over HTTP. The Python service does not affect architecture measurements — it's constant infrastructure.

## Conventions

- Contract-first: INVEX-API-v1.yaml is the single source of truth for the .NET API
- API acceptance tests are strictly black-box (EVO-001)
- Structural tests are iteration-specific
- The agent context (this file + per-component `AGENTS.md`) is a controlled variable (ACX-001, ACX-002)
