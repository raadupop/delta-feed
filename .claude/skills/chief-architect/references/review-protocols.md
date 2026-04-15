# Review Protocols

## Architecture Review

Use when reviewing a system design, proposed architecture, or migration plan.

### Review Dimensions

Work through each dimension. Skip those that genuinely don't apply, but default to
including rather than excluding — missing a dimension is worse than over-analyzing.

#### 1. Problem-Solution Fit
- Does the architecture actually solve the stated problem?
- Is the problem correctly understood? (Often the real problem is different from the stated one.)
- Is the solution proportional to the problem, or is it over-/under-engineered?

#### 2. Boundary Design
- Are service/module boundaries aligned with domain boundaries?
- Do boundaries minimize cross-cutting changes? (A feature change that touches 5 services is a boundary smell.)
- Are ownership boundaries clear — who operates what?

#### 3. Data Architecture
- Where is the source of truth for each key entity?
- How does data flow between boundaries? (Sync, async, replication, shared DB?)
- What are the consistency guarantees? Are they appropriate for the domain?
- How does the system handle data that changes shape over time (schema evolution)?

#### 4. Failure Modes
- What happens when [dependency X] is down?
- What happens when [component Y] is slow (not down — slow is harder)?
- Where are the single points of failure?
- Is there a degradation strategy or is it all-or-nothing?
- What's the blast radius of a bad deployment?

#### 5. Scalability
- What's the current load? What's the expected load in 12-24 months?
- Where will the system hit a ceiling first? (Usually: database, network, specific hot path.)
- Is the scaling strategy horizontal, vertical, or "rewrite it"?
- Are there hidden scalability killers? (Fan-out, N+1 queries, unbounded queues.)

#### 6. Security Boundaries
- Where does trust change? (Public → private, user → admin, service → service.)
- How is authentication/authorization handled at each boundary?
- Where is sensitive data, and how does it flow?
- What's the attack surface?

#### 7. Operational Readiness
- Can the team that owns this actually operate it? (Skills, tooling, on-call load.)
- Is it observable? (Logs, metrics, traces — not just "we'll add monitoring later.")
- How is it deployed? How long to rollback?
- What does the runbook look like at 3 AM?

#### 8. Evolutionary Fitness
- What happens when requirements change? (They will.)
- Where are the hardest parts to change? Are those the parts most likely to change?
- Does this design create options or close them off?

#### 9. Economic Analysis
- What's the total cost of ownership (build + run + maintain + eventually migrate away)?
- Are there cheaper alternatives that are "good enough"?
- Where is money being spent to avoid complexity, and is that trade-off worth it?

#### 10. Organizational Alignment
- Does the architecture match the team structure (Conway's Law)?
- If not, which should change — the architecture or the teams?
- Are there implicit dependencies between teams that the architecture makes worse?

### Review Output Format

```
## Architecture Review: [System/Decision Name]

### Summary
[2-3 sentences: what this is, what the key finding is]

### Critical Issues (must address before proceeding)
- [Issue]: [Why it's critical] → [Suggested resolution]

### Significant Concerns (should address, can proceed with plan)
- [Concern]: [Why it matters] → [Suggested approach]

### Observations (worth noting, not blocking)
- [Observation]

### What's Good
- [Genuinely good decisions worth calling out — don't skip this]

### Recommended Next Steps
1. [Concrete action]
2. [Concrete action]
```

---

## Code/Design Review (Architectural Lens)

Use when reviewing code, PRs, or detailed designs where the question is not
"does this work?" but "does this fit the system?"

This is not a line-by-line code review. It's a review of whether the code's
structure, boundaries, and patterns serve the system's long-term health.

### What to Look For

#### Structural Alignment
- Does this code respect the established architectural boundaries?
- Does it introduce new dependencies that cross boundaries?
- Does it follow or violate the dependency direction rules?

#### Abstraction Quality
- Are new abstractions earning their keep, or are they premature?
- Are existing abstractions being honored or worked around?
- Is there a leaky abstraction that will cause problems at scale?

#### Complexity Trajectory
- Does this change make the system simpler or more complex?
- Is the added complexity essential (domain-driven) or accidental (tooling/pattern-driven)?
- Will the next developer who touches this understand it without tribal knowledge?

#### Pattern Consistency
- Does this follow established patterns, or introduce a new one?
- If new: is the new pattern justified, or is it "I prefer this style"?
- If inconsistent: is the inconsistency deliberate (migration) or accidental?

#### Hidden Coupling
- Does this change create implicit coupling through shared state, timing assumptions, or naming conventions?
- Would changing the internals of one component force changes in another?

### Review Output Format

```
## Architectural Review: [PR/Design Name]

### Verdict: [Approve / Approve with changes / Request changes / Needs design discussion]

### Architectural Impact
[One paragraph: how this change affects the system beyond its immediate scope]

### Issues
- [Issue]: [Why it matters architecturally] → [What to do]

### Suggestions (non-blocking)
- [Suggestion]: [Why it would improve things]
```

---

## Technical Article Review

Use when reviewing articles, blog posts, or technical writing about software architecture.

### Review Dimensions

#### 1. Technical Accuracy
- Are the claims factually correct?
- Are patterns/concepts described accurately, or are there subtle mischaracterizations?
- Are there unsupported claims presented as established facts?
- Flag anything a senior practitioner would challenge.

#### 2. Argument Structure
- Does the reasoning flow logically from premises to conclusions?
- Are there logical gaps or unstated assumptions?
- Does the article conflate correlation with causation?
- Are examples well-chosen and genuinely illustrative?

#### 3. Practitioner Credibility
- Would a senior architect find this convincing, or does it read as theoretical/generic?
- Does it demonstrate real-world experience, or just textbook knowledge?
- Is the tone appropriate — authoritative without being dogmatic?

#### 4. Missing Perspectives
- What counterarguments or edge cases are not addressed?
- Is the scope appropriately bounded, or does it overclaim?
- Are trade-offs of the recommended approach acknowledged?

#### 5. Originality and Value
- Does this contribute something new, or restate known ideas?
- If restating: is the synthesis or framing novel enough to justify the piece?
- Who is the target audience, and does the article serve them?

### Review Output Format

Provide specific, actionable feedback. Not "this section could be stronger" but
"this section claims X without evidence — either cite a source, add a concrete
example, or qualify it as opinion."

Organize by severity:
1. **Factual errors** — things that are wrong and must be fixed
2. **Structural issues** — argument flow, missing sections, scope problems
3. **Polish items** — wording, examples, tone adjustments
