---
name: investigate
description: |
  Read a spec, execute every testable step, collect real results, then generate a podcast
  grounded in actual data — real API responses, real errors, real costs. Investigation first,
  narration second.
  Triggers: "investigate", "investigate this spec", "run and podcast", "investigate and podcast"
---

# Investigate — Spec-to-Execution-to-Audio

Read a spec, identify every testable claim, actually run the steps, collect artifacts, then
generate a podcast where two hosts narrate a completed investigation using real data. This is
NOT `/podcast` — that skill comments on docs. This skill executes them.

## Invocation

```
investigate <filepath>
```

The argument is a path to a spec, plan, or design doc with executable steps.

## Phase 0 — Credential Gate

**This is a hard gate. Nothing proceeds until every credential is confirmed.**

1. Read the spec at the given filepath
2. Identify ALL external services, APIs, and tools required:
   - API keys (OpenAI, Anthropic, Google, ElevenLabs, etc.)
   - CLI tools (yt-dlp, ffmpeg, jq, curl, python, etc.)
   - Accounts or access (Supabase, cloud services, etc.)
   - Data files or assets referenced in the spec
   - Telegram delivery (optional): `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
3. Check what is already available:
   - Source `.env` files in the project directory and repo root
   - Check environment variables with `echo $VAR_NAME`
   - Check CLI tools with `which <tool>` or `<tool> --version`
4. For anything missing: **stop and ask the user**. List exactly what is needed and why.
5. Validate every credential with a smoke test:
   - API keys: make a minimal API call (list models, ping endpoint)
   - CLI tools: run version check
   - Data files: verify they exist and are readable
6. Estimate cost:
   - Count expected API calls, estimate token usage, GPU time
   - Present a cost breakdown by service (e.g., "~$0.50 Claude API, ~$0.30 ElevenLabs")
   - Include the ElevenLabs TTS cost for Phase 3
7. Present the summary and wait for user confirmation:
   - Available credentials (confirmed working)
   - Estimated total cost
   - Expected duration
   - Number of steps to execute

**Do NOT proceed to Phase 1 until the user explicitly confirms.**

**Credential safety:** Never log, print, or include API keys in any output, transcript, report,
or dialogue. When capturing stdout/stderr, redact any strings that look like API keys or tokens.

## Phase 1 — Investigation

### Step Extraction

Parse the spec and extract an ordered list of testable steps. Look for:
- API calls with example payloads
- Scripts and CLI commands
- Data pipeline stages (extract, transform, load sequences)
- Success criteria and thresholds (hit rates, confidence scores, expected outputs)
- Validation or smoke test sections

Each step becomes a task:
- **Name:** Human-readable description (e.g., "Geolocate a dashcam frame with Claude")
- **Command or code:** The actual thing to run
- **Expected outcome:** What success looks like, per the spec
- **Timeout:** 5 minutes default per step
- **Dependencies:** Which previous steps must succeed first
- **Safety check:** Review the command before execution — no destructive operations

### Safety Review

Before executing any command, check for:
- `rm -rf`, `rm -r`, or any recursive deletion
- `DROP TABLE`, `DELETE FROM`, or destructive SQL
- `git push --force`, `git reset --hard`, or destructive git operations
- Writes to system directories outside the project
- Any command that modifies production infrastructure

If a command looks destructive, **skip it**, log why, and continue.

### Execution

For each step, in dependency order:

1. Log: step number, name, what is about to run
2. Execute the command with a 5-minute timeout
3. Capture: stdout, stderr, response payloads, generated files, wall-clock time
4. Record outcome: success, failure, unexpected result, or timeout
5. Save all artifacts to the investigation directory
6. Estimate cost for this step if possible (API calls made, tokens used)

**Failure handling:**
- Log the failure with the actual error message
- If the next step does NOT depend on this one: continue
- If the next step DOES depend on this one: skip it and log "skipped: depends on failed step N"
- If a step exceeds its timeout: kill it, log as timeout, continue

**Surprise handling — branch and explore:**
When a step produces a surprising result (unexpected failure, large divergence between expected
and actual, two approaches disagreeing wildly), don't just log it and move on. Investigate WHY.
- If two models disagree by a huge margin, dig into what each one saw and why they diverged
- If a result contradicts the spec's expectations, propose what would fix it — try an alternative
  approach if cheap and fast (e.g., "the VLM guessed coordinates badly — what if we took the
  business names it read and geocoded them via a Places API instead?")
- If something failed in a way the spec didn't anticipate, note it as a spec gap with a concrete
  suggestion for how to address it
- Budget: spend up to 2 extra API calls per surprise to explore alternatives. These branching
  explorations are often the most interesting content for the podcast.

**Total timeout:** 30 minutes for the entire investigation. If hit, stop execution, generate
the report with whatever has completed so far.

### Investigation Directory

Create this structure at `podcasts/<name>-investigation/`:

```
<name>-investigation/
  report.md                    # Structured summary (generated after all steps)
  cost-summary.json            # Total cost breakdown by service
  steps/
    01-<step-slug>/
      command.sh               # What was run
      stdout.txt               # Standard output
      stderr.txt               # Standard error (redacted of credentials)
      artifacts/               # Any generated files
    02-<step-slug>/
      ...
