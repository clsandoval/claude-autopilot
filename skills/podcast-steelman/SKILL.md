---
name: podcast-steelman
description: Produce a flight-podcast episode that steelmans a repo on engineering merits, then critiques it on file-pinned tensions. Local orchestration — research + dialogue happen under Claude Code supervision; render + Telegram delivery reuse the existing Pimsleur dispatch path. Invoked as `/autopilot podcast steelman OWNER/REPO`.
---

# Podcast — Steelman format

An adversarial-angle flight-podcast episode done the honest way: read enough of the repo to genuinely advocate for it first, then identify engineering tensions pinned to specific files and mechanisms. Fits into the existing `flight-podcast-2026-04-ext` series (ep 44+) at the currently scheduled `japanese_ratio`.

This skill does **not** replace `/podcast` or `/autopilot podcast pimsleur`. It is a specific rhetorical mode for repo critique episodes — when the interesting thing about the repo is not "look how it's built" but "look at the seam between what it claims and what it does."

## When this skill applies

Use when the user says `/autopilot podcast steelman <OWNER/REPO>` or asks to "critique," "tear down with respect," or "do an adversarial episode on" a specific GitHub repo. Do **not** use for:

- Neutral repo deep-dives (use standard `/autopilot podcast pimsleur`).
- Repos the user has already drafted dialogue for.
- Non-repo artifacts (specs, plans) — those go through `/podcast`.

## The format (non-negotiable)

### Forbidden moves

These are why earlier attempts at this format produced cheap takes. Do not:

- Use star counts, follower counts, or marketing-channel evidence as a claim about engineering quality. Stars inflate organically from Twitter and launches; that is not an architectural argument.
- Dismiss by analogy ("smells like X," "classic Y pattern," "this is the Z anti-pattern") without reading the actual code that would make the analogy true or false.
- Generalize about a category ("all self-optimizing agents are for-loops over prompts," "all finance agents lack risk controls") without checking whether THIS repo fits the generalization.
- Use debasing framing: "slop," "farm," "fake," "junk." Even if the critique is correct, those words collapse the listener's ability to evaluate it.
- Invent file paths, function names, or mechanisms. If the research subagent didn't surface it, it doesn't go in the dialogue.

### Required moves

- **Steelman in full before any critique.** The steelman artifact must stand on its own as an honest advocacy piece — a version of the episode that a contributor to the repo would read and recognize as fair.
- **Tensions pinned to a file + mechanism.** Every critique beat cites a specific file (with path) and a specific mechanism (function, prompt, data flow). "Guardrails are in the prompt" is vague; "the guardrail lives in `agent/prompts/system.ts:L142` as a regex match on user input before the LLM call, which fails under paraphrase" is pinned.
- **Acknowledge what the repo achieves.** Real users, real plugins, real shipping — name those before identifying where the architecture strains.
- **One crisp principle per episode.** The "lesson" beat in synthesis names an engineering principle the repo's own authors would likely agree with in a post-mortem. If no such principle exists, the episode isn't ready.
- **Drop-path:** if research cannot surface a real tension, the repo becomes a straight Pimsleur deep-dive (fall back to `/autopilot podcast pimsleur`) or gets dropped from the queue. Do not manufacture tensions.

## Workflow

### Step 0 — Parse invocation

Argument shape: `OWNER/REPO` (required). Optional second argument: `EP=NN` to pin the episode number; otherwise read `data/japanese/profile.yaml.episodes_completed + 1`.

Confirm with the user: repo + episode number + scheduled `japanese_ratio` (read from `data/japanese/schedule.yaml` for that ep slot if it exists). If the ep slot doesn't exist in schedule.yaml, ask the user to either append one or re-run with an existing slot.

### Step 1 — Steelman research

Spawn a `general-purpose` subagent with a prompt that includes, verbatim:

