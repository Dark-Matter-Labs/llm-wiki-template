#!/usr/bin/env python3
"""
skill_menu.py — everything this wiki can do, in plain words, each with the words to say to Claude.

Asked for on 12 October 2026: "show all skills we have and make them easier to run". The skills
live as files in `.claude/skills/`, described for a model, and run when someone types the right
phrase into Claude. Nobody can run a skill they have never heard of. This lists each one the way a
person would look for it (by what they want to do), says what it does in a line, and carries the
exact words to send. Where a skill needs one thing first ("challenge which position?"), it says so.

The app never runs a skill itself: v1 of the interface does no inference (build plan, August 2026),
so a button copies or hands over the words and the work happens in Claude, as now.

    python3 tools/skill_menu.py            # the menu, for a person
    python3 tools/skill_menu.py --json     # the menu, for the app
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
GROUPS = ["Add", "Ask and think", "Check", "Share", "Look back", "People", "Writing", "Behind the scenes"]

# name: (group, label, what it does, the words to say, what to ask for first or None)
MENU = {
    "ingest": ("Add", "Add a source", "File a report, paper or transcript, and update every page it touches.",
               "Add this to the wiki: {x}", "Which document, link or text?"),
    "call-notes": ("Add", "File call notes", "Files a week's project calls, with what was decided and who said yes to what.",
                   "Do the call notes for {x}.", "Which calls, or which week?"),
    "query": ("Ask and think", "Ask your wiki", "Answer a question from what the wiki holds, with its sources.",
              "What does the wiki say about {x}?", "What do you want to know?"),
    "office-hours": ("Ask and think", "Think an idea through", "A challenging session that sharpens an idea before you invest in it.",
                     "I have a new idea: {x}. Help me think it through.", "What is the idea?"),
    "joker": ("Ask and think", "Challenge a position", "Builds the strongest case against something you believe.",
              "Challenge this: {x}", "Which position?"),
    "inquiry": ("Ask and think", "What don't we know?", "The questions the wiki is waiting on, and one to work on.",
                "What don't we know? Help me pick one open question to work on.", None),
    "patterns": ("Ask and think", "Spot patterns", "Names patterns emerging across pages that nobody has named yet.",
                 "What patterns are emerging that we haven't named?", None),
    "delta": ("Ask and think", "Measure something against the wiki", "Where a paper or deck sits against what the wiki already holds.",
              "Run a delta on {x}.", "Which paper or deck?"),
    "gravity": ("Ask and think", "Where is the work heading?", "The centre of the wiki and which way it is moving.",
                "What's the gravity of the wiki right now?", None),
    "lint": ("Check", "Health check", "Finds stale pages, gaps, duplicates and quotes that don't match their source.",
             "Check the wiki.", None),
    "source-refresh": ("Check", "Have my sources changed?", "Checks whether the web pages behind saved sources were edited or taken down.",
                       "Check whether my sources have changed.", None),
    "retract": ("Check", "Remove something that leaked", "Finds and removes a leaked password, name or private title everywhere, without Claude seeing it.",
                "Something leaked and needs removing everywhere.", None),
    "ino-check": ("Check", "Is it inquiry-native?", "Asks whether a piece of work knows which question it serves and what would change its mind.",
                  "Run the INO check on {x}.", "Which page or draft?"),
    "publish-check": ("Check", "Is it ready to share?", "Checks a page's sources and claims before it leaves the wiki.",
                      "Is {x} ready to publish?", "Which page?"),
    "overview-refresh": ("Check", "Refresh the overview", "Rewrites the overview around what has arrived since it was last written.",
                         "Bring the overview up to date.", None),
    "rename": ("Check", "Rename something everywhere", "Carries a new name through every page, link and published copy.",
               "Rename {x} everywhere.", "What is the old name, and what is the new one?"),
    "cross-check": ("Check", "Get a second opinion", "Another model reads a page and says where it agrees or not.",
                    "Cross-check {x}.", "Which page?"),
    "source-proportion": ("Check", "Am I over-reading this?", "Checks the wiki's reading of a document stays in proportion to it.",
                          "Am I over-reading {x}?", "Which document?"),
    "contribute": ("Share", "Share with the team", "Proposes a page to the shared wiki, with personal details removed.",
                   "Share {x} with the team.", "Which page?"),
    "visual-guide": ("Writing", "Add a style guide", "Files a project's visual style guide in one shape, every value cited.",
                     "Add the style guide at {x}.", "Which guide, or where is it?"),
    "pre-read": ("Share", "Write a pre-read", "A short brief with its sources, for one meeting or audience.",
                 "Make a pre-read for {x}.", "Which meeting or audience?"),
    "live-page": ("Share", "Fix a page on the site", "Revises a published page, with a new version, checked on a phone and a laptop.",
                  "Update the published page {x}.", "Which page, and what should change?"),
    "lens-refresh": ("Share", "Refresh the lens", "Rebuilds the reading view with today's pages, ready for you to lock.",
                     "Refresh the lens.", None),
    "publish-web": ("Share", "Publish as a web page", "Turns a page into a styled page with a link you can send.",
                    "Publish {x} as a web page.", "Which page?"),
    "newsletter": ("Share", "Write the monthly newsletter", "What the wikis learned this month, written to be read.",
                   "Write the newsletter.", None),
    "my-commitments": ("Look back", "Update my commitments", "Keeps your list of open commitments current from what you say.",
                       "Update my commitments: {x}", "What is done, dropped or new?"),
    "brief": ("Look back", "Catch me up", "What's new in the wiki since you last looked.", "Catch me up.", None),
    "waiting": ("Look back", "What's waiting for me?", "Everything that needs you, in one list.", "What's waiting for me?", None),
    "reflect": ("Look back", "Weekly reflection", "How the thinking moved this week.", "Run the weekly reflection.", None),
    "weekly-review": ("Look back", "Weekly review", "A review of the week's work and what comes next.", "Run the weekly review.", None),
    "metacognition": ("Look back", "How am I using this?", "Your working patterns, and where they cost you time.",
                      "How am I using the wiki?", None),
    "coach": ("Look back", "What could my wiki do for me?", "One suggestion, from what your wiki can see.",
              "What's one thing my wiki could do for me now?", None),
    "crm": ("People", "Log a meeting or contact", "Keeps relationships as private pages, with a dated log and the next step.",
            "Log my meeting with {x}.", "Who did you meet?"),
    "leads": ("People", "Find leads", "Suggests organisations worth approaching for a goal, with the reason and source.",
              "Find leads for {x}.", "For which goal or need?"),
    "luck": ("People", "Who's worth a conversation?", "Suggests people worth talking to, from what the wiki knows.",
             "Who should I talk to next?", None),
    "ai-detox": ("Writing", "Make it sound human", "Takes the machine tells out of a draft.", "Detox this: {x}", "Which draft?"),
    "dm-style-guide": ("Writing", "Dark Matter Labs style", "Checks a draft against the house publishing standards.",
                       "Check {x} against the Dm style guide.", "Which draft?"),
    "xco-voice": ("Writing", "In xCO's voice", "Writes or rewrites something as xCO.", "Write {x} in xCO's voice.", "What should it say?"),
    "onboard": ("Behind the scenes", "Set up a new wiki", "The first session for a new person, team or option.",
                "Set up a wiki for {x}.", "For whom?"),
    "rulings": ("Behind the scenes", "Make a standing rule", "Files a lasting instruction in your words, and follows it from then on.",
                "From now on, {x}. Make that a rule.", "What should always happen?"),
    "learn": ("Behind the scenes", "Make that a skill", "Turns a pattern you keep repeating into a skill, once you confirm it.",
              "Make that a skill.", None),
    "rebuild-parity": ("Behind the scenes", "Did anything get lost?", "Checks a rebuilt artefact kept every record.",
                       "Check parity on {x}.", "Which artefact?"),
    "notion-sync": ("Behind the scenes", "Sync with Notion", "Brings Notion pages into the wiki.", "Sync from Notion.", None),
    "google-sync": ("Behind the scenes", "Sync with Google", "Brings Google Docs into the wiki.", "Sync from Google.", None),
}


def skills_held(root: pathlib.Path) -> list[str]:
    """Skills this wiki actually holds: files saved in it, not notes a plugin left lying around."""
    out = subprocess.run(["git", "ls-files", ".claude/skills/*/SKILL.md"], cwd=root, capture_output=True, text=True).stdout
    return sorted({pathlib.PurePosixPath(p).parent.name for p in out.split()})


def _first_line(root: pathlib.Path, name: str) -> str:
    text = (root / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    return (m.group(1).strip().strip("\"'").split(". ")[0] + ".") if m else ""


def build_menu(held: list[str], first_line=lambda n: "") -> list[dict]:
    """Groups in a fixed order; a skill not yet described here still appears, under Behind the scenes."""
    groups: dict[str, list] = {g: [] for g in GROUPS}
    for name in held:
        if name in MENU:
            group, label, line, say, ask = MENU[name]
        else:
            group, label, line, say, ask = ("Behind the scenes", name.replace("-", " ").capitalize(),
                                            first_line(name), f"Run the {name} skill.", None)
        groups[group].append({"skill": name, "label": label, "what": line, "say": say, "ask": ask})
    order = {name: i for i, name in enumerate(MENU)}   # the menu's own order: most useful first
    for g in groups.values():
        g.sort(key=lambda s: order.get(s["skill"], len(order)))
    return [{"group": g, "skills": groups[g]} for g in GROUPS if groups[g]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="What this wiki can do, each with the words to say to Claude.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(HERE.parent))
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    menu = build_menu(skills_held(root), lambda n: _first_line(root, n))
    if a.json:
        print(json.dumps({"wiki": root.resolve().name, "menu": menu}, indent=2, ensure_ascii=False))
        return 0
    for g in menu:
        print(f"\n{g['group']}")
        for s in g["skills"]:
            print(f"  {s['label']:34s} say: {s['say']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
