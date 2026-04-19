---
name: autopilot
description: |
  Dispatch autonomous work to Claude Managed Agents through a three-gate pipeline (credentials + outcome checklist + behavior brief). Also generates podcasts and investigations locally.
  Triggers: "autopilot", "dispatch", "autopilot status", "autopilot list", "autopilot podcast", "autopilot investigate"
  Local skills /podcast and /investigate are registered separately via skills/ directory.
---

# Autopilot — Managed Agent Command Center

Dispatch autonomous work to Claude Managed Agents through a disciplined three-gate pipeline. One plugin, two execution modes:

- **Remote** (`/autopilot`) — work runs on Anthropic's infrastructure, gated by credentials + brief
- **Local** (`/podcast`, `/investigate`) — work runs in your Claude Code session

**Announce at start:** "I'm using the autopilot skill to [dispatch new work / generate a podcast / check status / list sessions]."

## The Three Gates (for every remote dispatch)

1. **Credentials** — pre-launch check; missing required cred = hard block
2. **Outcome checklist** — concrete done-criteria the remote can self-verify against
3. **Behavior / process** — free-form path: exploration vs. exploitation, heuristics, stop conditions

Gates 2+3 together form **the brief**, written as `outcome.md` + `behavior.md` in `briefs/YYYY-MM-DD-<slug>/`. Credentials are verified by `scripts/dispatch-gate.py`. No shortcuts — the skill refuses to launch with any gate unfilled.

See `dispatch.md` for the full step-by-step flow.

## Subcommands

| Invocation | Where | Action |
|---|---|---|
| `/autopilot` | Remote | New dispatch — runs the three-gate flow (see `dispatch.md`) |
| `/autopilot podcast <brief>` | Remote | Three-gate dispatch using `remote-skills/podcast.md` |
| `/autopilot podcast pimsleur <brief>` | Remote | Three-gate dispatch using `remote-skills/podcast-pimsleur.md` (episode numbering + curriculum logic runs during the interview step) |
| `/autopilot investigate <brief>` | Remote | Three-gate dispatch using `remote-skills/investigate.md` |
| `/autopilot status` | Local (polls remote) | See `poll.md` |
| `/autopilot list` | Local (polls remote) | Show all tracked sessions |
| `/podcast <file>` | Local | Narrate a doc into podcast audio (registered via skills/podcast/) |
| `/investigate <file>` | Local | Execute a spec, collect results, podcast findings (registered via skills/investigate/) |

## Routing

**On `/autopilot` (with or without a skill name):**

1. Read `setup.md` — ensure `environment_id` exists in `.superpowers/autopilot-config.json`
2. Read `dispatch.md` — run the three-gate dispatch flow

**On `/autopilot status`:**

1. Read `poll.md` — run the session status flow
2. Critical: check `stop_reason` on `session.status_idle` events. `requires_action` = blocked waiting for input.

**On `/autopilot list`:** (unchanged)

1. Read `.superpowers/autopilot-sessions.json`
2. For each session, fetch current status via `GET /v1/sessions/{id}`
3. Display table (see `poll.md` for format).

**On `/podcast <file>` or `/investigate <file>`:** local skills handle these, no managed agents involved.

## Pimsleur Episode Numbering

When dispatching `podcast-pimsleur`, the interview step (see `dispatch.md`) runs the episode-numbering logic that used to live in `intake.md`:

- Read `monorepo/data/japanese/profile.yaml` → `episodes_completed` → next episode number is +1
- Read `monorepo/data/japanese/schedule.yaml` → find `episode_<N>` slot, use its `vocab`, `grammar`, `japanese_ratio` verbatim
- Check comprehension gating (average `exposures` of episode N-2 items ≥ 8 to allow ratio bump)
- Build review list from `vocabulary.yaml` + `grammar.yaml` (status new/learning)
- Mark slot `dispatched` in `schedule.yaml`, increment `profile.yaml`, commit
- Bundle curriculum files into the payload (mount at `/workspace/japanese/`)

Write the resolved episode number, ratio, vocab, grammar, and review items into `outcome.md` so the agent self-verifies against them.

## API Conventions

All Managed Agents API calls use `curl` via Bash with these headers:

```bash
curl -sS https://api.anthropic.com/v1/{endpoint} \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json"
```

For skills upload, also include: `-H "anthropic-beta: skills-2025-10-02"`.

The `ANTHROPIC_API_KEY` environment variable must be set (source from `.env` if needed).

## Local State Files

- `.superpowers/autopilot-config.json` — one-time setup results (environment ID, vault ID)
- `.superpowers/autopilot-sessions.json` — active/historical session tracking
- `briefs/YYYY-MM-DD-<slug>/` — per-dispatch permanent record (gitignored)

## Networking Limitations

The managed agent container routes all outbound traffic through an HTTP proxy:

- **No direct TCP connections** — `psql`, `mysql`, `redis-cli`, raw sockets will fail
- **HTTP/HTTPS only** — `curl`, `wget` work fine (via proxy)
- **For database access**, use REST APIs:
  - Supabase: PostgREST via `curl` with service role key
  - Other DBs: use any HTTP-based query API
- **Do NOT include `psql` connection strings in briefs** — wastes agent time

When the brief needs DB access, provide HTTP credentials (API URLs + tokens), not connection strings.

## Key Principles

- **Three gates, every time** — No dispatch skips credentials, outcome, or behavior. The skill refuses shortcuts.
- **Agent created per-job** — Each dispatch creates a fresh agent with skills tailored to the task.
- **`ask_user` is the interactive bridge** — Agent calls it, session goes idle with `stop_reason: requires_action`, `/autopilot status` surfaces the question.
- **Skills are the agent's expertise** — Upload relevant skills (custom or Anthropic pre-built) based on the task.
- **Git is the persistence layer** — The agent commits to `autopilot/<slug>` branches as it works.
- **PRs are created by the orchestrator** — `gh` CLI does not work inside the container; PRs are created locally via `/autopilot status` (or via GitHub MCP if a vault credential is configured).
- **Always check `stop_reason`** — `end_turn` = done, `requires_action` = blocked waiting for input.
- **Agent updates require versioning** — `POST /v1/agents/:id` requires a `version` field (optimistic concurrency).
- **`agent.thinking` events exist** — Filter these out when displaying messages.
