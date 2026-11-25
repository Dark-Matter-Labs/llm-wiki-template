# Words you may meet, and what they mean here

Claude and GitHub use words that nobody explains. This guide explains them. For each word you get what it
means, what we call it in your wiki, and what you do. Most of the time you do nothing.

You never need these words to use your wiki. Plain requests always work. Keep this page for the moment a
word appears on screen and you want to know if it matters.

---

## Part 1: Claude Code words

**Claude Code.** The version of Claude that works inside a folder of files. It reads, writes and checks
them, and it can run small programs. You reach it through the Code tab of the Claude desktop app.
*You do:* nothing. Talk to it in plain words.

**Session, or chat.** One conversation with Claude, from your first message to the last. Each new chat starts
fresh. Claude reads the wiki's rules again, but it does not recall what you said in other chats.
*You do:* start a new chat for each new task. The wiki keeps the work, so nothing is lost.

**Context.** Everything Claude can hold in mind at once: your messages, its replies, and the pages it has
read. It has a limit. People sometimes count it in *tokens*, which are small pieces of words.
*You do:* nothing, most of the time. Long tasks are easier to follow in short chats.

**Summarised, or compacted.** When a chat grows too long for the context, Claude shortens the older part into
a summary. It keeps working, but some early detail can be lost.
*You do:* if Claude seems to forget something you said early on, say it again. Or start a new chat.

**CLAUDE.md.** The instruction sheet in every wiki. Claude reads it at the start of each chat. It says what the
wiki is for and how Claude must work in it.
*You do:* nothing. To change how Claude works, say so, for example "from now on, always ask me the tier".
Claude proposes the change for you to save.

**Rules.** Short extra instruction sheets beside CLAUDE.md. Our wikis have rules on how to ask you things,
how to talk to you, and how to finish work. Most rules are shared by every wiki.
*You do:* nothing. To suggest a change for everyone, tell Claude in your own wiki.

**Memory.** Claude does not remember past chats by itself. In our wikis, the memory that lasts is the wiki:
its pages, its log and its rules. Claude Code can also keep a few notes of its own on your computer.
*You do:* if something matters, ask Claude to put it in the wiki.

**Skills.** A written set of steps for one kind of job, such as adding a source or checking the wiki. Claude
picks the right skill from what you say. Some appear in the app as names with a slash, like `/ingest`.
*You do:* say what you want in plain words. [Asking the wiki](asking-the-wiki.md) lists the phrases.

**Tools.** The actions Claude can take: read a file, search the wiki, run a check, open a web page. The app
shows each one as a small step in the chat.
*You do:* nothing. You can open a step to see what Claude did.

**Connectors, or MCP.** A connector joins Claude to another service, such as your calendar, Slack, Notion or
Google Drive. MCP is the shared standard most connectors use. You choose connectors in the app's settings.
*You do:* connect only the ones you need. In our wikis, Claude only reads your calendar. It asks before it
writes to one.

**Permissions, and approving an action.** Before some actions, the app stops and asks you to allow or deny
them. Examples are running a program, opening a web site, or sending a message.
*You do:* allow what you understand and expect. If you are unsure, deny it and ask Claude "what was that
for?". A denied action breaks nothing.

**Modes.** The app has modes that ask you more often or less often. In auto mode, Claude finishes a task
without stopping to ask at each step.
*You do:* be clear about what you want before you use auto mode. Even in auto mode, nothing is saved into
your wiki until you say yes to "Shall I merge this?".

**Plan mode.** Claude reads and thinks, then shows you a plan. It changes nothing until you accept the plan.
*You do:* use it for a big request, so you can correct the plan before any work begins.

**Subagents, or agents.** Claude can give part of a task to a helper. The helper works on its own and reports
to Claude. You see only its report, so the chat stays short.
*You do:* nothing.

**Hooks.** Automatic actions that run when Claude does a certain thing, such as a check after each edit.
They are part of the shared setup.
*You do:* nothing.

