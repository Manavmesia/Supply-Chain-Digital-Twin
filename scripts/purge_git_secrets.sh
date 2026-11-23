#!/usr/bin/env bash
# ==============================================================================
# Script: scripts/purge_git_secrets.sh
# Purpose: Permanently purge .env files from Git repository history (F-006)
# IMPORTANT: Coordinate with all team members before executing and force-pushing.
# ==============================================================================
set -euo pipefail

echo "==> Purging .env and backend/.env from Git history..."

if command -v git-filter-repo >/dev/null 2>&1; then
    echo "Using git-filter-repo..."
    git filter-repo --path .env --path backend/.env --invert-paths --force
else
    echo "git-filter-repo not found. Using git filter-branch fallback..."
    git filter-branch --force --index-filter \
      "git rm --cached --ignore-unmatch .env backend/.env" \
      --prune-empty --tag-name-filter cat -- --all
fi

echo "==> Expiring git reflog and pruning unreachable objects..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "==> Git history scrubbing complete. Verify with:"
echo "    git log --all --full-history -- .env"
echo "==> Coordinate with team before running: git push origin --force --all"
