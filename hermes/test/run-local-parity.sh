#!/usr/bin/env bash
# Local ingress-parity check: run the built add-on image behind an HA ingress
# emulator and walk every dashboard page directly and through ingress.
#   hermes/test/run-local-parity.sh <image> <outdir>
set -euo pipefail
IMAGE=${1:?image}
OUT=${2:?outdir}
HERE=$(cd "$(dirname "$0")" && pwd)
NET=woow-hermes-test
TOKEN=testtoken0123456789abcdefghijklmnopqrstuvwxy
mkdir -p "$OUT/data"

cleanup() {
    podman logs woow-hermes-test-addon >"$OUT/addon.log" 2>&1 || true
    podman logs woow-hermes-test-ingress >"$OUT/ingress.log" 2>&1 || true
    podman rm -f woow-hermes-test-addon woow-hermes-test-ingress >/dev/null 2>&1 || true
    podman volume rm -f woow-hermes-test-home >/dev/null 2>&1 || true
    podman network rm -f "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

PW=$(head -c 18 /dev/urandom | base64 | tr -d '/+=')
printf '%s' "$PW" >"$OUT/.pw"
jq -n --arg pw "$PW" '{dashboard_username: "admin", dashboard_password: $pw, env_vars: []}' >"$OUT/data/options.json"

podman network create --subnet 172.30.32.0/23 "$NET" >/dev/null
podman run -d --name woow-hermes-test-addon --network "$NET" --ip 172.30.33.10 --memory=3g \
    -v "$OUT/data:/data:Z" -v woow-hermes-test-home:/opt/data -p 127.0.0.1:19119:9119 "$IMAGE" >/dev/null
podman run -d --name woow-hermes-test-ingress --network "$NET" --ip 172.30.32.2 \
    -v "$HERE/ha-ingress-emulator.conf:/etc/nginx/nginx.conf:ro,Z" -p 127.0.0.1:18080:8080 \
    docker.io/library/nginx:alpine >/dev/null

for _ in $(seq 1 90); do
    curl -fsS -o /dev/null http://127.0.0.1:19119/login && break
    sleep 2
done
curl -fsS -o /dev/null http://127.0.0.1:19119/login

if [[ -z ${SKIP_WALK:-} ]]; then
    node "$HERE/walk.js" direct http://127.0.0.1:19119/ "$OUT/direct" "$OUT/.pw"
    node "$HERE/walk.js" ingress "http://127.0.0.1:18080/api/hassio_ingress/$TOKEN/" "$OUT/ingress" "$OUT/.pw"
fi
node "$HERE/test-cookie-isolation.js" http://127.0.0.1:19119/ "http://127.0.0.1:18080/api/hassio_ingress/$TOKEN/" "$OUT/.pw" \
    | tee "$OUT/cookie-isolation.txt"
if [[ -z ${SKIP_WALK:-} ]]; then
    echo "--- direct";  cat "$OUT/direct/summary.json"
    echo "--- ingress"; cat "$OUT/ingress/summary.json"
fi
