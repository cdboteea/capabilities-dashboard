#!/bin/bash
# google-tts.sh — Google Cloud TTS wrapper
# Usage: google-tts.sh "text to speak" [output.mp3] [voice-name]
# Defaults: output=/tmp/tts-output.mp3, voice=en-US-Chirp3-HD-Charon (natural male)

set -euo pipefail

TEXT="${1:?Usage: google-tts.sh \"text\" [output.mp3] [voice]}"
OUTPUT="${2:-/tmp/tts-output.mp3}"
VOICE="${3:-en-US-Chirp3-HD-Charon}"

# Get API key from Keychain
API_KEY=$(security find-generic-password -s clawdbot-google-tts-apikey -w 2>/dev/null)
if [ -z "$API_KEY" ]; then
    echo "Error: No API key found in Keychain (clawdbot-google-tts-apikey)" >&2
    exit 1
fi

# Detect language code from voice name
LANG_CODE=$(echo "$VOICE" | grep -oE '^[a-z]{2}-[A-Z]{2}' || echo "en-US")

# Build request
JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'input': {'text': sys.argv[1]},
    'voice': {'languageCode': sys.argv[2], 'name': sys.argv[3]},
    'audioConfig': {'audioEncoding': 'MP3', 'sampleRateHertz': 24000}
}))
" "$TEXT" "$LANG_CODE" "$VOICE")

# Call API and decode
curl -s -X POST \
  "https://texttospeech.googleapis.com/v1/text:synthesize?key=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$JSON" | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
if 'audioContent' in data:
    audio = base64.b64decode(data['audioContent'])
    with open(sys.argv[1], 'wb') as f:
        f.write(audio)
    print(f'{len(audio)} bytes → {sys.argv[1]}', file=sys.stderr)
else:
    print(f'Error: {json.dumps(data)}', file=sys.stderr)
    sys.exit(1)
" "$OUTPUT"
