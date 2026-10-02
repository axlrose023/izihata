#!/bin/sh
set -eu

# Keep previous hashed chunks so open tabs can finish navigating after a release.
mkdir -p /usr/share/nginx/html/assets
find /usr/share/nginx/html/assets -type f -mtime +14 -delete
cp -R /opt/frontend-assets/. /usr/share/nginx/html/assets/