```

The `<name>` is derived from the input filename (strip path and extension).

### Investigation Report

After all steps complete (or total timeout), generate `report.md`:

```markdown
# Investigation Report: <spec name>

**Date:** <today>
**Spec:** <filepath>
**Duration:** <total wall-clock time>

## Summary

- Steps attempted: N
- Succeeded: N
- Failed: N
- Skipped: N
- Timed out: N

## Steps

### 1. <step name>
- **Status:** success | failure | skipped | timeout
- **Duration:** Xs
- **Command:** `<what was run>`
- **Result:** <what happened>
- **Key finding:** <the interesting part>

### 2. <step name>
...

## Surprises

<anything that contradicted the spec's expectations>

## Cost Breakdown

| Service | Calls | Est. Cost |
|---------|-------|-----------|
| ...     | ...   | ...       |
| **Total** |     | **$X.XX** |

## Artifacts Index

| File | Description |
|------|-------------|
| ...  | ...         |
```

Also generate `cost-summary.json`:
```json
{
  "total_usd": 0.00,
  "by_service": {
    "service_name": { "calls": 0, "cost_usd": 0.00 }
  },
  "duration_seconds": 0
}
```

## Prior Investigation Awareness

Before generating narration, check for prior investigation reports and podcasts for the same spec:
- Look in `podcasts/` for existing `*-investigation/report.md` files matching this spec
- Look for existing transcripts and audio files

If prior investigations exist:
- Read their reports to understand what was already tried and found
- The new podcast REPLACES all prior episodes — it is the single definitive episode
- Incorporate prior findings as baseline knowledge, not as "last time we found..."
- The hosts should present a complete picture: everything discovered across all runs
- Delete or note that prior audio files are superseded (don't delete without asking)

The goal: someone receiving this ONE file gets the full story. No "part 1 of 3." No "as we
discussed in the previous episode." One standalone episode with everything.

## Phase 2 — Narration

Generate podcast dialogue from ALL investigation results (current run + any prior runs).

### Personas

**Person A** — The investigator. Ran the whole thing, has the results, walks through what
happened. Practitioner energy: "when I ran this" and "look at what came back." Gets excited
about surprising results. Defends the spec when it was right, roasts it when it was wrong.

**Person B** — The skeptic. Didn't run it but is reacting to real data. Asks the hard
questions: "okay but what about..." and "wait, that error means..." B is NOT a prompt
machine — B has opinions, makes connections, sometimes takes over the conversation. B draws
on experience to challenge or build on findings. Give B multi-sentence responses, their own
observations, moments where they riff unprompted.

### Dialogue Rules

**Lead with the most interesting finding, not step 1.** If step 7 had a spectacular failure
or step 3 returned something nobody expected, open with that. The investigation order is not
the narrative order.

**Reference ACTUAL results.** Use real numbers, real coordinates, real confidence scores,
real error messages, real file sizes, real durations. "We got back 14.6510, 121.0325" not
"we got coordinates." "It timed out after 4 minutes 38 seconds" not "it took a while."

**Failures are the best content.** A timeout, a wrong answer, an unexpected error — these
make for better stories than everything working perfectly. Dig into why it failed. Speculate.
Argue about it.

**When results match the spec:** confirm with specifics ("the spec said 40% hit rate, we
got 43% — not bad").

**When results diverge:** that is the interesting part. Why? What does it mean? Is the spec
wrong or is the test wrong?

**Tone:** Same rules as `/podcast`:
- Two friends riffing, not an interview
- Short sentences, interruptions, false starts
- Write like people talk, not like people write
- Humor comes from specificity and real reactions
- Let them disagree, be wrong, change their mind
- At least one "wait, go back" moment
- At least one moment where they both get fired up

**Never use:** "honestly", "genuinely", or "literally" — these are AI-dialogue crutches.

**Balance rule:** A and B have roughly equal airtime. If A has spoken for 3+ lines in a row,
B takes over with a real thought, not a short reaction. Count the words: if A has 2x the
total words as B, the dialogue is too lopsided. Rewrite.

**Length:** Target ~1 minute of audio per 3-4 investigation steps. A 10-step investigation
gets a ~3 minute episode. Each minute is roughly 150 words of dialogue. Adjust based on how
interesting the results are — boring results get shorter coverage, spectacular failures get
more airtime.

**Do NOT:**
- Narrate steps in order — lead with the interesting parts
- Sound scripted — no clean transitions, no "speaking of which"
- Include API keys, tokens, or credentials in dialogue
- Summarize the spec — summarize what HAPPENED when you ran it
- Make B a one-liner machine — B's lines are as long and substantive as A's on average
- Fall into A explains, B reacts, A explains, B reacts ping-pong

## Phase 3 — Audio Generation

Reuse the existing podcast audio pipeline:

1. Generate the dialogue as a JSON array:
   ```json
   [
     {"speaker": "a", "text": "Dude, so I actually ran the whole pipeline..."},
     {"speaker": "b", "text": "Wait you ran it? Like, for real? What happened?"}
   ]
   ```
2. Save the transcript to `podcasts/<name>-transcript.md`
   - Format as readable markdown with **A:** and **B:** prefixes
3. Write the JSON array to a temp file
4. Run the audio generation script:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/generate.sh" <temp-json> podcasts/<name>.mp3
   ```
