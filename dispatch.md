# Autopilot Dispatch — Three-Gate Flow

Every dispatch passes three non-negotiable gates:

1. **Credentials** — pre-launch check, hard block on missing required creds
2. **Outcome checklist** — done-criteria the remote can self-verify against
3. **Behavior / process** — free-form path to outcome (exploration → exploitation)

Gates 2+3 together form **the brief**. Nothing launches unless all three pass.

## Directory Layout

Every dispatch writes to `briefs/YYYY-MM-DD-<slug>/` containing:

- `outcome.md` — checklist
- `behavior.md` — free-form process
- `context.md` — user-curated pointers to local state (plan files, commits, notes)
- `payload.json` — resolved file list mounted into the remote session
- `credentials.json` — pass/fail record of the credentials check
- `dispatch.log` — launch record (timestamp, session ID, exit)

`briefs/` is gitignored. It's the permanent local record of dispatches.

## Step-by-Step

### Step 1 — Select remote skill

List `remote-skills/*.md` and prompt the user to pick one. The selected file provides the `credentials:`, `interview:`, and `payload:` manifest used for this dispatch.

### Step 2 — Interview

Read the selected skill's `interview:` list and ask each `prompt` one at a time. Collect free-form answers.

### Step 3 — Draft brief

Synthesize the interview answers into two files under the new brief directory:

- `outcome.md` — turn answers into a concrete checklist of done-criteria
- `behavior.md` — free-form process/heuristics the remote should follow

Show both files to the user for edit/approval. Do NOT advance until the user approves.

### Step 4 — Context pointers

Prompt: "Paste any local artifact paths the remote should read (plan files, specs, recent notes). One per line." Write the answer to `context.md`.

### Step 5 — Payload manifest

Resolve the skill's declared `payload:` entries + every line in `context.md` into a concrete file list. Write to `payload.json`:

```json
{
  "skill_declared": ["scripts/generate.sh", "scripts/verify-dialogue.py"],
  "extra": ["docs/superpowers/specs/2026-04-19-foo.md"]
}
```

Show the combined list to the user. Confirm or edit.

### Step 6 — User approval

Display `outcome.md`, `behavior.md`, `context.md`, and the payload list together. Wait for explicit approval. If the user edits any file, re-display and re-confirm.

### Step 7 — Credentials gate (hard block)

Run:

```bash
python3 scripts/dispatch-gate.py all remote-skills/<skill>.md briefs/<dispatch>/
```

If exit code is non-zero: print the failure rows, refuse to launch, and tell the user exactly what's missing. Do NOT proceed.

On success, write the check results to `credentials.json` in the brief directory.

### Step 8 — Launch

Use the same curl flows previously in `intake.md` (Phase 3: Create Agent, Phase 4: Create Session & Dispatch) with these adjustments:

- The agent's skills array includes the uploaded remote skill + brainstorming
- The session `resources` array includes every file in `payload.json` (skill-declared + user extras), each mounted at a sensible path under `/workspace/`
- The brief sent as the first `user.message` is the concatenation of `outcome.md` + `behavior.md` + `context.md` with clear section headers

Append the launch record to `briefs/<dispatch>/dispatch.log`:

```
{timestamp} session_id={SESSION_ID} agent_id={AGENT_ID} exit=launched
```

### Step 9 — Post-launch

Print the session ID and URL. Append the session to `.superpowers/autopilot-sessions.json`. The brief directory remains as the permanent dispatch record.

## Skipping a Gate

The skill refuses shortcuts. If a user says "just dispatch it," explain which gate they're trying to skip and require them to supply the missing piece. The only exception: `check: remote-secret` entries report as manual-verify rather than hard-block (autopilot can't check the remote env from outside).

## Legacy API Call Reference

All managed-agents API curls from the previous `intake.md` are preserved structurally — only the orchestration above them changes. Key references for the launch step:

- Upload custom skill: `POST /v1/skills` with `anthropic-beta: skills-2025-10-02`
- Upload file: `POST /v1/files` with `anthropic-beta: files-api-2025-04-14`
- Create agent: `POST /v1/agents` with `anthropic-beta: managed-agents-2026-04-01`
- Create session: `POST /v1/sessions`
- Send event: `POST /v1/sessions/{id}/events`

Required header on all: `x-api-key: $ANTHROPIC_API_KEY`, `anthropic-version: 2023-06-01`.
