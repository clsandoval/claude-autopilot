---
name: autopilot
description: Use when the user wants to dispatch autonomous background work that runs without their laptop open — kicks off a Claude Managed Agent that brainstorms, specs, plans, and implements from a brief, with async Q&A via polling
---

# Autopilot — Managed Agent Command Center

Dispatch autonomous work to Claude Managed Agents. The user provides a brief (with optional local brainstorming), the agent runs on Anthropic's infrastructure, and the user checks in asynchronously via `/autopilot status`.

**Announce at start:** "I'm using the autopilot skill to [dispatch new work / check status / list sessions]."

## Two Modes of Operation

### Mode 1: Brainstorm Locally, Then Dispatch
The user wants to think through the approach first. Run the full brainstorming flow locally (approach selection, architecture decisions, constraints), then dispatch a fully-formed brief. The agent executes without deliberation.

**Use when:** The user is actively engaged and wants to make decisions now.

### Mode 2: Dispatch Fast, Answer Questions Later
The user wants to fire and forget. Send a brief (can be vague), and the agent will brainstorm autonomously and ask questions via `ask_user`. The session pauses with `requires_action` until the user responds via `/autopilot status`.

**Use when:** The user says "just dispatch it" or provides a brief and wants to move on.

**Default:** Ask the user which mode they prefer. If they provide a detailed brief with decisions already made, lean toward Mode 1. If they provide a vague brief, lean toward Mode 2.

## Subcommands

| Invocation | Action |
|---|---|
| `/autopilot` | New job — intake, configure, dispatch |
| `/autopilot status` | Check progress, answer pending questions |
| `/autopilot list` | Show all tracked sessions |

## Routing

**On `/autopilot` (no args or with a brief):**
1. Read `setup.md` — ensure one-time environment setup is complete (environment_id in config)
2. Read `intake.md` — run the intake flow:
   - Determine mode (local brainstorm vs fast dispatch)
   - If Mode 1: brainstorm locally, then configure and dispatch
   - If Mode 2: gather brief + repo/branch, configure and dispatch quickly
   - Configure agent: repo, branch, skills, include `ask_user` custom tool
   - Create agent per-job with selected skills
   - Create session and dispatch

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
- **PRs are created by the orchestrator** — The `gh` CLI does not work inside the container (git proxy blocks GitHub API access). The agent pushes branches via `git push`; PRs are created by the orchestrator locally via `/autopilot status`.
- **Always check `stop_reason`** — A session being `idle` doesn't mean it's done. Check `stop_reason.type`: `end_turn` = done, `requires_action` = blocked waiting for input.