5. If `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are available, upload the MP3:
   ```bash
   curl -s -X POST \
     "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendAudio" \
     -F chat_id=${TELEGRAM_CHAT_ID} \
     -F audio=@"<output.mp3>" \
     -F title="<spec name> — Investigation" \
     -F caption="<one-line summary of what the hosts discovered>"
   ```
6. Report to the user:
   - Audio file path and duration
   - Transcript file path
   - Investigation directory path
   - Report file path
   - Total cost
   - Telegram delivery status

## Output

All files go to `podcasts/` (created if it doesn't exist):

- `<name>.mp3` — the podcast audio
- `<name>-transcript.md` — readable dialogue with speaker labels
- `<name>-investigation/report.md` — structured investigation summary
- `<name>-investigation/cost-summary.json` — cost breakdown
- `<name>-investigation/steps/` — per-step artifacts, logs, and outputs

## Error Handling

- **`ELEVENLABS_API_KEY` not set:** tell the user to set it and stop (same as `/podcast`)
- **`ffmpeg`, `jq`, or `curl` missing:** tell the user to install and stop
- **Missing project credentials:** Phase 0 catches this, asks the user, waits for confirmation
- **All investigation steps fail:** still generate a podcast about what went wrong — failures
  are the best content
- **Audio generation fails:** keep the transcript and investigation artifacts — the research
  and creative work are preserved. Show the error and the file paths.
- **Total timeout hit:** stop execution, generate report and podcast with whatever completed

## No Git Commits

The investigation artifacts, podcast, and transcript are generated output. Do not commit them.
Tell the user the file paths and let them decide.
