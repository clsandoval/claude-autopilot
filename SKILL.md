---
name: autopilot
description: |
  Dispatch autonomous work to Claude Managed Agents, or generate podcasts/investigations locally.
  Triggers: "autopilot", "dispatch", "autopilot status", "autopilot list", "autopilot podcast", "autopilot investigate"
  Local skills /podcast and /investigate are registered separately via skills/ directory.
---

# Autopilot — Managed Agent Command Center

Dispatch autonomous work to Claude Managed Agents, generate podcasts, and run investigations. One plugin, two execution modes:

- **Remote** (`/autopilot`) — work runs on Anthropic's infrastructure
- **Local** (`/podcast`, `/investigate`) — work runs in your Claude Code session

**Announce at start:** "I'm using the autopilot skill to [dispatch new work / generate a podcast / check status / list sessions]."

## Two Modes of Operation (for `/autopilot` dispatch)

### Mode 1: Brainstorm Locally, Then Dispatch
The user wants to think through the approach first. Run the full brainstorming flow locally (approach selection, architecture decisions, constraints), then dispatch a fully-formed brief. The agent executes without deliberation.

**Use when:** The user is actively engaged and wants to make decisions now.

### Mode 2: Dispatch Fast, Answer Questions Later
The user wants to fire and forget. Send a brief (can be vague), and the agent will brainstorm autonomously and ask questions via `ask_user`. The session pauses with `requires_action` until the user responds via `/autopilot status`.

**Use when:** The user says "just dispatch it" or provides a brief and wants to move on.

**Default:** Ask the user which mode they prefer. If they provide a detailed brief with decisions already made, lean toward Mode 1. If they provide a vague brief, lean toward Mode 2.

## Subcommands

| Invocation | Where | Action |
|---|---|---|
| `/autopilot` | Remote | New job — intake, configure, dispatch |
| `/autopilot podcast <brief>` | Remote | Dispatch managed agent to research + write dialogue + generate audio + deliver via Telegram |
| `/autopilot podcast pimsleur <brief>` | Remote | Dispatch bilingual Japanese immersion podcast with curriculum tracking |
| `/autopilot investigate <brief>` | Remote | Dispatch managed agent to execute a spec + collect results + podcast findings + deliver via Telegram |
| `/autopilot status` | Local (polls remote) | Check progress, answer pending questions |
| `/autopilot list` | Local (polls remote) | Show all tracked sessions |
| `/podcast <file>` | Local | Narrate a doc into podcast audio (registered via skills/podcast/) |
| `/investigate <file>` | Local | Execute a spec, collect results, podcast findings (registered via skills/investigate/) |

## Routing

**On `/autopilot` (no args or with a generic brief):**
1. Read `setup.md` — ensure one-time environment setup is complete (environment_id in config)
2. Read `intake.md` — run the intake flow:
   - Determine mode (local brainstorm vs fast dispatch)
   - If Mode 1: brainstorm locally, then configure and dispatch
   - If Mode 2: gather brief + repo/branch, configure and dispatch quickly
   - Configure agent: repo, branch, skills, include `ask_user` custom tool
   - Create agent per-job with selected skills
   - Create session and dispatch

**On `/autopilot podcast <brief>`:**
1. Read `setup.md` — ensure environment setup is complete
2. Read `intake.md` — run the **podcast dispatch** flow:
   - Upload `remote-skills/podcast.md` as a custom skill
   - Upload `scripts/generate.sh` as a file (mounted at `/workspace/generate.sh`)
   - Upload `.env` as a file (mounted at `/workspace/.env`) for ElevenLabs + Telegram keys
   - Create agent with: podcast skill + brainstorming skill + agent_toolset
   - Construct brief from user's input (the brief IS the source material for the podcast)
   - Create session and dispatch
   - The agent writes dialogue, generates audio via ElevenLabs, delivers to Telegram

**Pimsleur variant:** When the brief starts with "pimsleur" or the subcommand is `/autopilot podcast pimsleur <brief>`, the intake flow changes:

   **Step 1 — Determine episode number**
   - Read `monorepo/data/japanese/profile.yaml` → `episodes_completed` field
   - The next episode number = `episodes_completed + 1`
   - If dispatching multiple episodes at once (e.g. 4 in parallel), assign sequential numbers: N, N+1, N+2, N+3

   **Step 2 — Read from schedule.yaml (DO NOT select ad-hoc)**
   - Read `monorepo/data/japanese/schedule.yaml`
   - Find the slot for `episode_N` — use its `vocab`, `grammar`, and `japanese_ratio` exactly as specified
   - If the slot status is `queued`, proceed. If `dispatched` or `completed`, warn the user before re-dispatching.
   - If the episode slot doesn't exist in schedule.yaml yet, read `vocabulary.yaml` and `grammar.yaml` to select the next `not_started` items (5-6 vocab, 1 grammar every 2 episodes), write the new slot to schedule.yaml first, then dispatch

   **Step 2b — Comprehension gating (ratio bump check)**
   - If the slot's `japanese_ratio` is HIGHER than the previous episode's ratio, this is a tier bump
   - Check items introduced in episode N-2: read vocabulary.yaml and grammar.yaml, find items with `introduced_in: episode_(N-2)`, sum their `exposures`
   - If average exposures < 4, downgrade this episode's ratio to match the previous episode (no bump yet) and write the override back to schedule.yaml with a `gated_at: <date>` note
   - If average exposures >= 4, proceed at the scheduled ratio
   - This prevents the ratio from racing ahead of actual comprehension

   **Step 3 — Build review list**
   - Read `vocabulary.yaml` and `grammar.yaml` for all items with status `new` or `learning`
   - Include all of them as review items (the agent weaves them in naturally — no upper cap)
   - Items from the most recent 2 episodes get priority mention in the brief

   **Step 4 — Mark slot as dispatched**
   - Update `schedule.yaml`: set `episode_N.status = dispatched`
   - Increment `profile.yaml` `episodes_completed` by the number of episodes being dispatched
   - Commit: `git add data/japanese/ && git commit -m "pimsleur: dispatch episode N"`

   **Step 5 — Bundle and dispatch**
   - Bundle into an augmented brief with a `[PIMSLEUR]` marker
   - Upload `profile.yaml`, `grammar.yaml` as session resources at `/workspace/japanese/`
   - Upload `schedule.yaml` as a session resource at `/workspace/japanese/schedule.yaml`
   - Dispatch with the podcast skill — the `[PIMSLEUR]` marker activates bilingual immersion mode in `remote-skills/podcast.md`

   **After completion:** On `/autopilot status`, sync curriculum_update.yaml back:
   - Mark introduced vocab/grammar items as `new` in vocabulary.yaml / grammar.yaml
   - Update `profile.yaml` `total_exposure_hours`
   - Commit: `git add data/japanese/ && git commit -m "pimsleur: sync ep N curriculum"`