> Research `OWNER/REPO` thoroughly enough to advocate for it on engineering merits. You are writing a steelman, not a critique. Any critique belongs in a later pass.
>
> Required sources (use `gh api` via Bash):
> - `gh api repos/OWNER/REPO/readme --jq .content | base64 -d`
> - `gh api repos/OWNER/REPO/git/trees/main --jq '.tree[] | select(.type=="tree") | .path'`
> - Read 3–5 key source files. Pick by informed guess based on the tree. Prefer files that encode the architectural thesis (runtime loop, agent core, prompt layer, plugin loader, memory store).
> - Docker / compose / CI if present.
>
> Walk the six axes as an advocate: compute topology, LLM locus, tool mechanics, extension loading, context & memory strategy, scaling topology. For each axis, state what the repo does well and why that choice is reasonable given its constraints. Cite real file paths.
>
> Write the output to `research/<slug>_steelman.md` with frontmatter: `repo`, `slug`, `sources` (list of real file paths consulted), and sections: `What this repo actually achieves`, `Six-axis walk (advocating)`, `The contribution` (one paragraph on what the repo adds to the field that wasn't there before).
>
> Do NOT identify tensions, flaws, or critiques in this pass. The steelman must stand on its own.

Slug: lowercased `OWNER-REPO` with `/` replaced by `-`.

After the subagent returns, open `research/<slug>_steelman.md`. Read it end-to-end. Spot-check at least one cited file path via `gh api` to confirm the subagent isn't inventing.

### Step 2 — User gate

Show the user a one-paragraph summary of the steelman plus the three most-cited file paths. Ask:

> Does this repo have a real engineering tension worth an episode on, or should it become a straight deep-dive / drop from the batch?

Wait for an explicit answer. Acceptable replies: `proceed` / `tension: <one-line description>` / `straight deep-dive` / `drop`.

If `drop`: remove the ep slot from schedule.yaml if one was created for this run, commit, done.
If `straight deep-dive`: hand off to `/autopilot podcast pimsleur` with the existing ep slot. Do not proceed through this skill.
If `proceed` or `tension: ...`: continue to Step 3. If the user named a specific tension, pass it to the tells subagent as a hypothesis to verify (not to assume).

### Step 3 — Tells research

Spawn a second `general-purpose` subagent:

> You have access to `research/<slug>_steelman.md` describing what `OWNER/REPO` achieves. Your job is to identify engineering tensions — places where the architecture strains or the claims don't fully land. Every tension must be pinned to a specific file (with path) and a specific mechanism.
>
> Hypothesis to verify (if provided): `<user's one-line tension description or "none — open search">`. If provided, investigate it first. If the code does not support the hypothesis, say so clearly and report what the code actually shows.
>
> Research method: read the files cited in the steelman more carefully, plus 2–5 additional files the steelman didn't cover. Look at: prompt files (system prompts, guardrails), executor boundaries (where LLM output becomes action), error handling paths, test coverage on the riskiest mechanisms, config surface (what users can change vs. what's hardcoded).
>
> For each tension, write:
> - **What the repo does** (one sentence, neutral)
> - **The file + mechanism** (path + function/section + quoted snippet if short)
> - **Why this is a tension** (one paragraph — the engineering argument, not a vibe)
> - **What the authors probably intended** (steelman the choice)
> - **The calibrated critique** (one or two sentences — where this breaks, under what conditions, how a listener could verify)
>
> Forbidden: star counts, analogy without code, generalization without repo-specific evidence, debasing framing.
>
> If after honest research you find no tension that survives file-level scrutiny, write `NO_TENSION_FOUND` as the first line of the file and a paragraph explaining what you looked for and why it didn't land. Do NOT manufacture a tension to fill the file.
>
> Output: `research/<slug>_tells.md`.

After return, read the file. If `NO_TENSION_FOUND`, fall back to the drop / straight-deep-dive paths from Step 2 and inform the user.

### Step 4 — Dialogue drafting

Spawn a third subagent (dialogue writer). It receives both artifacts and writes `briefs/2026-04-22-flight-podcast/ep_NN.md`.

Prompt includes the standard TEMPLATE-DEEP-TECHNICAL preamble from `automations/flight-podcast/TEMPLATE-DEEP-TECHNICAL.md` plus the steelman-format overlay below.

**5-segment structure (modified):**

