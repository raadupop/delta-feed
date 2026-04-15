# Trade-off Analysis Frameworks

## Framework 1: Decision Matrix

Use when comparing 3+ options across multiple dimensions.

### Structure

| Dimension | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Reversibility | High/Med/Low | Score 1-5 | Score 1-5 | Score 1-5 |
| Build cost | ... | ... | ... | ... |
| Run cost (annual) | ... | ... | ... | ... |
| Time to deliver | ... | ... | ... | ... |
| Organizational fit | ... | ... | ... | ... |
| Risk (worst case) | ... | ... | ... | ... |
| Scalability ceiling | ... | ... | ... | ... |

Weights reflect the specific context. A startup optimizes differently than a regulated enterprise.
Do not average scores — the matrix is a conversation tool, not a calculator.

### How to use it
1. Fill in the matrix with the user or from context.
2. Identify where options diverge sharply — those are the real decision points.
3. Ask: "Which dimension, if you got it wrong, would hurt the most?" That's CoBW.
4. The option that scores well on the highest-CoBW dimensions wins, even if it loses on total points.

## Framework 2: CoBW (Cost of Being Wrong) Analysis

Use for binary or high-stakes decisions where the key question is "what happens if we're wrong?"

### Structure

```
Decision: [What are we deciding?]

Option A: [Name]
  If right: [What we gain]
  If wrong: [What we lose, how hard to recover, blast radius]
  CoBW: [Low / Medium / High / Catastrophic]
  Reversal cost: [Cheap / Moderate / Expensive / Irreversible]

Option B: [Name]
  If right: [What we gain]
  If wrong: [What we lose, how hard to recover, blast radius]
  CoBW: [Low / Medium / High / Catastrophic]
  Reversal cost: [Cheap / Moderate / Expensive / Irreversible]

Recommendation: [Which option and why]
Key assumption: [The one thing that, if wrong, changes the answer]
Hedge: [What you'd do to limit downside if you're wrong]
```

### Guidance
- CoBW is asymmetric. Option A might have higher upside but catastrophic downside.
  A chief architect usually picks the option with bounded downside unless the upside
  justifies the tail risk.
- Always identify the key assumption. If you can test it cheaply, do that before committing.
- A hedge is not a compromise — it's a concrete action that limits blast radius.

## Framework 3: Reversibility Quadrant

Use for quick triage of multiple decisions to decide where to invest analysis time.

```
                    High Impact
                        |
    Analyze deeply      |     Decide fast, monitor
    (irreversible +     |     (reversible +
     high impact)       |      high impact)
                        |
  ----------------------+----------------------
                        |
    Delegate or         |     Just do it
    standardize         |     (reversible +
    (irreversible +     |      low impact)
     low impact)        |
                        |
                    Low Impact
  
  Left = Hard to reverse    Right = Easy to reverse
```

### How to use it
1. Plot pending decisions on the quadrant.
2. Top-left quadrant gets chief architect attention and formal ADRs.
3. Top-right gets a lightweight decision with monitoring.
4. Bottom-left gets a standard/policy (decide once, apply everywhere).
5. Bottom-right gets delegated — don't waste senior time here.

## Framework 4: Forces Diagram

Use when the decision is blocked by conflicting stakeholder concerns or non-obvious constraints.

### Structure
```
Decision: [What are we deciding?]

Forces pushing toward Option A:
  - [Force 1]: [Why it pushes this way]
  - [Force 2]: [Why it pushes this way]

Forces pushing toward Option B:
  - [Force 1]: [Why it pushes this way]
  - [Force 2]: [Why it pushes this way]

Constraints (non-negotiable):
  - [Constraint]: [Why it's non-negotiable]

Resolution: [How the forces resolve given the constraints]
```

### Guidance
- Forces are not arguments — they're real pressures from the environment
  (business timelines, team skills, regulatory requirements, data gravity, existing contracts).
- Constraints eliminate options. List them first to narrow the space.
- If forces are balanced, look for an option that satisfies the highest-weight
  forces while staying within constraints. If none exists, escalate — the decision
  requires a business trade-off, not just a technical one.