**On `/autopilot investigate <brief>`:**
1. Read `setup.md` — ensure environment setup is complete
2. Read `intake.md` — run the **investigate dispatch** flow:
   - Upload `remote-skills/investigate.md` as a custom skill
   - Upload `scripts/generate.sh` as a file (mounted at `/workspace/generate.sh`)
   - Upload `.env` as a file (mounted at `/workspace/.env`)
   - Optionally mount a GitHub repo if the investigation needs codebase access
   - Create agent with: investigate skill + brainstorming skill + agent_toolset
   - Create session and dispatch
   - The agent executes steps, collects results, writes dialogue, generates audio, delivers to Telegram

**On `/autopilot status`:**
1. Read `status.md` — follow the status check flow
2. **Critical:** Check `stop_reason` on `session.status_idle` events. If `requires_action`, the agent is blocked waiting for input — surface the question and respond.

**On `/autopilot list`:**
1. Read `.superpowers/autopilot-sessions.json`
2. For each session, fetch current status via `GET /v1/sessions/{id}`
3. Display table:

```
| # | Brief                          | Repo          | Status      | Started    |
|---|--------------------------------|---------------|-------------|------------|
| 1 | Stripe webhook handler         | clsandoval/m… | running     | 2h ago     |
| 2 | Research: PH LLM infra options | clsandoval/m… | ⚠️ blocked  | 45m ago    |
| 3 | Inbox ingestion loop           | clsandoval/m… | complete    | 3h ago     |
```

**On `/podcast <file>` or `/investigate <file>`:**
These are handled by their respective SKILL.md files in `skills/podcast/` and `skills/investigate/`. They run locally in your Claude Code session. No managed agents involved.

## API Conventions

All Managed Agents API calls use `curl` via Bash with these headers:

```bash
curl -sS https://api.anthropic.com/v1/{endpoint} \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json"
```

For skills upload, use the skills beta header:
```bash
-H "anthropic-beta: skills-2025-10-02"
```

The `ANTHROPIC_API_KEY` environment variable must be set (source from `.env` if needed).

## Local State Files

- `.superpowers/autopilot-config.json` — one-time setup results (environment ID, vault ID)
- `.superpowers/autopilot-sessions.json` — active/historical session tracking

Both files live in the project root's `.superpowers/` directory. These files should be in `.gitignore`.

## Networking Limitations

The managed agent container routes all outbound traffic through an HTTP proxy. This means:

- **No direct TCP connections** — `psql`, `mysql`, `redis-cli`, raw socket connections, and similar tools will fail with DNS resolution or connection errors
- **HTTP/HTTPS only** — `curl`, `wget`, and other HTTP clients work fine (they use the proxy)
- **For database access**, use REST APIs instead of direct connections:
  - Supabase: use the PostgREST API via `curl` with the service role key, not `psql`
  - Other databases: use any HTTP-based query API available
- **Do NOT include `psql` connection strings in briefs** — the agent will waste time trying to make them work

When the brief requires database access, provide HTTP-based credentials (API URLs + auth tokens) instead of connection strings.

## Key Principles

- **Agent created per-job** — Each dispatch creates a fresh agent with skills tailored to the task.
- **`ask_user` is the interactive bridge** — The agent calls it, the session goes idle with `stop_reason: requires_action`, and `/autopilot status` surfaces the question for the user to answer.
- **Skills are the agent's expertise** — Upload relevant skills (custom or Anthropic pre-built) based on the task.
- **Git is the persistence layer** — the agent commits to `autopilot/<slug>` branches as it works.
- **PRs are created by the orchestrator** — The `gh` CLI does not work inside the container (git proxy blocks GitHub API access). The agent pushes branches via `git push`; PRs are created by the orchestrator locally via `/autopilot status`. Alternatively, if GitHub MCP is configured with a vault credential, the agent can create PRs directly via MCP tools (`create_branch`, `create_or_update_file`, `create_pull_request`).
- **Always check `stop_reason`** — A session being `idle` doesn't mean it's done. Check `stop_reason.type`: `end_turn` = done, `requires_action` = blocked waiting for input.
- **Agent updates require versioning** — Updating an agent via `POST /v1/agents/:id` requires a `version` field for optimistic concurrency. Get the current version from the agent object before updating.
- **`agent.thinking` events exist** — The event stream includes `agent.thinking` events alongside `agent.message`. Status check code should be aware of these when parsing events.
