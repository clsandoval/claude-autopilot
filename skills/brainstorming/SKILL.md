---
name: brainstorming
description: "Structured brainstorming for managed agents — one question at a time via ask_user, explores approaches before implementation."
---

# Brainstorming Ideas Into Designs (Managed Agent)

Turn ideas into fully formed designs through structured collaborative dialogue using `ask_user`.

<HARD-GATE>
Do NOT write specs, plans, or code until you have explored the codebase, asked clarifying questions ONE AT A TIME, proposed approaches, presented a design, and gotten user approval via `ask_user`. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: Batching Questions

**NEVER ask multiple questions in a single `ask_user` call.** Each call pauses the session and costs the user a round-trip. This makes it tempting to batch — resist this completely.

Bad (batched):
```
ask_user(question: "Three questions: 1) Where should this run? 2) What order? 3) Storage?")
```

Good (one at a time):
```
ask_user(question: "Where should the pipeline run?", options: ["A) Local", "B) Cloud", "C) Notebook"])
// wait for answer, then:
ask_user(question: "Given cloud hosting, what stage order?", options: ["A) Spec order", "B) Detect-first"])
// wait for answer, then:
ask_user(question: "Given cloud + detect-first, how to handle failures?", options: ["A) Stateless", "B) Checkpoints"])
```

Each question builds on the previous answer. Later questions may become irrelevant based on earlier answers. This is why batching is wrong — you cannot know which questions matter until you have the prior answers.

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short, but you MUST present it and get approval.

## Checklist

Complete these steps in order:

1. **Explore project context** — check files, docs, recent commits at /workspace/repo
2. **Assess scope** — if the request spans multiple independent subsystems, call `ask_user` to ask how to decompose before proceeding
3. **Ask clarifying questions** — one `ask_user` call per question, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** — present via `ask_user` with trade-offs and your recommendation
5. **Present design** — in your message text, scaled to complexity. Call `ask_user` to confirm each major section.
6. **Write design doc** — save to `docs/autopilot/<slug>-spec.md` and commit
7. **Spec self-review** — check for placeholders, contradictions, ambiguity, scope issues. Fix inline.
8. **User reviews spec** — call `ask_user` summarizing key decisions, ask for approval before planning

## Process Flow

```
Explore codebase
    |
    v
Assess scope --- too large? ---> ask_user: how to decompose
    |                                    |
    | (appropriately scoped)             v
    v                            Decompose, brainstorm first sub-project
Clarifying question 1 (ask_user, one question)
    |
    v
Clarifying question 2 (ask_user, builds on Q1 answer)
    |
    v
... (as many as needed, one at a time)
    |
    v
Propose 2-3 approaches (ask_user, multiple choice)
    |
    v
Present design sections (in messages)
    |
    v
ask_user: "Does this design look right? Any changes?"
    |
    +--- no ---> Revise and re-present
    |
    v (yes)
Write spec doc + commit
    |
    v
Spec self-review (fix inline)
    |
    v
ask_user: "Spec committed. Review and approve before I start planning."
    |
    v
Proceed to Phase 2 (Spec is done) / Phase 3 (Planning)
```

## ask_user Discipline

### One question per call — NO EXCEPTIONS

Each `ask_user` call should contain exactly one question. If you have 3 things to ask, that's 3 separate `ask_user` calls with 3 separate user responses.

**Why:** The user answers asynchronously. Compound questions get partial answers, force re-asking, and waste everyone's time. Also, later questions often depend on earlier answers — you literally cannot ask Q3 correctly until you know the answer to Q1.

### Multiple choice preferred

When possible, present options the user can pick from rather than open-ended questions:

```json
{
  "question": "Which approach should we take for the data pipeline?",
  "context": "Found existing ETL patterns in /src/pipelines/ using Python + pandas. The repo also has a Go service for real-time ingestion.",
  "options": [
    "A) Python batch pipeline — matches existing ETL patterns, simplest",
    "B) Go streaming pipeline — matches real-time service, better for scale",
    "C) Hybrid — Python for batch, Go for real-time, more complex"
  ]
}
```

### Question sequencing

Questions should flow naturally, each building on the previous answer:

1. **Purpose/goal** — "What is this for?" (if not clear from brief)
2. **Constraints** — "Any hard requirements?" (tech stack, timeline, etc.)
3. **Architecture choices** — "Given X, which approach?" (informed by codebase exploration)
4. **Design details** — "For the chosen approach, how should X work?" (only after approach is locked)

Don't ask design detail questions before the approach is chosen — they may be irrelevant.

### When NOT to use ask_user

- The brief already answers the question explicitly
- The codebase answers the question (read more files instead of asking)
- The decision is low-impact and easily reversible
- You're asking for permission to do something obvious

## The Process

**Understanding the idea:**

- Check out the current project state first (files, docs, recent commits)
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems, flag this immediately via `ask_user`. Don't spend questions refining details of a project that needs to be decomposed first.
- For appropriately-scoped projects, ask questions one at a time via `ask_user`
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs via `ask_user`
- Lead with your recommended option and explain why
- Include codebase evidence: "Found X pattern in Y file, so approach A fits naturally"

**Presenting the design:**

- Once you understand what you're building, present the design in your message text
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Call `ask_user` after presenting to confirm: "Does this design look right? Any changes before I write the spec?"
- Cover: architecture, components, data flow, error handling, testing

**Design for isolation and clarity:**

- Break the system into smaller units with one clear purpose each
- Well-defined interfaces between units
- Can someone understand what a unit does without reading its internals?
- Smaller units are easier to implement correctly

**Working in existing codebases:**

- Explore the current structure before proposing changes. Follow existing patterns.
- Where existing code has problems that affect the work, include targeted improvements as part of the design.
- Don't propose unrelated refactoring. Stay focused on what serves the current goal.

## After the Design

**Write the spec:**
- Save to `docs/autopilot/<slug>-spec.md`
- Commit with message: `autopilot: spec for <slug>`

**Spec Self-Review:**
After writing the spec, check with fresh eyes:

1. **Placeholder scan:** Any "TBD", "TODO", incomplete sections? Fix them.
2. **Internal consistency:** Do sections contradict each other?
3. **Scope check:** Focused enough for a single implementation plan?
4. **Ambiguity check:** Could any requirement be interpreted two ways? Pick one and make it explicit.

Fix any issues inline.

**User Review Gate:**
After self-review, call `ask_user`:

```json
{
  "question": "Spec written and committed. Key decisions: [summary]. Ready to proceed to planning?",
  "context": "The spec covers [brief summary]. Review the spec at docs/autopilot/<slug>-spec.md",
  "options": ["A) Approved — proceed to planning", "B) Changes needed (I'll describe what to change)"]
}
```

Wait for approval before proceeding to planning/implementation phases.

## Key Principles

- **One question at a time** — Don't batch. Ever.
- **Multiple choice preferred** — Easier for async answers
- **YAGNI ruthlessly** — Remove features not explicitly requested
- **Explore alternatives** — Always propose 2-3 approaches before settling
- **Incremental validation** — Present design, get approval before writing spec
- **Codebase evidence** — Back recommendations with what you found in the code
