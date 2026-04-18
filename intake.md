# Autopilot Intake & Dispatch

## Flow Overview

Two modes of intake, chosen based on user preference:

### Mode 1: Brainstorm Locally, Then Dispatch
```
Local brainstorm → Configure agent (skills, tools) → Create agent → Create session → Dispatch brief
```

### Mode 2: Dispatch Fast, Answer Questions Later
```
Gather brief + repo → Configure agent (with ask_user) → Create agent → Dispatch → User answers via /autopilot status
```

**Ask the user which mode they want.** If they say "just dispatch it" or seem eager to move on, use Mode 2.

## Phase 1: Gather the Brief

### Mode 1 (Local Brainstorm):
1. **Understand the task** — Ask: "What are you trying to build or figure out?"
2. **Explore context** — Read relevant files in the repo, check existing specs/plans
3. **Clarify one question at a time** — Resolve ambiguities, constraints, success criteria
4. **Propose 2-3 approaches** — With trade-offs and your recommendation
5. **Get user's choice** — Lock in the approach before proceeding

The brief should be specific enough that the agent can execute without interpretation. Include:
- What to build and why
- Chosen approach and rationale
- Key decisions already made
- Pointers to relevant files in the repo
- What the deliverable is (spec only? code? research?)
- Constraints (stop after Phase N, no code, specific tech stack, etc.)

### CRITICAL: Verify Every Claim in the Brief

**Before sending any brief, double-check every concrete detail against the actual codebase.** The brief is the agent's only source of truth — if it contains wrong schemas, stale file paths, incorrect API signatures, or made-up field names, the agent wastes time discovering and working around your mistakes.

Mandatory verification checklist:
- **API schemas/payloads**: Read the actual Pydantic models or OpenAPI spec — do NOT write request bodies from memory
- **File paths**: Glob/grep to confirm files exist at the paths you cite
- **Function signatures**: Read the actual function, don't guess parameter names
- **Environment details**: Confirm URLs, auth mechanisms, and credential formats against current code
- **Field names**: Read the model definition — `label` vs `anchor_text` matters

If you skip verification, the agent will figure it out eventually by reading the codebase, but you've wasted its time and compute on a self-inflicted detour.

### Mode 2 (Fast Dispatch):
1. **Get the brief** — Can be vague ("add a useful automation to the monorepo")
2. **Confirm repo and branch** — Default to this repo, main branch
3. **Dispatch immediately** — The agent will explore, brainstorm, and ask questions via `ask_user`

## Phase 2: Configure the Agent

Based on the task, decide what the agent needs.

### Q1: Which repo?
GitHub URL, "this repo", or local path. Resolve to GitHub URL via `git remote get-url origin`.

### Q2: Which branch to base off?
Default: main.

### Q3: Which skills does this task need?

Present relevant options based on the task type:

**Anthropic pre-built skills** (available by ID):
- `xlsx` — Excel/spreadsheet work
- `pptx` — PowerPoint/presentation work
- `docx` — Word/document work
- `pdf` — PDF generation

**Custom skills** — Upload from local skill directories if needed. Any `.claude/skills/` skill or superpowers skill can be packaged and uploaded.

To upload a custom skill:
```bash
# Upload skill directory as custom skill
curl -X POST "https://api.anthropic.com/v1/skills" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: skills-2025-10-02" \
  -F "display_title=Skill Name" \
  -F "files[]=@skill_dir/SKILL.md;filename=skill_dir/SKILL.md" \
  -F "files[]=@skill_dir/other_file.md;filename=skill_dir/other_file.md"
```

The response returns a `skill_id` (like `skill_01AbCdEf...`) to attach to the agent.

### Always-Upload: Brainstorming Skill

The brainstorming skill (`$SKILL_DIR/skills/brainstorming/SKILL.md`) is ALWAYS uploaded. It enforces one-question-at-a-time `ask_user` discipline during Phase 1 exploration. Without it, agents batch questions and make poor architectural decisions.

```bash
BRAINSTORM_SKILL_RESPONSE=$(curl -sS -X POST "https://api.anthropic.com/v1/skills" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: skills-2025-10-02" \
  -F "display_title=Brainstorming" \
  -F "files[]=@$SKILL_DIR/skills/brainstorming/SKILL.md;filename=brainstorming/SKILL.md")
BRAINSTORM_SKILL_ID=$(echo "$BRAINSTORM_SKILL_RESPONSE" | jq -r '.id')
```

Add this to the skills array for every agent:
```json
{"type": "custom", "skill_id": "$BRAINSTORM_SKILL_ID", "version": "latest"}
```

### Q4: Any additional constraints?
Optional — tech stack, timeline, what NOT to do, etc.

## Phase 3: Create the Agent

Create a fresh agent tailored to this specific job. Each dispatch gets its own agent with the right skills and tools.

