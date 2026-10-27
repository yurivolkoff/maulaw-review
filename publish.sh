#!/usr/bin/env bash
# Regenerate the MauLaw digest-review site and publish it to GitHub Pages.
#
# Mac/Linux port of publish.ps1 (kept for Windows). Pure script workflow, no AI
# session required: runs build-site.py against cases.json, then commits and
# pushes docs/ (and the manifest/generator themselves) to main, which GitHub
# Pages serves from /docs. Every stage fails loudly with a nonzero exit.
#
# Usage: ./publish.sh            (from anywhere; paths resolve off this file)
#        ./publish.sh --no-push  (build + commit only)
set -euo pipefail

SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH=1
[[ "${1:-}" == "--no-push" ]] && PUSH=0

stage() { printf '\n>>> stage: %s\n' "$1"; }
fail() { printf '\n=== STAGE FAILED: %s ===\n%s\n' "$1" "$2" >&2; exit 1; }

# Stage 1: build -- regenerate docs/ from cases.json.
stage build
CASES_JSON="$SITE_DIR/cases.json"
[[ -f "$CASES_JSON" ]] || fail build "Manifest not found: $CASES_JSON"
CASE_COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' "$CASES_JSON")" \
  || fail build "Could not parse manifest: $CASES_JSON"
(cd "$SITE_DIR" && python3 build-site.py) || fail build "build-site.py failed"
[[ -f "$SITE_DIR/docs/index.html" ]] || fail build "Expected output not found: $SITE_DIR/docs/index.html"
echo "    built $CASE_COUNT case(s) -> $SITE_DIR/docs"

# Stage 2: commit -- a clean tree (nothing changed since last publish) is not an error.
stage commit
cd "$SITE_DIR"
[[ -d .git ]] || fail commit "$SITE_DIR is not a git repository"
git add cases.json build-site.py publish.ps1 publish.sh README.md .gitignore docs || fail commit "git add failed"
if [[ -z "$(git status --porcelain)" ]]; then
  echo "    nothing to commit -- tree already matches last publish"
else
  MSG="Publish review site: $CASE_COUNT case(s) ($(date +%F))"
  git commit -q -m "$MSG" || fail commit "git commit failed"
  echo "    committed: $MSG"
fi

# Stage 3: push.
if [[ $PUSH -eq 1 ]]; then
  stage push
  git push || fail push "git push failed"
fi

printf '\n=== publish complete: %s case(s) ===\n' "$CASE_COUNT"
