#!/usr/bin/env bash
#
# generate.sh — Turn dialogue JSON into a podcast MP3 via ElevenLabs TTS
#
# Usage: generate.sh <dialogue.json> <output.mp3>
#
# Requires: ELEVENLABS_API_KEY env var, curl, jq, ffmpeg
#
# Features:
#   - Persistent cache: already-generated chunks are reused across runs
#   - Retry with exponential backoff on API errors
#   - Rate limit protection (0.3s delay between calls)

set -euo pipefail

DIALOGUE_JSON="$1"
OUTPUT_MP3="$2"

# Voice IDs — override with PODCAST_VOICE_A / PODCAST_VOICE_B env vars
VOICE_A="${PODCAST_VOICE_A:-UgBBYS2sOqTuMpoF3BR0}"
VOICE_B="${PODCAST_VOICE_B:-aGv5jHWKBy8K5xKvYeSX}"

MODEL="${PODCAST_MODEL:-eleven_v3}"
API_BASE="https://api.elevenlabs.io/v1/text-to-speech"

# Gemini TTS fallback voices (used when ElevenLabs is unavailable)
GEMINI_VOICE_A="${PODCAST_GEMINI_VOICE_A:-Charon}"
GEMINI_VOICE_B="${PODCAST_GEMINI_VOICE_B:-Kore}"
GEMINI_API_BASE="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"

# --- Preflight checks ---

if [[ -z "${ELEVENLABS_API_KEY:-}" ]] && [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "ERROR: Neither ELEVENLABS_API_KEY nor GOOGLE_API_KEY is set." >&2
  exit 1
fi

# Detect which TTS backend to use
USE_GEMINI=false
if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  echo "No ELEVENLABS_API_KEY — falling back to Gemini TTS (Charon/Kore)"
  USE_GEMINI=true
else
  # Quick liveness check: probe ElevenLabs API
  PROBE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
    "https://api.elevenlabs.io/v1/user")
  if [[ "$PROBE" != "200" ]]; then
    echo "ElevenLabs returned HTTP $PROBE — falling back to Gemini TTS (Charon/Kore)"
    USE_GEMINI=true
  fi
fi

if [[ "$USE_GEMINI" == "true" ]] && [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "ERROR: ElevenLabs unavailable and GOOGLE_API_KEY is not set." >&2
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

# --- Generate audio chunks with caching ---

# Cache dir persists across runs — keyed by text hash so we never re-generate
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/podcast-tts"
mkdir -p "$CACHE_DIR"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

TOTAL=$(jq 'length' "$DIALOGUE_JSON")
CACHED=0
GENERATED=0
echo "Generating audio for $TOTAL dialogue lines..."

for i in $(seq 0 $((TOTAL - 1))); do
  SPEAKER=$(jq -r ".[$i].speaker" "$DIALOGUE_JSON")
  TEXT=$(jq -r ".[$i].text" "$DIALOGUE_JSON")

  if [[ "$SPEAKER" == "a" ]]; then
    VOICE_ID="$VOICE_A"
  else
    VOICE_ID="$VOICE_B"
  fi

  PADDED=$(printf "%03d" "$i")
  CHUNK="$TMPDIR/${PADDED}-${SPEAKER}.mp3"

  if [[ "$USE_GEMINI" == "true" ]]; then
    GEMINI_VOICE=$([ "$SPEAKER" == "a" ] && echo "$GEMINI_VOICE_A" || echo "$GEMINI_VOICE_B")
    CACHE_KEY=$(echo -n "gemini:${GEMINI_VOICE}:${TEXT}" | sha256sum | cut -d' ' -f1)
  else
    CACHE_KEY=$(echo -n "${VOICE_ID}:${MODEL}:${TEXT}" | sha256sum | cut -d' ' -f1)
  fi
  CACHE_FILE="${CACHE_DIR}/${CACHE_KEY}.mp3"

  if [[ -f "$CACHE_FILE" ]] && ! file "$CACHE_FILE" | grep -q "JSON\|text\|ASCII\|empty"; then
    cp "$CACHE_FILE" "$CHUNK"
    CACHED=$((CACHED + 1))
    echo "  [$((i + 1))/$TOTAL] $SPEAKER: ${TEXT:0:60}... (cached)"
    continue
  fi

  echo "  [$((i + 1))/$TOTAL] $SPEAKER: ${TEXT:0:60}..."

  RETRIES=0
  MAX_RETRIES=3
  while true; do
    if [[ "$USE_GEMINI" == "true" ]]; then
      AUDIO_B64=$(curl -sS --max-time 30 \
        "${GEMINI_API_BASE}?key=${GOOGLE_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
          --arg text "$TEXT" \
          --arg voice "$GEMINI_VOICE" \
          '{
            contents: [{parts: [{text: $text}]}],
            generationConfig: {
              responseModalities: ["AUDIO"],
              speechConfig: {voiceConfig: {prebuiltVoiceConfig: {voiceName: $voice}}}
            }
          }')" | jq -r '.candidates[0].content.parts[0].inlineData.data // empty')

      if [[ -z "$AUDIO_B64" ]]; then
        RETRIES=$((RETRIES + 1))
        if [[ $RETRIES -ge $MAX_RETRIES ]]; then
          echo "ERROR: Gemini TTS returned no audio for line $i after $MAX_RETRIES retries" >&2
          exit 1
        fi
        sleep $((2 ** RETRIES))
        continue
      fi

      echo "$AUDIO_B64" | base64 -d > /tmp/_gemini_pcm.raw
      ffmpeg -y -f s16le -ar 24000 -ac 1 -i /tmp/_gemini_pcm.raw "$CHUNK" 2>/dev/null
    else
      curl -s --max-time 30 -X POST "${API_BASE}/${VOICE_ID}" \
        -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
          --arg text "$TEXT" \
          --arg model "$MODEL" \
          '{
            text: $text,
            model_id: $model,
            voice_settings: {
              stability: 0.5,
              similarity_boost: 0.75,
              style: 0.5,
              use_speaker_boost: true
            }
          }')" \
        -o "$CHUNK"

      if file "$CHUNK" | grep -q "JSON\|text\|ASCII"; then
        RETRIES=$((RETRIES + 1))
        if [[ $RETRIES -ge $MAX_RETRIES ]]; then
          echo "ERROR: ElevenLabs API returned an error for line $i after $MAX_RETRIES retries:" >&2
          cat "$CHUNK" >&2
          exit 1
        fi
        DELAY=$((2 ** RETRIES))
        echo "    Retry $RETRIES/$MAX_RETRIES (waiting ${DELAY}s)..."
        sleep "$DELAY"
        continue
      fi
    fi

    # Valid audio — cache it
    cp "$CHUNK" "$CACHE_FILE"
    GENERATED=$((GENERATED + 1))
    break
  done

  # Small delay between API calls to avoid rate limits
  sleep 0.3
done

echo "Audio: $GENERATED generated, $CACHED cached"

# --- Concatenate chunks ---

echo "Concatenating $TOTAL chunks..."

CONCAT_LIST="$TMPDIR/concat.txt"
for f in "$TMPDIR"/*.mp3; do
  echo "file '$f'" >> "$CONCAT_LIST"
done

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_MP3")"

ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$OUTPUT_MP3" 2>/dev/null

DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_MP3" 2>/dev/null | cut -d. -f1)
echo "Done! Podcast saved to $OUTPUT_MP3 (${DURATION}s)"
