#!/usr/bin/env bash
#
# generate.sh — Turn dialogue JSON into a podcast MP3
#
# Primary:  Gemini 3.1 Flash TTS (multi-speaker, Charon/Kore)
# Fallback: ElevenLabs (if ELEVENLABS_API_KEY set and Gemini fails)
#
# Usage: generate.sh <dialogue.json> <output.mp3>
# Requires: GOOGLE_API_KEY, curl, jq, ffmpeg

set -euo pipefail

DIALOGUE_JSON="$1"
OUTPUT_MP3="$2"

# Gemini config
GEMINI_VOICE_A="${PODCAST_GEMINI_VOICE_A:-Charon}"
GEMINI_VOICE_B="${PODCAST_GEMINI_VOICE_B:-Kore}"
GEMINI_MODEL="${PODCAST_GEMINI_MODEL:-gemini-3.1-flash-tts-preview}"
GEMINI_PACE="${PODCAST_PACE-}"   # default: empty (natural pacing). Set PODCAST_PACE='[fast]' to rush.
GEMINI_API_BASE="https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent"
BATCH_SIZE="${PODCAST_BATCH_SIZE:-8}"

# ElevenLabs fallback config
EL_VOICE_A="${PODCAST_VOICE_A:-UgBBYS2sOqTuMpoF3BR0}"
EL_VOICE_B="${PODCAST_VOICE_B:-aGv5jHWKBy8K5xKvYeSX}"
EL_MODEL="${PODCAST_MODEL:-eleven_v3}"
EL_API_BASE="https://api.elevenlabs.io/v1/text-to-speech"

# --- Preflight ---

if [[ -z "${GOOGLE_API_KEY:-}" ]] && [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  echo "ERROR: Neither GOOGLE_API_KEY nor ELEVENLABS_API_KEY is set." >&2
  exit 1
fi

for cmd in curl jq ffmpeg; do
  command -v "$cmd" &>/dev/null || { echo "ERROR: $cmd not installed." >&2; exit 1; }
done

[[ -f "$DIALOGUE_JSON" ]] || { echo "ERROR: $DIALOGUE_JSON not found." >&2; exit 1; }

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/podcast-tts"
mkdir -p "$CACHE_DIR"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

TOTAL=$(jq 'length' "$DIALOGUE_JSON")
CACHED=0
GENERATED=0

# --- Gemini batch generation ---

gemini_batch() {
  local start=$1 end=$2 chunk=$3

  local tagged=""
  for i in $(seq $start $end); do
    local speaker text sname
    speaker=$(jq -r ".[$i].speaker" "$DIALOGUE_JSON")
    text=$(jq -r ".[$i].text" "$DIALOGUE_JSON")
    sname=$([ "$speaker" == "a" ] && echo "A" || echo "B")
    tagged="${tagged}<speaker name=\"${sname}\">${text}</speaker>\n"
  done
  local tagged_text
  tagged_text="${GEMINI_PACE} $(printf "%b" "$tagged")"

  local cache_key
  cache_key=$(echo -n "${GEMINI_MODEL}:${GEMINI_VOICE_A}:${GEMINI_VOICE_B}:${tagged_text}" | sha256sum | cut -d' ' -f1)
  local cache_file="${CACHE_DIR}/${cache_key}.mp3"

  if [[ -f "$cache_file" ]] && ! file "$cache_file" | grep -q "JSON\|text\|ASCII\|empty"; then
    cp "$cache_file" "$chunk"
    echo "    (cached)"
    CACHED=$((CACHED + 1))
    return 0
  fi

  local retries=0
  while true; do
    local audio_b64
    audio_b64=$(curl -sS --max-time 60 \
      "${GEMINI_API_BASE}?key=${GOOGLE_API_KEY}" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg text "$tagged_text" \
        --arg va "$GEMINI_VOICE_A" \
        --arg vb "$GEMINI_VOICE_B" \
        '{
          contents: [{parts: [{text: $text}]}],
          generationConfig: {
            responseModalities: ["AUDIO"],
            speechConfig: {
              multiSpeakerVoiceConfig: {
                speakerVoiceConfigs: [
                  {speaker: "A", voiceConfig: {prebuiltVoiceConfig: {voiceName: $va}}},
                  {speaker: "B", voiceConfig: {prebuiltVoiceConfig: {voiceName: $vb}}}
                ]
              }
            }
          }
        }')" | jq -r '.candidates[0].content.parts[0].inlineData.data // empty')

    if [[ -n "$audio_b64" ]]; then
      echo "$audio_b64" | base64 -d > "${TMPDIR}/_pcm.raw"
      ffmpeg -y -f s16le -ar 24000 -ac 1 -i "${TMPDIR}/_pcm.raw" "$chunk" 2>/dev/null
      cp "$chunk" "$cache_file"
      GENERATED=$((GENERATED + 1))
      return 0
    fi

    retries=$((retries + 1))
    if [[ $retries -ge 3 ]]; then return 1; fi
    echo "    Retry $retries/3..."
    sleep $((2 ** retries))
  done
}

# --- ElevenLabs line generation (fallback) ---

elevenlabs_line() {
  local idx=$1 chunk=$2
  local speaker text voice_id
  speaker=$(jq -r ".[$idx].speaker" "$DIALOGUE_JSON")
  text=$(jq -r ".[$idx].text" "$DIALOGUE_JSON")
  voice_id=$([ "$speaker" == "a" ] && echo "$EL_VOICE_A" || echo "$EL_VOICE_B")

  local cache_key cache_file
  cache_key=$(echo -n "${EL_VOICE_A}:${EL_VOICE_B}:${EL_MODEL}:${text}" | sha256sum | cut -d' ' -f1)
  cache_file="${CACHE_DIR}/${cache_key}.mp3"

  if [[ -f "$cache_file" ]] && ! file "$cache_file" | grep -q "JSON\|text\|ASCII\|empty"; then
    cp "$cache_file" "$chunk"
    CACHED=$((CACHED + 1))
    return 0
  fi

  local retries=0
  while true; do
    curl -s --max-time 30 -X POST "${EL_API_BASE}/${voice_id}" \
      -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg t "$text" --arg m "$EL_MODEL" \
        '{text:$t,model_id:$m,voice_settings:{stability:0.5,similarity_boost:0.75,style:0.5,use_speaker_boost:true}}')" \
      -o "$chunk"

    if ! file "$chunk" | grep -q "JSON\|text\|ASCII"; then
      cp "$chunk" "$cache_file"
      GENERATED=$((GENERATED + 1))
      return 0
    fi

    retries=$((retries + 1))
    if [[ $retries -ge 3 ]]; then return 1; fi
    sleep $((2 ** retries))
  done
}

