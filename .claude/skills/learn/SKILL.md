---
name: learn
description: "Turn a recurring correction or workaround into a skill, after the owner verifies it. \"make that a skill\", \"learn this pattern\"."
---

# Learn — verified pattern → new skill

This is how the wiki grows its own skills without drifting. Indy's design: *"it could ask me for
verification… then you could build verified auto-verified patterns."* The verification step is the
whole point — it is what keeps a "learned" skill trustworthy.

Offer it when the same correction or workaround appears a third time, as well as on "make that a skill".

## Method

1. **Describe the pattern in plain language** — what the recurring behaviour is, and its **trigger
   conditions** (when it should fire). Cite where you saw it recur (git/log, or the current session).
2. **Ask the owner to verify — mandatory:**
   > "Is this a pattern you want to reinforce? Should I make it a skill?"
   Wait for an explicit yes. No yes → stop; nothing is created. ("Maybe" / silence is not a yes.)
3. **On yes, draft the new `SKILL.md`** in house format (frontmatter `name` + `description`; then
   purpose, method, output, rules), following the tone of the existing skills.
4. **Register it.** Add a row to `.claude/reference/operations.md` and an entry in `tools/skill_menu.py`, and run
   `python3 tools/check_budgets.py`. Do not add it to `CLAUDE.md`.
5. **Log it:** `## [YYYY-MM-DD] learn | <skill name> verified by the owner`.

## Hard rules
- **Never create or modify a skill without the explicit verification step.** Not even a "small" one.
- **Never mark a skill as verified when it wasn't.** The log line "verified by the owner" may only be
  written after a real yes from the owner. If they tweak the pattern, verify the tweaked version.
- If the owner says no, that's a useful result — note in-session what was rejected and why (don't file a page).
