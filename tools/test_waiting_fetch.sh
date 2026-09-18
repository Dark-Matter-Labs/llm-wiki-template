#!/usr/bin/env bash
# Tests the commons-fetch step in .github/workflows/waiting.yml, with a fake `git` that
# reports what it was asked to clone instead of cloning it.
#
# The step fetched a single COMMONS_REPO until 2026-09-18. This wiki contributes to two
# commons, so the second reported "could not be checked" every week — permanently, which
# is halfway back to a section that cannot fire. It now reads `contributes_to` from
# design/federation.json, the same list sync_commons.py uses locally.
#
# The step lives in YAML and cannot be imported, so this reads the run block straight out
# of the workflow and executes it. If the two drift, this tests nothing — which is the
# honest limit of testing shell in a workflow file, and why case 5 mutates the loop back
# to a single target and asserts case 2 drops to one clone.
#
# Usage: bash tools/test_waiting_fetch.sh
set -u
# Resolve the workflow from THIS repo, not a fixed path. The first version hardcoded the
# source wiki's path, so every sibling passed by testing a file in another repository —
# ten green runs proving one thing once.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Standard library only. This imported PyYAML at first and turned CI red, which is the
# same failure tools/community.py records for networkx and check_frontmatter.py records
# for yaml itself — twice in one day, in a codebase with no requirements.txt and no pip
# step. The block is found by name and read by indentation, which is all a YAML literal
# block needs.
BLOCK=$(WF="$HERE/.github/workflows/waiting.yml" python3 -c '
import os, sys
lines = open(os.environ["WF"], encoding="utf-8").read().split("\n")
out, indent = [], None
for i, ln in enumerate(lines):
    if indent is None:
        if ln.lstrip().startswith("- name:") and "Fetch the commons" in ln:
            for j in range(i + 1, len(lines)):
                t = lines[j].strip()
                if t.startswith("- name:"):
                    break
                if t in ("run: |", "run: |-"):
                    indent = len(lines[j]) - len(lines[j].lstrip()) + 2
                    start = j + 1
                    break
        continue
for j in range(start, len(lines)):
    ln = lines[j]
    if ln.strip() and (len(ln) - len(ln.lstrip())) < indent:
        break
    out.append(ln[indent:] if len(ln) >= indent else ln)
sys.stdout.write("\n".join(out))
' 2>/dev/null)

if [ -z "${BLOCK}" ]; then
  echo "  FAIL  no Fetch-the-commons step in $HERE/.github/workflows/waiting.yml"
  exit 1
fi

nbad=0
chk(){ if [ "$2" = "$3" ]; then echo "  PASS  $1"; else echo "  FAIL  $1"; echo "        got: $2"; echo "        want: $3"; nbad=$((nbad+1)); fi; }

run_case(){ # $1=dir  rest=env
  d=$(mktemp -d); mkdir -p "$d/bin" "$d/design"
  printf '#!/bin/sh\nfor a in "$@"; do case "$a" in https://*) echo "CLONE ${a##*@}";; esac; done\nexit 0\n' > "$d/bin/git"
  chmod +x "$d/bin/git"
  [ -n "${FED:-}" ] && printf '%s' "$FED" > "$d/design/federation.json"
  ( cd "$d" && PATH="$d/bin:$PATH" GITHUB_REPOSITORY="Dark-Matter-Labs/indy-llm-wiki" \
    TOKEN="${TOKEN:-}" COMMONS="${COMMONS:-}" bash -c "$BLOCK" 2>&1 )
  rm -rf "$d"
}

echo "1. no token — says so and fetches nothing"
out=$(TOKEN="" FED='{"contributes_to":["xco-team-wiki"]}' run_case)
chk "notice, no clone" "$(printf '%s' "$out" | grep -c CLONE)" "0"
chk "says why" "$(printf '%s' "$out" | grep -c 'COMMONS_READ_TOKEN not set')" "1"

echo "2. two declared commons — both fetched"
out=$(TOKEN=tok FED='{"contributes_to":["xco-team-wiki","power-project-wiki"]}' run_case)
chk "clones two" "$(printf '%s' "$out" | grep -c CLONE)" "2"
chk "the first" "$(printf '%s' "$out" | grep -c 'github.com/Dark-Matter-Labs/xco-team-wiki.git')" "1"
chk "the second" "$(printf '%s' "$out" | grep -c 'github.com/Dark-Matter-Labs/power-project-wiki.git')" "1"

echo "3. a commons that feeds nobody — nothing to fetch"
out=$(TOKEN=tok FED='{"contributes_to":[]}' run_case)
chk "no clone" "$(printf '%s' "$out" | grep -c CLONE)" "0"
chk "says so" "$(printf '%s' "$out" | grep -c 'declares no commons')" "1"

echo "4. COMMONS_REPO still overrides"
out=$(TOKEN=tok COMMONS="Dark-Matter-Labs/somewhere-else" FED='{"contributes_to":["xco-team-wiki","power-project-wiki"]}' run_case)
chk "clones only the override" "$(printf '%s' "$out" | grep -c CLONE)" "1"
chk "and it is the override" "$(printf '%s' "$out" | grep CLONE | grep -c somewhere-else)" "1"

echo "5. MUTATION: go back to a single default and case 2 must drop to one"
MUT=$(printf '%s' "$BLOCK" | sed 's/for C in ${TARGETS}; do/for C in ${TARGETS%% *}; do/')
d=$(mktemp -d); mkdir -p "$d/bin" "$d/design"
printf '#!/bin/sh\nfor a in "$@"; do case "$a" in https://*) echo "CLONE ${a##*@}";; esac; done\nexit 0\n' > "$d/bin/git"; chmod +x "$d/bin/git"
printf '%s' '{"contributes_to":["xco-team-wiki","power-project-wiki"]}' > "$d/design/federation.json"
out=$( cd "$d" && PATH="$d/bin:$PATH" GITHUB_REPOSITORY="Dark-Matter-Labs/indy-llm-wiki" TOKEN=tok COMMONS="" bash -c "$MUT" 2>&1 ); rm -rf "$d"
chk "mutant fetches one where the real one fetches two" "$(printf '%s' "$out" | grep -c CLONE)" "1"

echo
[ "$nbad" = 0 ] && echo "all passed" || echo "FAILURES: $nbad"
exit "$nbad"