# --- Main generation loop ---

USE_GEMINI=true
[[ -z "${GOOGLE_API_KEY:-}" ]] && USE_GEMINI=false

if [[ "$USE_GEMINI" == "true" ]]; then
  echo "Using Gemini 3.1 Flash TTS (${GEMINI_VOICE_A}/${GEMINI_VOICE_B}, pace: ${GEMINI_PACE})"
  echo "Generating $TOTAL lines in batches of $BATCH_SIZE..."

  BATCH_NUM=0
  for START in $(seq 0 $BATCH_SIZE $((TOTAL - 1))); do
    END=$((START + BATCH_SIZE - 1))
    [[ $END -ge $TOTAL ]] && END=$((TOTAL - 1))
    PADDED=$(printf "%04d" "$BATCH_NUM")
    CHUNK="$TMPDIR/${PADDED}.mp3"
    echo "  Batch $((BATCH_NUM + 1)) [lines $((START+1))-$((END+1))/$TOTAL]..."

    if ! gemini_batch $START $END "$CHUNK"; then
      echo "  Gemini failed — falling back to ElevenLabs for this batch"
      if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
        echo "ERROR: Gemini failed and no ELEVENLABS_API_KEY set." >&2; exit 1
      fi
      for i in $(seq $START $END); do
        LPADDED=$(printf "%04d" "$i")
        LCHUNK="$TMPDIR/el_${LPADDED}.mp3"
        elevenlabs_line $i "$LCHUNK"
        sleep 0.3
      done
      rm -f "$CHUNK"
    fi

    BATCH_NUM=$((BATCH_NUM + 1))
    sleep 0.5
  done
else
  echo "GOOGLE_API_KEY not set — using ElevenLabs"
  [[ -z "${ELEVENLABS_API_KEY:-}" ]] && { echo "ERROR: No ELEVENLABS_API_KEY either." >&2; exit 1; }
  for i in $(seq 0 $((TOTAL - 1))); do
    PADDED=$(printf "%04d" "$i")
    echo "  [$((i+1))/$TOTAL] $(jq -r ".[$i].text" "$DIALOGUE_JSON" | head -c 60)..."
    elevenlabs_line $i "$TMPDIR/${PADDED}.mp3"
    sleep 0.3
  done
fi

echo "Audio: $GENERATED generated, $CACHED cached"

# --- Concatenate ---

echo "Concatenating chunks..."
CONCAT_LIST="$TMPDIR/concat.txt"
for f in $(ls "$TMPDIR"/*.mp3 | sort); do
  echo "file '$f'" >> "$CONCAT_LIST"
done

mkdir -p "$(dirname "$OUTPUT_MP3")"
ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$OUTPUT_MP3" 2>/dev/null
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_MP3" 2>/dev/null | cut -d. -f1)
echo "Done! $(basename "$OUTPUT_MP3") — ${DURATION}s"
