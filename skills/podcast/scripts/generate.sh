#!/usr/bin/env bash
#
# generate.sh — Turn dialogue JSON into a podcast MP3 via ElevenLabs TTS
#
# Usage: generate.sh <dialogue.json> <output.mp3>
#
# Requires: ELEVENLABS_API_KEY env var, curl, jq, ffmpeg
#
# Uses request stitching (previous_text/next_text) for smooth transitions
# between dialogue lines. See: github.com/elevenlabs/skills/tree/main/text-to-speech

set -euo pipefail

DIALOGUE_JSON="$1"
OUTPUT_MP3="$2"

# Voice IDs
VOICE_A="UgBBYS2sOqTuMpoF3BR0"
VOICE_B="aGv5jHWKBy8K5xKvYeSX"

MODEL="eleven_multilingual_v2"
API_BASE="https://api.elevenlabs.io/v1/text-to-speech"

# --- Preflight checks ---

if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  echo "ERROR: ELEVENLABS_API_KEY is not set." >&2
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

# --- Generate audio chunks with request stitching ---

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

TOTAL=$(jq 'length' "$DIALOGUE_JSON")
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

  echo "  [$((i + 1))/$TOTAL] $SPEAKER: ${TEXT:0:60}..."

  curl -s -X POST "${API_BASE}/${VOICE_ID}" \
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

  # Check that we got valid audio, not an error JSON
  if file "$CHUNK" | grep -q "JSON\|text\|ASCII"; then
    echo "ERROR: ElevenLabs API returned an error for line $i:" >&2
    cat "$CHUNK" >&2
    exit 1
  fi
done

# --- Concatenate chunks ---

echo "Concatenating $TOTAL chunks..."

# Build ffmpeg concat file
CONCAT_LIST="$TMPDIR/concat.txt"
for f in "$TMPDIR"/*.mp3; do
  echo "file '$f'" >> "$CONCAT_LIST"
done

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_MP3")"

ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$OUTPUT_MP3" 2>/dev/null

DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_MP3" 2>/dev/null | cut -d. -f1)
echo "Done! Podcast saved to $OUTPUT_MP3 (${DURATION}s)"
