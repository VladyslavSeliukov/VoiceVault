set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a
source "$SCRIPT_DIR/../.env"
set +a

: "${WHISPER_CPP_DIR:?WHISPER_CPP_DIR is not set in .env}"
: "${WHISPER_PORT:=8080}"
: "${WHISPER_MODEL:=ggml-base.en.bin}"

"$WHISPER_CPP_DIR/build/bin/whisper-server" \
    -m "$WHISPER_CPP_DIR/models/$WHISPER_MODEL" \
    --host 0.0.0.0 \
    --port "$WHISPER_PORT" \
    --convert
