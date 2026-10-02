#!/usr/bin/env bash
set -euo pipefail
umask 077
app_dir="${IZIHATA_APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
state_dir="${IZIHATA_STATE_DIR:-/home/deployer/.local/state/izihata}"
backup_root="${IZIHATA_BACKUP_DIR:-/home/deployer/backups/izihata}"
mkdir -p "$state_dir"
compose=(docker compose --project-directory "$app_dir" --env-file "$app_dir/.env.production" -f "$app_dir/compose.production.yml")
report="$(mktemp "$state_dir/.health.XXXXXX")"
trap 'rm -f -- "$report"' EXIT
failed=0
for service in app frontend db cache tasks scheduler; do
  container="$("${compose[@]}" ps --all -q "$service")"
  if [[ -z "$container" ]]; then
    status=missing
  else
    status="$(docker inspect --format '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container")"
  fi
  printf '%s: %s\n' "$service" "$status" >> "$report"
  [[ "$status" == running/healthy ]] || failed=1
done
if curl --fail --silent --show-error --max-time 15 'https://izihata.com.ua/api/v1/catalog/products?include_facets=false&page_size=1' > /dev/null 2>&1; then
  printf 'public catalog: ok\n' >> "$report"
else
  printf 'public catalog: FAILED\n' >> "$report"
  failed=1
fi
if [[ -d "$backup_root" ]] && [[ -n "$(find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name 'daily-*' -mmin -1560 -print -quit)" ]]; then
  printf 'daily backup: recent\n' >> "$report"
else
  printf 'daily backup: MISSING or older than 26 hours\n' >> "$report"
  failed=1
fi
if dead="$("${compose[@]}" exec --interactive=false db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM outbox_events WHERE status='\''DEAD'\''"' 2>/dev/null)"; then
  printf 'outbox dead events: %s\n' "$dead" >> "$report"
else
  printf 'outbox count: FAILED\n' >> "$report"
  failed=1
fi
if ! cmp -s "$report" "$state_dir/health.txt"; then
  priority=daemon.notice
  [[ "$failed" == 0 && "${dead:-0}" == 0 ]] || priority=daemon.err
  logger -p "$priority" -t izihata-health -- "$(cat "$report")"
fi
mv -- "$report" "$state_dir/health.txt"
date -u +%FT%TZ > "$state_dir/last-check.txt"
cat "$state_dir/health.txt"
exit "$failed"
