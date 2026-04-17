#!/usr/bin/env bash
#
# generate.sh — Turn dialogue JSON into a podcast MP3 via Gemini 3.1 Flash TTS
#
# Usage: generate.sh <dialogue.json> <output.mp3>
#
# Requires: GOOGLE_API_KEY env var, curl, jq, ffmpeg
#
# dialogue.json format: array of {speaker: "a"|"b", text: "..."}
# Speaker A = Charon, Speaker B = Kore (override with PODCAST_GEMINI_VOICE_A/B)

set -euo pipefail

DIALOGUE_JSON="$1"
OUTPUT_MP3="$2"

GEMINI_VOICE_A="${PODCAST_GEMINI_VOICE_A:-Charon}"
GEMINI_VOICE_B="${PODCAST_GEMINI_VOICE_B:-Kore}"
GEMINI_MODEL="${PODCAST_GEMINI_MODEL:-gemini-3.1-flash-tts-preview}"
GEMINI_API_BASE="https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent"
BATCH_SIZE="${PODCAST_BATCH_SIZE:-8}"

# --- Preflight checks ---

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "ERROR: GOOGLE_API_KEY is not set." >&2
  exit 1
fi

for cmd in curl jq ffmpeg; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: $cmd is not installed." >&2
    exit 1
  fi
done

if [[ ! -f "$DIALOGUE_JSON" ]]; then
  echo "ERROR: Dialogue file not found: $DIALOGUE_JSON" >&2
  exit 1
fi

# --- Setup ---

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/podcast-tts"
mkdir -p "$CACHE_DIR"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

TOTAL=$(jq 'length' "$DIALOGUE_JSON")
echo "Generating audio for $TOTAL dialogue lines (batch size: $BATCH_SIZE)..."

# --- Generate audio in batches ---

BATCH_NUM=0
CACHED=0
GENERATED=0

for START in $(seq 0 $BATCH_SIZE $((TOTAL - 1))); do
  END=$((START + BATCH_SIZE - 1))
  if [[ $END -ge $TOTAL ]]; then END=$((TOTAL - 1)); fi

  PADDED=$(printf "%04d" "$BATCH_NUM")
  CHUNK="$TMPDIR/${PADDED}.mp3"

  # Build speaker-tagged text block for this batch
  TAGGED_TEXT=""
  for i in $(seq $START $END); do
    SPEAKER=$(jq -r ".[$i].speaker" "$DIALOGUE_JSON")
    TEXT=$(jq -r ".[$i].text" "$DIALOGUE_JSON")
    SPEAKER_NAME=$([ "$SPEAKER" == "a" ] && echo "A" || echo "B")
    TAGGED_TEXT="${TAGGED_TEXT}<speaker name=\"${SPEAKER_NAME}\">${TEXT}</speaker>\n"
  done
  TAGGED_TEXT=$(printf "%b" "$TAGGED_TEXT")

  # Cache key based on batch content + voices + model
  CACHE_KEY=$(echo -n "${GEMINI_MODEL}:${GEMINI_VOICE_A}:${GEMINI_VOICE_B}:${TAGGED_TEXT}" | sha256sum | cut -d' ' -f1)
  CACHE_FILE="${CACHE_DIR}/${CACHE_KEY}.mp3"

  echo "  Batch $((BATCH_NUM + 1)) [lines $((START + 1))-$((END + 1))/$TOTAL]..."

  if [[ -f "$CACHE_FILE" ]] && ! file "$CACHE_FILE" | grep -q "JSON\|text\|ASCII\|empty"; then
    cp "$CACHE_FILE" "$CHUNK"
    CACHED=$((CACHED + 1))
    echo "    (cached)"
    BATCH_NUM=$((BATCH_NUM + 1))
    continue
  fi

  RETRIES=0
  MAX_RETRIES=3
  while true; do
    AUDIO_B64=$(curl -sS --max-time 60 \
      "${GEMINI_API_BASE}?key=${GOOGLE_API_KEY}" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg text "$TAGGED_TEXT" \
        --arg voice_a "$GEMINI_VOICE_A" \
        --arg voice_b "$GEMINI_VOICE_B" \
        '{
          contents: [{parts: [{text: $text}]}],
          generationConfig: {
            responseModalities: ["AUDIO"],
            speechConfig: {
              multiSpeakerVoiceConfig: {
                speakerVoiceConfigs: [
                  {speaker: "A", voiceConfig: {prebuiltVoiceConfig: {voiceName: $voice_a}}},
                  {speaker: "B", voiceConfig: {prebuiltVoiceConfig: {voiceName: $voice_b}}}
                ]
              }
            }
          }
        }')" | jq -r '.candidates[0].content.parts[0].inlineData.data // empty')

    if [[ -z "$AUDIO_B64" ]]; then
      RETRIES=$((RETRIES + 1))
      if [[ $RETRIES -ge $MAX_RETRIES ]]; then
        echo "ERROR: Gemini TTS returned no audio for batch $BATCH_NUM after $MAX_RETRIES retries" >&2
        exit 1
      fi
      echo "    Retry $RETRIES/$MAX_RETRIES (waiting $((2 ** RETRIES))s)..."
      sleep $((2 ** RETRIES))
      continue
    fi

    echo "$AUDIO_B64" | base64 -d > "${TMPDIR}/_pcm.raw"
    ffmpeg -y -f s16le -ar 24000 -ac 1 -i "${TMPDIR}/_pcm.raw" "$CHUNK" 2>/dev/null
    cp "$CHUNK" "$CACHE_FILE"
    GENERATED=$((GENERATED + 1))
    break
  done

  BATCH_NUM=$((BATCH_NUM + 1))
  sleep 0.5
done

echo "Audio: $GENERATED batches generated, $CACHED cached"

# --- Concatenate chunks ---

echo "Concatenating $BATCH_NUM chunks..."

CONCAT_LIST="$TMPDIR/concat.txt"
for f in "$TMPDIR"/*.mp3; do
  echo "file '$f'" >> "$CONCAT_LIST"
done

mkdir -p "$(dirname "$OUTPUT_MP3")"
ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$OUTPUT_MP3" 2>/dev/null

DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_MP3" 2>/dev/null | cut -d. -f1)
echo "Done! Podcast saved to $OUTPUT_MP3 (${DURATION}s)"
