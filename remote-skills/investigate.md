---
name: remote-investigate
description: Execute a spec's testable steps inside a Managed Agent container, collect real results, generate a data-grounded podcast, deliver via Telegram.
credentials:
  - name: ANTHROPIC_API_KEY
    check: env
    required: true
  - name: GEMINI_API_KEY
    check: env
    required: true
  - name: TELEGRAM_BOT_TOKEN
    check: env
    required: true
  - name: TELEGRAM_CHAT_ID
    check: env
    required: true
interview:
  - id: spec_path
    prompt: "Path to the spec/brief to execute?"
  - id: needs_repo
    prompt: "Does the investigation need a GitHub repo mounted? (y/n)"
  - id: cost_ceiling
    prompt: "Max spend for the investigation? (e.g., '$5')"
payload:
  - path: scripts/generate.sh
    required: true
---

# Remote Investigate — Spec-to-Execution-to-Audio (Managed Agent Version)

This skill runs inside an Anthropic Managed Agent container. It executes a spec's testable
steps, collects real results, generates a podcast grounded in actual data, then delivers
via Telegram.

## Environment

- `source /workspace/.env` in EVERY bash command (separate shells)
- Audio script at `/workspace/generate.sh` (mounted by orchestrator)
- Repo at `/workspace/repo` (if mounted by orchestrator)
- Install deps: `apt-get update && apt-get install -y ffmpeg jq curl`
- `chmod +x /workspace/generate.sh`

## Phase 0 — Credential Gate

1. Read the spec/brief provided
2. Identify ALL external services, APIs, and tools required
3. Check what is available: `source /workspace/.env && env | grep -E "(key|token|secret)" | sed 's/=.*/=***/'`
4. Validate credentials with smoke tests (minimal API calls)
5. If anything critical is missing: use `ask_user` to request it
6. Estimate cost and present summary

## Phase 1 — Investigation

### Step Extraction
Parse the spec and extract testable steps. Each step becomes:
- **Name:** Human-readable description
- **Command or code:** The actual thing to run
- **Expected outcome:** What success looks like
- **Timeout:** 5 minutes default per step
- **Dependencies:** Which previous steps must succeed first

### Safety Review
Before executing any command, check for destructive operations (rm -rf, DROP TABLE, force push).
Skip destructive commands, log why, continue.

### Execution
For each step in dependency order:
1. Log: step number, name, what is about to run
2. Execute with 5-minute timeout
3. Capture: stdout, stderr, response payloads, wall-clock time
4. Record outcome: success, failure, unexpected, or timeout
5. Save artifacts to investigation directory

**Failure handling:** Log failures, skip dependent steps, continue independent ones.

**Surprise handling:** When results diverge from expectations, investigate WHY. Spend up to
2 extra API calls per surprise to explore alternatives. These are often the best podcast content.

**Total timeout:** 30 minutes for the entire investigation.

### Investigation Directory
Create at `podcasts/<name>-investigation/`:
```
<name>-investigation/
  report.md
  cost-summary.json
  steps/
    01-<step-slug>/
      command.sh
      stdout.txt
      stderr.txt
      artifacts/
```

### Investigation Report
Generate `report.md` with: summary, per-step results, surprises, cost breakdown, artifacts index.

## Phase 2 — Narration

Generate podcast dialogue from ALL investigation results.

**Person A** — The investigator. Ran the whole thing, has the results. "When I ran this" energy.
Gets excited about surprising results. Defends the spec when right, roasts it when wrong.

**Person B** — The skeptic. Reacting to real data. Asks hard questions. Has opinions, makes
connections, sometimes takes over. Multi-sentence responses, own observations.

### Dialogue Rules
- Lead with the most interesting finding, NOT step 1
- Reference ACTUAL results: real numbers, real errors, real durations
- Failures are the best content — dig into why they failed
- Two friends riffing, not an interview
- Never use "honestly", "genuinely", or "literally"
- Balance: A and B roughly equal airtime (word count within 2x)
- ~1 minute of audio per 3-4 investigation steps (150 words/minute)

Output as JSON array:
```json
[
  {"speaker": "a", "text": "So I actually ran the whole pipeline..."},
  {"speaker": "b", "text": "Wait you ran it? For real?"}
]
```

## Phase 3 — Audio Generation

1. Write JSON dialogue to `/tmp/dialogue.json`
2. Save transcript to `podcasts/<name>-transcript.md`
3. Generate audio:
   ```bash
   source /workspace/.env && bash /workspace/generate.sh /tmp/dialogue.json podcasts/<name>.mp3
   ```
4. Deliver via Telegram:
   ```bash
   source /workspace/.env
   curl -s -X POST \
     "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendAudio" \
     -F chat_id=${TELEGRAM_CHAT_ID} \
     -F audio=@"podcasts/<name>.mp3" \
     -F title="<spec name> — Investigation" \
     -F caption="<one-line summary of what the hosts discovered>"
   ```
5. Commit transcript + investigation report (NOT the .mp3) and push the branch.

## Error Handling

- Missing credentials: Phase 0 catches this, uses `ask_user`
- All steps fail: still generate a podcast about what went wrong — failures are the best content
- Audio generation fails: keep transcript and investigation artifacts, show the error
- Total timeout hit: stop execution, generate report and podcast with whatever completed