```bash
SYSTEM_PROMPT=$(cat "$SKILL_DIR/system-prompt.md")

SKILLS_JSON=$(jq -n '$ARGS.positional' --jsonargs "${SKILL_ENTRIES[@]}")
# Each entry is like: '{"type":"anthropic","skill_id":"xlsx"}' or '{"type":"custom","skill_id":"skill_01...","version":"latest"}'

AGENT_RESPONSE=$(curl -sS https://api.anthropic.com/v1/agents \
  -X POST \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d "$(jq -n \
    --arg name "Autopilot: $SLUG" \
    --arg system "$SYSTEM_PROMPT" \
    --argjson skills "$SKILLS_JSON" \
    '{
      name: $name,
      model: {id: "claude-sonnet-4-6[1m]", speed: "standard"},
      system: $system,
      skills: $skills,
      tools: [
        {
          type: "agent_toolset_20260401",
          default_config: {
            enabled: true,
            permission_policy: {type: "always_allow"}
          }
        },
        {
          type: "custom",
          name: "ask_user",
          description: "Ask the user a question. The session will pause until the user responds via /autopilot status. Use this for approach confirmation, ambiguous requirements, and key decision points.",
          input_schema: {
            type: "object",
            properties: {
              question: {type: "string", description: "The question to ask"},
              options: {type: "array", items: {type: "string"}, description: "Options to choose from"},
              context: {type: "string", description: "Why this question matters"}
            },
            required: ["question", "context"]
          }
        }
      ]
    }')")

AGENT_ID=$(echo "$AGENT_RESPONSE" | jq -r '.id')
AGENT_VERSION=$(echo "$AGENT_RESPONSE" | jq -r '.version')
```

## Phase 4: Create Session & Dispatch

### Step 0: Upload Credentials File (if .env exists)

If the project has a `.env` file, upload it via the Files API so the agent can run integration tests with real credentials. The file is mounted read-only at `/workspace/.env` and scoped to the session.

```bash
ENV_FILE_ID=""
if [ -f .env ]; then
  ENV_UPLOAD_RESPONSE=$(curl -sS -X POST "https://api.anthropic.com/v1/files" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: files-api-2025-04-14" \
    -F "file=@.env;filename=.env" \
    -F "purpose=agent")
  ENV_FILE_ID=$(echo "$ENV_UPLOAD_RESPONSE" | jq -r '.id // empty')
  if [ -n "$ENV_FILE_ID" ]; then
    echo "Uploaded .env as file: $ENV_FILE_ID"
  else
    echo "WARNING: .env upload failed. Agent will not have credentials."
  fi
fi
```

### Step 1: Create Session

Build the resources array: always include the GitHub repo, optionally include the .env file mount.

```bash
ENVIRONMENT_ID=$(jq -r '.environment_id' .superpowers/autopilot-config.json)
VAULT_ID=$(jq -r '.vault_id // empty' .superpowers/autopilot-config.json)
VAULT_IDS=$([ -n "$VAULT_ID" ] && echo "[\"$VAULT_ID\"]" || echo "[]")

# Build resources JSON — repo + optional .env file
RESOURCES=$(jq -n \
  --arg repo_url "$REPO_URL" \
  --arg github_token "$GITHUB_TOKEN" \
  --arg base_branch "$BASE_BRANCH" \
  --arg env_file_id "$ENV_FILE_ID" \
  '[
    {
      type: "github_repository",
      url: $repo_url,
      mount_path: "/workspace/repo",
      authorization_token: $github_token,
      checkout: {type: "branch", name: $base_branch}
    }
  ] + (if $env_file_id != "" then [{
      type: "file",
      file_id: $env_file_id,
      mount_path: "/workspace/.env"
    }] else [] end)')

curl -sS https://api.anthropic.com/v1/sessions \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d "$(jq -n \
    --arg agent_id "$AGENT_ID" \
    --argjson agent_version $AGENT_VERSION \
    --arg environment_id "$ENVIRONMENT_ID" \
    --arg title "autopilot: $SLUG" \
    --argjson resources "$RESOURCES" \
    --argjson vault_ids "$VAULT_IDS" \
    '{
      agent: {type: "agent", id: $agent_id, version: $agent_version},
      environment_id: $environment_id,
      title: $title,
      resources: $resources,
      vault_ids: $vault_ids
    }')"
```

### Step 2: Send the Brief
```bash
curl -sS "https://api.anthropic.com/v1/sessions/$SESSION_ID/events" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d "$(jq -n --arg text "$BRIEF_TEXT" '{
    events: [{
      type: "user.message",
      content: [{type: "text", text: $text}]
    }]
  }')"
```