1. **Cold open (2 min)** — Red's README misread. Ark's correction. Unchanged.
2. **New core — architecture + the tells (16 min)** — Walk the 6 axes. For each axis, state what works (from steelman) before naming any tension (from tells). When a tension belongs on the axis, Ark cites the specific file path and mechanism. When the axis has no tension, Ark says "this axis is sound" and moves on. Roughly 2–3 minutes per axis.
3. **Review interleave + new grammar (6 min)** — Same as standard template. Prior ep vocab + new grammar pattern from schedule.yaml.
4. **Synthesis — the pattern (4 min)** — Red restates the architecture in plain terms. Ark adds ONE crisp engineering principle the repo's authors would likely agree with in a post-mortem. This is the "lesson" beat. Not a zinger. A principle.
5. **Tease next ep (2 min)** — Drop one JP callforward word. Unchanged.

**Rhetorical guardrails for the dialogue subagent:**

- Every critique in Segment 2 is preceded by acknowledgment in the same turn or the one before ("they got X right; the place where it strains is Y").
- Ark cites file paths as they appear in `research/<slug>_tells.md`. No new paths invented in dialogue.
- Red's "dumb-smart" questions come from the steelman, not the critique. Red is not the dismissive host — Red is the one who read the marketing and believed it. Ark's job is to show Red the seam, not to mock Red.
- No debasing vocabulary ("slop," "farm," "fake"). Flagged by the dialogue verifier if present.
- Japanese layer remains Pimsleur-standard: ratio from schedule.yaml, 1,800 CJK floor, vocab + grammar from the ep slot, gloss pairing rule enforced.

### Step 5 — Verify

Run the standard density + pairing verifier on `briefs/2026-04-22-flight-podcast/ep_NN.md`:

```bash
python3 /home/clsandoval/.claude/skills/autopilot/scripts/verify-dialogue.py <path>
```

Additionally grep for debasing vocabulary:

```bash
grep -niE '\b(slop|farm|fake|junk|garbage|trash|debasing)\b' briefs/2026-04-22-flight-podcast/ep_NN.md
```

Any hit = flag to user, do not auto-rewrite. User decides whether the usage is warranted.

### Step 6 — User review

Show the user: density report, pairing report, grep results, and the `--- [synthesis] ---` segment verbatim (since the "principle" beat is the rhetorical load-bearing one). Ask for approval to dispatch.

### Step 7 — Dispatch render

Hand off to the existing script:

```bash
EP=NN bash automations/flight-podcast/dispatch-ep.sh
```

The script handles upload + session creation + brief. Session ID appends to `.superpowers/autopilot-sessions.json`. Steelman format requires no changes to the render path — it's pre-written dialogue mode.

### Step 8 — Commit artifacts

Commit both research artifacts (`research/<slug>_steelman.md`, `research/<slug>_tells.md`) alongside the dialogue. These are the evidence trail; future episodes can cite them as prior-art when a repo comes up again.

Commit message: `podcast: ep NN steelman+tells+dialogue for OWNER/REPO`.

## Artifacts produced per run

- `research/<slug>_steelman.md` — advocacy artifact
- `research/<slug>_tells.md` — file-pinned tensions (or `NO_TENSION_FOUND`)
- `briefs/2026-04-22-flight-podcast/ep_NN.md` — dialogue
- Session ID in `.superpowers/autopilot-sessions.json`
- MP3 delivered to Telegram by remote agent

## Failure modes to watch for

- **Subagent invented file paths.** Spot-check at least one path via `gh api` per research pass. If inventions found, re-dispatch with stricter "cite only files you actually read" prompt.
- **Tension is vibes-level.** If the tells artifact reads more like an essay than a file-pinned critique, it's not usable. Re-dispatch or drop.
- **Steelman is thin.** If the steelman is shorter than the tells, the episode will feel hostile regardless of content. Re-dispatch steelman with "the steelman must be the longest artifact in this run."
- **Dialogue drifts to debasement.** The grep in Step 5 catches obvious cases. Read segment 2 and 4 manually — debasement can be present without forbidden words.
