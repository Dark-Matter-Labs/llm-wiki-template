# For any AI agent working in this wiki

This wiki works with any coding agent: Codex, opencode, Cursor, Gemini CLI or another tool.
It was built with Claude Code, so some files carry Claude's name. Their rules apply to you too.

## Read these first, every session

1. Read `CLAUDE.md` in full. It holds this wiki's rules. Where it says "Claude", read "you".
2. Read every file in `.claude/rules/`. Claude Code loads them on its own. You must read them yourself.
3. Read `wiki/index.md` to see what the wiki holds.

A file under `.claude/` is not Claude-only. Its location is historical.

## Skills

- Each skill is a folder with one `SKILL.md`, in `.claude/skills/`.
- `.agents/skills` links to the same folder. Codex, Cursor and others look there.
- opencode also reads `.claude/skills` directly.
- When a request matches a skill's description, read its `SKILL.md` in full. Then follow it.
- `CLAUDE.md` says which skill fits which request. `python3 tools/skill_menu.py` lists them in plain words.

## Where a file names a Claude Code tool

| The file says | Do this instead |
|---|---|
| use the Skill tool, or invoke a skill | Read that skill's `SKILL.md` and follow it. |
| `AskUserQuestion` | Ask one plain question in your reply. Wait for the answer. |
| a subagent, or the Agent tool | Do the work yourself, one step at a time. |
| an Artifact, or a claude.ai page | Say your tool cannot publish one. Offer a file in the wiki. |
| `.claude/settings.json` | It sets Claude Code only. Your tool has its own settings. |

## Rules your tool will not enforce for you

Claude Code users may run hooks that stop some mistakes. Your tool does not. Keep these rules yourself:

- Never edit or delete anything in `raw/`.
- Never write a person's verification mark. `CLAUDE.md` describes it. Only a person writes one.
- Never put a `private` page, its title or a link to it on any shared or published surface.
- Never save secrets, passwords or keys in the wiki.
- Never save a change into `main` without a person's yes in the session.

The automatic checks run on GitHub for every proposed change, whichever tool wrote it.
Run the checks a skill names before you propose a change.
The full list is in `.github/workflows/checks.yml`.

## For the person choosing a tool

Another tool sends the wiki's text to the company behind it.
Dark Matter Labs has confirmed its terms with Anthropic, for Claude.
Check that a tool's terms suit internal and private pages before you use it on them.
Each page in `wiki/` shows its tier in its `visibility` field.

## Keeping this file

This file is shared by every wiki and delivered by `tools/deliver_shared.py`.
A wiki may add its own lines. Its changes are kept when the shared file changes.
`python3 tools/check_agents.py --check` confirms the skills still load in other tools.
