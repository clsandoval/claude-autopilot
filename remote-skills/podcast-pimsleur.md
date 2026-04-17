# Pimsleur Mode — reference

Loaded when the brief contains `[PIMSLEUR]`. This is the spaced-repetition language layer that turns a normal podcast into a Japanese immersion lesson.

## Method

Pimsleur rests on four principles. The podcast adapts them:

1. **Graduated interval recall.** Classical Pimsleur recalls each item at widening intervals (~5s, 25s, 2min, 10min, 1hr). A passive podcast can't page-fault on recall, but it CAN stage exposures across an episode at widening intervals rather than clustering them.
2. **Anticipation.** Classical Pimsleur forces the learner to produce the target before hearing it. The podcast simulates the beat: speaker says the English meaning, pause or hesitation, then the Japanese lands. The listener's brain fills the gap.
3. **Core vocabulary, high-utility patterns.** Function words and everyday structures first. `schedule.yaml` encodes this — don't override.
4. **Organic grammar (inductive).** Never metalanguage ("this is the conditional form"). Use the pattern 4+ times across varied contexts. The listener absorbs the rule from the pattern.

## Curriculum source: `schedule.yaml`

The brief cites an episode number (`Episode: 5`). You MUST:

1. Find `schedule.yaml` in mounted resources — check `/workspace/japanese/` and `/mnt/session/uploads/workspace/japanese/`.
2. Find `episode_<N>` matching the brief.
3. Use its `vocab` and `grammar` lists VERBATIM. Do not invent or substitute items.
4. Use `japanese_ratio` from that entry; fall back to `profile.yaml` if absent.
5. Read `profile.yaml` for learner level and `episodes_completed`.

If the episode entry is missing, STOP — do not ad-hoc a curriculum.

## New vocabulary: 3 exposures each, spaced

Each item from `episode_<N>.vocab` must appear AT LEAST 3×, staged at roughly the **20% / 50% / 80% marks** of the episode. Don't cluster all three at the start.

Per-exposure scaffolding (decreasing English support):

1. **First** — English meaning first, hesitation, then Japanese. Anticipation beat.
   `"It was a, uh — what's the word — \"やくそく\", a promise, basically."`
2. **Second** — Japanese with light context, no re-teaching.
   `"That \"やくそく\" came back to bite us."`
3. **Third** — Japanese only, meaning from context.
   `"Yeah, \"やくそくなんだよね.\""`

### Kana > kanji for TTS

Gemini TTS mispronounces kanji because of multiple readings (音/訓). **Prefer hiragana/katakana in the dialogue JSON.** The verification script accepts either `word` (kanji) OR `reading` (kana) as a valid exposure, so write freely in kana. Transcripts can use kanji — they're for human readers.

### Quoted Japanese

Wrap every Japanese chunk in `""`:

```json
{"text": "\"なあ,\" I've been staring at the code. \"毎回,\" we pay 400ms."}
```

NOT:
```json
{"text": "なあ、I've been staring at the code. 毎回、we pay 400ms."}
```

Without quotes, the TTS sometimes skips or garbles Japanese boundaries. Quotes count toward raw char total but the CJK regex counts only kana/kanji, so the gate is unaffected.

## New grammar: 1–2 patterns × 4 exposures

Introduce inductively. Use the pattern 4+ times in varied contexts. No metalanguage. Patterns with leading `〜` (like `〜なくちゃ`) — the verification script strips the tilde automatically; just use `なくちゃ` in the dialogue.

## Review items: ≥10 present

Previously learned items listed under `=== REVIEW ITEMS ===` in the brief must appear naturally. No "remember this word?" — just use them like a fluent speaker.

## Japanese ratio — concrete thresholds

| Ratio | Feel |
|-------|------|
| 0.20 | English dominant, Japanese words / short phrases mixed in. ~30% of turns have Japanese. |
| 0.40 | Full Japanese sentences every 2–3 turns. ~60% of turns have Japanese. |
| 0.60 | Majority Japanese. English only for new concepts and clarification. ~90% of turns. |
| 0.80 | Near-full Japanese. English rare. 95% of turns. |
| 1.00 | Full Japanese. English only for a brand-new concept. 95% of turns. |

**CJK minimums** (formula: `ratio × dialogue_words × 2` — English word ≈ 2 moras; CJK char ≈ mora):

| Audio | Words | 0.20 | 0.40 | 0.60 | 0.80 | 1.00 |
|-------|-------|------|------|------|------|------|
| 30 min | 4500 | 1800 | 3600 | 5400 | 7200 | 9000 |
| 60 min | 9000 | 3600 | 7200 | 10800 | 14400 | 18000 |

Below minimum = FAIL. Rewrite with more Japanese phrases and sentences, not just single-word sprinkles.

## Pimsleur relaxes the skeptical-pragmatism posture

The main skill prescribes steelman → critique → calibrated close. In Pimsleur episodes, the topic is usually a *vehicle* for the vocab (planning a trip, daily life, etc.) — there's nothing to stress-test.

**Relax the posture when the content has no critique target.** Still Red Web warm, still dryly funny, still real disagreement — just not adversarial toward the topic. If the Pimsleur episode DOES have a claim to interrogate (power-user workflows, technical architecture), keep the posture.

## Speaker dynamics

Both A and B code-switch naturally. Neither is "the teacher." A drops Japanese terms when excited. B picks them up, sometimes uses them imperfectly, self-corrects — `"wait, \"よやくをとります\"? no, \"よやくする\", right?"` — this teaches without lecturing.

## After audio generates: write `curriculum_update.yaml`

```yaml
episode: <N>
new_vocab_introduced:
  - {word: "約束", reading: "やくそく", meaning: "promise", times_used: 3}
new_grammar_introduced:
  - {pattern: "なくちゃ", meaning: "must (casual)", times_used: 4}
items_reviewed: [食べる, 難しい, ...]
estimated_japanese_ratio: 0.XX
actual_cjk_chars: <count>
total_dialogue_words: <count>
```

Write to `/tmp/curriculum_update.yaml`. The orchestrator reads this post-completion to update `vocabulary.yaml` and `grammar.yaml`.
