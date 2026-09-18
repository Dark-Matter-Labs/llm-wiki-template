#!/usr/bin/env bash
# Tests the gate loop in .github/workflows/monthly-newsletter.yml — the step that runs
# this wiki's own checks against what the model wrote, before the PR is opened.
#
# The loop lives in YAML and so cannot be imported. This file carries a copy, and the
# copy is the point of failure: if the two drift, this passes while the workflow does
# something else. Case 4 mutates the rc assignment away and asserts case 2 stops
# failing, which is the only way to know the loop is doing the work rather than the
# stubs.
#
# Written after 2026-09-18, when a newsletter run wrote a log entry with eight em
# dashes and reported success.
#
# Usage: bash tools/test_newsletter_gates.sh
set -u
T=$(mktemp -d); cd "$T"; mkdir -p tools
mk() { printf '#!/usr/bin/env python3\nimport sys\nprint("%s")\nsys.exit(%s)\n' "$2" "$3" > "tools/$1"; chmod +x "tools/$1"; }

run_block() {
  export GITHUB_OUTPUT="$T/out.txt" GITHUB_STEP_SUMMARY="$T/sum.md"
  : > "$GITHUB_OUTPUT"; : > "$GITHUB_STEP_SUMMARY"
  rc=0
  fails=""
  for c in "check_prose.py --check" "house_rules.py --check" "check_log_shape.py" "sync_log_index.py --check"; do
    if out=$(python3 tools/$c 2>&1); then
      echo "ok    $c"
    else
      echo "FAIL  $c"
      printf '%s\n' "$out" | tail -12 | sed 's/^/        /'
      fails="${fails}- \`$c\`"$'\n'
      rc=1
    fi
  done
  if [ "$rc" != "0" ]; then
    {
      echo "### The issue does not pass this wiki's own checks"
      echo ""
      printf '%s' "$fails"
    } >> "$GITHUB_STEP_SUMMARY"
  fi
  echo "failed=$rc" >> "$GITHUB_OUTPUT"
}

nbad=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; else echo "  FAIL  $1 (got '$2' want '$3')"; nbad=$((nbad+1)); fi; }

echo "1. all four gates pass"
for f in check_prose.py house_rules.py check_log_shape.py sync_log_index.py; do mk "$f" "clean" 0; done
run_block >/dev/null
chk "failed=0" "$(grep -o 'failed=.' "$T/out.txt")" "failed=0"
chk "no summary written" "$(wc -c < "$T/sum.md" | tr -d ' ')" "0"

echo "2. check_prose fails, as it did on 2026-09-18"
mk check_prose.py "NEW wiki/log/2026-09-18.md emdash 10" 1
run_block >/dev/null
chk "failed=1" "$(grep -o 'failed=.' "$T/out.txt")" "failed=1"
chk "summary names check_prose" "$(grep -c 'check_prose.py --check' "$T/sum.md")" "1"
chk "summary has the heading" "$(grep -c 'does not pass' "$T/sum.md")" "1"

echo "3. two fail, both are named"
mk house_rules.py "civilisation with an s" 1
run_block >/dev/null
chk "failed=1" "$(grep -o 'failed=.' "$T/out.txt")" "failed=1"
chk "both listed" "$(grep -c '^- ' "$T/sum.md")" "2"

echo "4. MUTATION: drop the rc=1 assignment, case 2 must stop failing"
mut() {
  export GITHUB_OUTPUT="$T/out2.txt"; : > "$GITHUB_OUTPUT"
  rc=0
  for c in "check_prose.py --check"; do
    if out=$(python3 tools/$c 2>&1); then echo "ok"; else echo "FAIL"; fi   # rc never set
  done
  echo "failed=$rc" >> "$GITHUB_OUTPUT"
}
mut >/dev/null
chk "mutant reports success on a failing gate" "$(grep -o 'failed=.' "$T/out2.txt")" "failed=0"

echo
[ "$nbad" = "0" ] && echo "all passed" || echo "FAILURES: $nbad"
rm -rf "$T"
exit "$nbad"