**Working folder and scratchpad.** Claude works in a copy of your wiki on your computer. That is the working
folder. A scratchpad is a temporary folder for Claude's own notes. The computer clears it later.
*You do:* nothing. The wiki on GitHub is the copy that counts.

**Rewind, or checkpoints.** The app can take a chat back to an earlier point and undo Claude's edits since
then. It undoes only the edits made in that chat.
*You do:* ask Claude to undo a change instead. In our wikis, every change is a draft first, so undoing
is always possible.

---

## Part 2: GitHub words

Your wiki keeps its history with a tool called **git**, and lives on a web site called **GitHub**. These words
come from there.

**Repository, or repo.** A folder of files together with the full history of every change to them.
*In your wiki:* the repository *is* your wiki, with its pages and its sources. *You do:* nothing.

**Commit.** One saved step in that history, with a short note on what changed. A commit is like a version in a
document's version history. The difference: you choose when each version is kept.
*In your wiki:* Claude makes the commits. *You do:* nothing.

**Branch.** A separate line of work. Changes on a branch do not touch the wiki until someone saves them in.
*In your wiki:* we call it **a draft**. *You do:* nothing.

**main.** The one branch that holds the saved wiki. In our wikis, nobody changes it directly. Every change
arrives through a proposed change, including small fixes you make yourself.
*In your wiki:* this is just **your wiki**. *You do:* nothing.

**Push and pull.** Push sends Claude's saved steps from your computer to GitHub. Pull brings the latest
version from GitHub to your computer.
*You do:* nothing. Claude does both.

**Pull request, or PR.** A request to bring a branch into main. It shows every change, line by line, and the
automatic checks run on it.
*In your wiki:* we call it **a proposed change**. *You do:* read Claude's summary of it. You rarely need the
GitHub page.

**Draft pull request.** A proposed change that is not ready yet. The automatic checks wait until Claude marks
it ready. That saves GitHub time, which costs the organisation money.
*You do:* nothing. Claude marks it ready before it asks you to save it.

**Automatic checks, or CI.** Small tests that run on every proposed change. They check spelling rules, broken
links and missing page details. A failed check stops a change from being saved.
*You do:* if one fails, ask Claude "why did the check fail?". See
[When something goes wrong](when-something-goes-wrong.md).

**Merge.** Bring a proposed change into main, so it becomes part of the wiki.
*In your wiki:* we say **save it into the wiki**. This is the question **"Shall I merge this?"**.
*You do:* say yes to save it. Say no, or say nothing, and the draft waits. [How your wiki
works](../HOW-IT-WORKS.md) explains more.

**Conflict.** Two changes touched the same lines of the same file, and git cannot choose between them. In our
wikis, the day's log is the usual place.
*In your wiki:* Claude says it "clashes". *You do:* ask Claude to redo it. It keeps both sides.

**History, and revert.** History is the list of every saved change. Revert means a new change that reverses an
older one. The older change stays in the history, so nothing is truly lost.
*You do:* to undo something, say "undo the change about X".

**Worktree.** A second working folder for the same wiki, on a different branch. Claude uses one to keep two
pieces of work apart.
*You do:* nothing.

---

## Three more things to know

**Who can see a page.** Every page has a label: `private`, `internal`, `unlisted` or `public`. Saving a page
never shares it. [How your wiki works](../HOW-IT-WORKS.md) explains each label.

**Small fixes you can make yourself.** A typo or a wrong date is yours to fix on GitHub. Anything that touches
more than one page is Claude's. [Editing the wiki yourself](../EDITING.md) shows how.

**Secrets.** Never paste a password, key or access code into a chat. If a step needs one, Claude asks you to
enter it yourself, in the right place.

---

## Further reading

These two articles explain the same ideas for any project. Our wikis use their own words, as above.

- [Claude Code for non-coders: concepts explained](https://www.mindstudio.ai/blog/claude-code-for-non-coders-concepts-explained),
  MindStudio. Auto mode, skills, MCP, hooks, memory and the context window.
- [Git in plain English](https://www.knowcode.tech/blog/git-in-plain-english/), Knowcode. Commits, branches,
  pull requests, merging and worktrees, with good everyday comparisons.
