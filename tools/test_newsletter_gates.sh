#!/usr/bin/env bash
# Tests the two shell blocks in .github/workflows/monthly-newsletter.yml that decide whether
# the newsletter run tells the truth: the gate step that runs this wiki's own checks against
# what the model wrote, and the block that writes the pull request body.
#
# Both live in YAML and so cannot be imported. This file carries a copy, and the copy is the
# point of failure: if the two drift, this passes while the workflow does something else.
# Case 5 mutates the rc assignment away and asserts case 2 stops failing, which is the only
# way to know the block is doing the work rather than the stubs.
#
# Written after 2026-09-18, when a newsletter run wrote a log entry with eight em dashes and
# reported success. Rewritten the same day, when the deeper defect turned out to be that the
# PR itself had no checks at all - GitHub does not fire `pull_request` workflows for a PR
# opened with the default GITHUB_TOKEN - and the step's hand-written list of four gates did
# not include `export.py --check`, which would have caught the broken link that merged.
# The list is now derived by `tools/gates.py`; `tools/test_gates.py` tests the derivation.
#
# Usage: bash tools/test_newsletter_gates.sh
set -u
WF="$(cd "$(dirname "$0")/.." && pwd)/.github/workflows/monthly-newsletter.yml"
T=$(mktemp -d); cd "$T"; mkdir -p tools

# A stand-in for tools/gates.py: prints the same first line the real one does, then either
# passes or prints the failure block the workflow greps for.
mk_gates() {   # $1 = exit code, $2.. = failing gate names
  {
    printf '#!/usr/bin/env bash\n'
    printf 'echo "27 gates, from .github/workflows/checks.yml"\n'
    if [ "$1" = "0" ]; then
      printf 'echo ""\necho "all 27 gates pass"\nexit 0\n'
    else
      shift
      printf 'echo "  FAIL  %s"\n' "$@"
      printf 'echo ""\necho "%s of 27 gates failed:"\n' "$#"
      printf 'echo "  - %s"\n' "$@"
      printf 'exit 1\n'
    fi
  } > tools/gates.sh
  chmod +x tools/gates.sh
}

# --- copy of the "Check the issue against the house gates" step ------------------------
gate_block() {
  export GITHUB_OUTPUT="$T/out.txt" GITHUB_STEP_SUMMARY="$T/sum.md"
  : > "$GITHUB_OUTPUT"; : > "$GITHUB_STEP_SUMMARY"
  rc=0
  bash tools/gates.sh > /tmp/gates.txt 2>&1 || rc=1
  cat /tmp/gates.txt
  echo "count=$(sed -n '1s/ gates,.*//p' /tmp/gates.txt)" >> "$GITHUB_OUTPUT"
  if [ "$rc" != "0" ]; then
    {
      echo "### The issue does not pass this wiki's own checks"
      echo ""
      echo '```'
      sed -n '/gates failed:/,$p' /tmp/gates.txt
      echo '```'
      echo ""
      echo "The issue is still committed and the pull request still opened, so"
      echo "nothing is lost. Read the failures above and fix them on the branch."
    } >> "$GITHUB_STEP_SUMMARY"
  fi
  echo "failed=$rc" >> "$GITHUB_OUTPUT"
}

# --- copy of the body block in "Commit and open the PR" --------------------------------
body_block() {
  {
    echo "Automated monthly issue. **Nothing has been sent.** Read it, edit it, then"
    echo "decide where it goes: the skill deliberately has no delivery path, because a"
    echo "newsletter a model can mail to the team without a person reading it first is a"
    echo "mailing list nobody consented to."
    echo ""
    if [ "${GATES_FAILED}" = "1" ]; then
      echo "### This issue does not pass this wiki's own checks"
      echo ""
      echo '```'
      sed -n '/gates failed:/,$p' /tmp/gates.txt
      echo '```'
      echo ""
      echo "It is here rather than discarded because the prose is usually worth keeping."
      echo "Fix it on this branch. A push by a person restores this PR's own checks."
    else
      echo "All ${GATES_COUNT} gates in \`.github/workflows/checks.yml\` were run against this"
      echo "branch before this PR was opened, and passed. **GitHub does not run workflows**"
      echo "**for a PR opened by \`github-actions[bot]\`**, so the Checks tab below is empty"
      echo "whether or not anything was checked. This line is the check."
    fi
  } > "$T/pr-body.md"
}