### Step 3: Save Session to Local State
```bash
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
[ -f .superpowers/autopilot-sessions.json ] || echo '{"sessions": []}' > .superpowers/autopilot-sessions.json

jq \
  --arg id "$SESSION_ID" \
  --arg brief "$BRIEF" \
  --arg repo "$REPO_URL" \
  --arg branch "autopilot/$SLUG" \
  --arg base_branch "$BASE_BRANCH" \
  --arg agent_id "$AGENT_ID" \
  --arg started_at "$STARTED_AT" \
  '.sessions += [{
    id: $id,
    brief: $brief,
    repo: $repo,
    branch: $branch,
    base_branch: $base_branch,
    agent_id: $agent_id,
    started_at: $started_at,
    status: "running",
    last_checked_at: null
  }]' .superpowers/autopilot-sessions.json > /tmp/autopilot-sessions-tmp.json \
  && mv /tmp/autopilot-sessions-tmp.json .superpowers/autopilot-sessions.json
```

### Step 4: Confirm to User
```
Session dispatched.

  Session ID : <SESSION_ID>
  Brief      : <BRIEF>
  Repo       : <REPO_URL>
  Branch     : autopilot/<SLUG>
  Base branch: <BASE_BRANCH>
  Agent      : <AGENT_ID> (skills: <skill list>)

The agent is executing on Anthropic's infrastructure. Use /autopilot status to check progress.
```

## Podcast & Investigate Dispatch

These are specialized dispatch flows for `/autopilot podcast <brief>` and `/autopilot investigate <brief>`.

### `/autopilot podcast` Flow

1. **Upload the remote podcast skill** from `$SKILL_DIR/remote-skills/podcast.md`:
   ```bash
   PODCAST_SKILL_RESPONSE=$(curl -sS -X POST "https://api.anthropic.com/v1/skills" \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "anthropic-beta: skills-2025-10-02" \
     -F "display_title=Remote Podcast $(date +%s)" \
     -F "files[]=@$SKILL_DIR/remote-skills/podcast.md;filename=podcast/SKILL.md")
   PODCAST_SKILL_ID=$(echo "$PODCAST_SKILL_RESPONSE" | jq -r '.id')
   ```

2. **Upload generate.sh, verify-dialogue.py, and the Pimsleur reference** as session resources (not skill files). The agent reads `podcast-pimsleur.md` only for Pimsleur episodes, and runs `verify-dialogue.py` before audio gen:
   ```bash
   upload() {
     curl -sS -X POST "https://api.anthropic.com/v1/files" \
       -H "x-api-key: $ANTHROPIC_API_KEY" \
       -H "anthropic-version: 2023-06-01" \
       -H "anthropic-beta: files-api-2025-04-14" \
       -F "file=@$1;filename=$(basename $1)" -F "purpose=agent" | jq -r '.id'
   }
   SCRIPT_FILE_ID=$(upload "$SKILL_DIR/scripts/generate.sh")
   VERIFY_FILE_ID=$(upload "$SKILL_DIR/scripts/verify-dialogue.py")
   PIMSLEUR_REF_ID=$(upload "$SKILL_DIR/remote-skills/podcast-pimsleur.md")
   ```

3. **Upload .env** with Telegram (+ Google) keys (find .env in project dir or source from env vars)

4. **Create agent** with podcast skill + brainstorming skill + agent_toolset

5. **Create session** with resources mounted at:
   - `/workspace/generate.sh`
   - `/workspace/verify-dialogue.py`
   - `/workspace/podcast-pimsleur.md` (only needed for Pimsleur dispatches — safe to always mount)
   - `/workspace/.env`
   - optionally a GitHub repo if the brief needs codebase access

6. **Construct and send the brief** — the user's input IS the source material for the podcast. The brief should instruct the agent to follow the remote podcast skill.

7. Save session and confirm to user (same as generic dispatch Step 3-4)

### `/autopilot investigate` Flow

Same as podcast flow, but:
1. Upload `$SKILL_DIR/remote-skills/investigate.md` instead of podcast.md
2. A GitHub repo mount is more likely needed (the investigation may need to read/run code)
3. The brief should include the spec or reference the spec file in the mounted repo

### Shared: File Resources for Podcast/Investigate

Both flows need generate.sh and .env mounted. Add these to the resources array:

```bash
# Add to resources array alongside any GitHub repo
RESOURCES=$(jq -n \
  --arg script_file_id "$SCRIPT_FILE_ID" \
  --arg env_file_id "$ENV_FILE_ID" \
  --argjson base_resources "$BASE_RESOURCES" \
  '$base_resources + [
    {"type": "file", "file_id": $script_file_id, "mount_path": "/workspace/generate.sh"},
    {"type": "file", "file_id": $env_file_id, "mount_path": "/workspace/.env"}
  ]')
```

## Slugifying the Brief
```bash
SLUG=$(echo "$BRIEF" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//' | cut -c1-50)
```
