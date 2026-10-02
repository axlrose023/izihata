#!/usr/bin/env bash
set -euo pipefail
umask 077

app_dir="${IZIHATA_APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
backup_root="${IZIHATA_BACKUP_DIR:-/home/deployer/backups/izihata}"
mkdir -p "$backup_root"
exec 9>"$backup_root/.backup.lock"
flock -n 9 || exit 0
compose=(docker compose --project-directory "$app_dir" --env-file "$app_dir/.env.production" -f "$app_dir/compose.production.yml")
created_at="$(date -u +%Y%m%dT%H%M%SZ)"
staging="$(mktemp -d "$backup_root/.partial-$created_at.XXXXXX")"
trap 'rm -rf -- "$staging"' EXIT

"${compose[@]}" exec --interactive=false db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$staging/database.dump"
"${compose[@]}" exec -T db pg_restore --list < "$staging/database.dump" > "$staging/restore.list"
"${compose[@]}" exec --interactive=false app tar -C /app/media -czf - . > "$staging/media.tar.gz"
tar -tzf "$staging/media.tar.gz" > "$staging/media.list"
git -C "$app_dir" rev-parse HEAD > "$staging/release.txt"
(cd "$staging" && sha256sum database.dump media.tar.gz > SHA256SUMS)
mv -- "$staging" "$backup_root/daily-$created_at"
trap - EXIT
# Retention applies only to completed daily snapshots, after a new one succeeds.
find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name 'daily-*' -mtime +14 -exec rm -rf -- {} +
printf 'Backup completed: %s/daily-%s\n' "$backup_root" "$created_at"
