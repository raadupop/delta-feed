# ADR Template

## Format

```markdown
# ADR-NNN: [Decision Title]

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNN
**Date:** YYYY-MM-DD
**Deciders:** [Who made or will make this decision]
**Domain:** [Which part of the system this affects]

## Context

Describe the situation and the forces at play. This is not just "the problem" —
it includes business context, technical constraints, team capabilities, timelines,
and any prior decisions that constrain this one.

A reader who wasn't in the room should understand why this decision matters
and why it's non-obvious.

## Decision Drivers

Rank-ordered list of what matters most for this specific decision:

1. [Most important driver — e.g., "Time to market: must ship by Q3"]
2. [Second driver — e.g., "Data consistency: financial transactions cannot be lost"]
3. [Third driver — e.g., "Team capability: team has no Kafka experience"]

## Options Considered

### Option A: [Name]

**Description:** What this option entails.

**Pros:**
- [Concrete benefit with specifics]

**Cons:**
- [Concrete cost or risk with specifics]

**CoBW:** [What happens if this turns out to be the wrong choice]

### Option B: [Name]

[Same structure]

### Option C: Do Nothing / Status Quo

Always include this. It forces you to articulate why change is necessary.

## Decision

[State the decision clearly in one sentence.]

[Then explain why — connect it back to the decision drivers.]

## Trade-offs Accepted

Name what you're giving up. Every decision sacrifices something.

- [What's sacrificed]: [Why that's acceptable in this context]

## Consequences

### Positive
- [Concrete positive outcome]

### Negative
- [Concrete negative outcome or new constraint introduced]

### Risks
- [Risk]: [Likelihood] / [Impact] / [Mitigation]

## Cost of Being Wrong

**Reversibility:** [Easy / Moderate / Hard / Irreversible]
**Blast radius:** [Single service / Team / Platform / Organization]
**Detection time:** [How quickly would we know this was wrong?]
**Recovery path:** [What would we do if this fails?]

## Review Triggers

This decision should be revisited if:
- [Condition that would invalidate the assumptions]
- [Metric threshold that signals the decision isn't working]
```

## Guidance

### What makes a good ADR

1. **Context is king.** The decision section is often the shortest part. Most of the
   value is in the context — capturing why the decision was necessary and what forces
   shaped it. Six months from now, the "what" is obvious from the code. The "why" is
   lost forever if you don't write it down.

2. **Options must be real.** Don't include strawman options to make the chosen one look
   better. Each option should be something a reasonable engineer could advocate for.
   If you can't make a genuine case for it, drop it.

3. **"Do Nothing" is always an option.** If the status quo is genuinely untenable,
   stating why makes the case for change. If it's actually fine, maybe you don't need
   this ADR.

4. **Trade-offs are not cons.** Cons are downsides of an option. Trade-offs are what
   you consciously sacrifice by choosing one option over another. They're the cost
   of the decision, acknowledged and accepted.

5. **Review triggers prevent zombie decisions.** Without them, decisions outlive their
   context and become "that's just how we do it" folklore. Explicit triggers make
   revisiting rational, not political.

### When to write an ADR

- The decision is hard to reverse (infrastructure, data model, protocol, vendor)
- Multiple teams are affected
- There was significant disagreement
- The decision is non-obvious (a new team member would ask "why?")
- The cost of being wrong is high

### When NOT to write an ADR

- The decision is easily reversible and low-impact
- It's a well-established pattern with no controversy
- You're writing it to satisfy a process, not to capture reasoning