nbad=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; else echo "  FAIL  $1 (got '$2' want '$3')"; nbad=$((nbad+1)); fi; }

# Case 0 is the answer to this file's own warning. The old version of this test carried a
# copy of a four-gate loop and went on passing after the workflow stopped having one, which
# is the drift it was written to prevent happening silently. So the distinctive lines are
# asserted to exist in the real file. Only `gates.sh` differs, deliberately: the copies below
# call a stub where the workflow calls `python3 tools/gates.py`.
echo "0. the copies below still match the workflow"
for line in \
  'python3 tools/gates.py > /tmp/gates.txt 2>&1 || rc=1' \
  'echo "count=$(sed -n '"'"'1s/ gates,.*//p'"'"' /tmp/gates.txt)" >> "$GITHUB_OUTPUT"' \
  "sed -n '/gates failed:/,\$p' /tmp/gates.txt" \
  'All ${GATES_COUNT} gates in' \
  '--body-file /tmp/pr-body.md'
do
  chk "workflow still contains: ${line:0:46}" "$(grep -cF -- "$line" "$WF" > /dev/null && echo yes || echo no)" "yes"
done

echo "1. every gate passes"
mk_gates 0
gate_block >/dev/null
chk "failed=0" "$(grep -o 'failed=.' "$T/out.txt")" "failed=0"
chk "count reaches the next step" "$(grep -o 'count=..' "$T/out.txt")" "count=27"
chk "no summary written" "$(wc -c < "$T/sum.md" | tr -d ' ')" "0"

echo "2. a gate fails, as export.py would have on 2026-09-18"
mk_gates 1 "python3 tools/export.py --check"
gate_block >/dev/null
chk "failed=1" "$(grep -o 'failed=.' "$T/out.txt")" "failed=1"
chk "summary names export.py" "$(grep -c 'export.py --check' "$T/sum.md")" "1"
chk "summary has the heading" "$(grep -c 'does not pass' "$T/sum.md")" "1"

echo "3. two fail, both reach the summary"
mk_gates 1 "python3 tools/export.py --check" "python3 tools/check_links.py --check"
gate_block >/dev/null
chk "failed=1" "$(grep -o 'failed=.' "$T/out.txt")" "failed=1"
chk "both listed in the failure block" "$(grep -c '^  - python3' "$T/sum.md")" "2"

echo "4. the PR body states the outcome either way"
GATES_FAILED=1 GATES_COUNT=27 body_block
chk "failing body carries the failures" "$(grep -c 'check_links.py --check' "$T/pr-body.md")" "1"
chk "failing body does not claim a pass" "$(grep -c 'This line is the check' "$T/pr-body.md")" "0"
mk_gates 0; gate_block >/dev/null
GATES_FAILED=0 GATES_COUNT=27 body_block
chk "passing body names the count" "$(grep -c 'All 27 gates' "$T/pr-body.md")" "1"
chk "passing body warns the tab is empty" "$(grep -c 'This line is the check' "$T/pr-body.md")" "1"

echo "5. MUTATION: drop the '|| rc=1', case 2 must stop failing"
mut() {
  export GITHUB_OUTPUT="$T/out2.txt"; : > "$GITHUB_OUTPUT"
  rc=0
  bash tools/gates.sh > /tmp/gates.txt 2>&1    # rc never set
  echo "failed=$rc" >> "$GITHUB_OUTPUT"
}
mk_gates 1 "python3 tools/export.py --check"
mut >/dev/null
chk "mutant reports success on a failing gate" "$(grep -o 'failed=.' "$T/out2.txt")" "failed=0"

echo
[ "$nbad" = "0" ] && echo "all passed" || echo "FAILURES: $nbad"
rm -rf "$T"
exit "$nbad"
