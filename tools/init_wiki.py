#!/usr/bin/env python3
"""
init_wiki.py — generate a wiki's own configuration, and keep checking it afterwards.

## Why this exists

`SETUP.md` is 7.4KB of steps a person follows by hand to stand up a new wiki. Most of them
are fine — deciding who may read the repo is a judgement, and writing the owner's section of
CLAUDE.md is writing. But a handful are mechanical, and those are the ones that go wrong,
because **their failure looks like success**:

  * **The template ships `name: llm-wiki-template`** in `design/federation.json`. A wiki
    created from the template that forgets to change it still runs, still exports, still
    passes CI — and contributes upward *as the template*, stamping someone else's provenance
    on every page it sends. Nothing anywhere says otherwise.

  * **A commons needs the two-cut export**, and SETUP.md says so in bold: without it the
    commons publishes an empty public graph and every spoke syncing from it is told the sync
    succeeded. The instruction is `cp ../xco-team-wiki/tools/export.py tools/export.py`.
    A copy that never happened leaves a green repo.

  * **`display_name` is read by `export_shared.py`** to title the colleague mirror. Left at
    the template's "this LLM Wiki", nine mirrors say the same anonymous thing.

Every one of those is a fact this repo already knows about itself. So they are generated
once and **checked forever** — the second half being the point. A generator that runs on
setup day and never again is just SETUP.md with fewer words; the failures above all appear
*later*, when a role changes or a file is copied from the wrong reference.

Borrowed from qm's `deploy/layers` scaffolding, which puts it well: generate the layer rather
than hand-building it, so the parts that must be right come with it.

## What it will not do

Invent `tools/export.py`. A commons's two-cut exporter is a real program that must come from
a reference repo; this tool detects its absence and says which file to copy from where. The
line is: **configuration is generated, code is copied by a person who then reads it.**

Usage:
  python3 tools/init_wiki.py --check                 # verify this repo's own configuration
  python3 tools/init_wiki.py --init --name alex-llm-wiki --role spoke \
      --display-name "Alex's LLM Wiki" --contributes-to xco-team-wiki
  python3 tools/init_wiki.py --init ... --force      # overwrite an existing configuration
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

FEDERATION = "design/federation.json"
SOCIAL_CARD = "design/social-card.json"
MANIFEST = "design/shared-layer.json"
EXPORT = "tools/export.py"
DEPLOY_PAGES = ".github/workflows/deploy-pages.yml"

ROLES = ("spoke", "commons")

# The strings the template ships. Left in place they are not errors in any mechanical sense --
# the file parses, the tools run -- which is exactly why they need naming.
PLACEHOLDER_DISPLAY_NAMES = {"this llm wiki", "llm wiki", ""}
PLACEHOLDER_CARD_LINES = {"an llm wiki."}
TEMPLATE_NAME = "llm-wiki-template"

# The marker that distinguishes a commons's exporter from a spoke's. A spoke publishes one cut
# (wiki.public.json); a commons publishes that plus wiki.shared.json -- public + unlisted +
# internal -- which is the entire reason the `internal` tier exists.
SHARED_CUT_MARKER = "wiki.shared.json"


class Report:
    """Failures stop the gate; advisories are surfaced for a person to decide.

    `skipped` is not decoration. Half of these checks only apply to a commons, so in a spoke
    the tool passes without having tested the thing most likely to be wrong. Saying which
    checks did not run is how a vacuous pass stays visible -- this repo has shipped six gates
    that could not fire, and every one of them reported success.
    """

    def __init__(self):
        self.failures: list[str] = []
        self.advisories: list[str] = []
        self.passed: list[str] = []
        self.skipped: list[str] = []

    def fail(self, msg):      self.failures.append(msg)
    def advise(self, msg):    self.advisories.append(msg)
    def ok(self, msg):        self.passed.append(msg)
    def skip(self, msg):      self.skipped.append(msg)


def _read_json(rel, root=None):
    p = (root or ROOT) / rel
    if not p.exists():
        return None, f"{rel} does not exist"
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except ValueError as e:
        return None, f"{rel} is not valid JSON: {e}"


def known_federation(root=None) -> set[str]:
    """Every wiki name the federation knows, from the synced manifest.

    Read rather than hardcoded: the manifest travels with the shared layer, so a repo added
    to the federation becomes a legal contribution target everywhere on the next sync. A
    hardcoded list is how power-project-wiki and fang-llm-wiki went five days without tooling.
    """
    data, _ = _read_json(MANIFEST, root)
    if not data:
        return set()
    return set(data.get("siblings") or []) | ({data["source"]} if data.get("source") else set())


def check(root=None) -> Report:
    root = root or ROOT
    r = Report()

    fed, err = _read_json(FEDERATION, root)
    if err:
        r.fail(f"{err} — every wiki must declare its place in the graph; "
               f"run: python3 tools/init_wiki.py --init --name <repo> --role spoke ...")
        return r

    # ---- identity ---------------------------------------------------------------------
    for key in ("name", "role", "display_name", "contributes_to"):
        if key not in fed:
            r.fail(f"{FEDERATION} has no `{key}`")
    if r.failures:
        return r

    name, role = fed["name"], fed["role"]
    ups = list(fed.get("contributes_to") or [])
    repo_dir = root.name

    if role not in ROLES:
        r.fail(f"role `{role}` is not one of {', '.join(ROLES)}")
    else:
        r.ok(f"role `{role}` is valid")

    if name != repo_dir:
        r.fail(f"`name` is `{name}` but the repository directory is `{repo_dir}`. "
               f"Provenance is stamped from `name`, so this wiki would contribute as "
               f"`{name}`" + (" — the template's own identity, which is the default nobody "
                              "notices" if name == TEMPLATE_NAME else ""))
    else:
        r.ok(f"`name` matches the repository directory (`{repo_dir}`)")

    # The template is the one repo where the placeholders are the correct content: it exists
    # to be copied, and a template with Indy's name in it would seed nine wikis called Indy's.
    # So the placeholder checks are inverted here rather than skipped -- a template that has
    # LOST its placeholder has been edited in place, which is its own quiet failure.
    is_template = (name == TEMPLATE_NAME)
    placeholder_display = str(fed["display_name"]).strip().lower() in PLACEHOLDER_DISPLAY_NAMES
    if is_template:
        if placeholder_display:
            r.ok("template: `display_name` is a placeholder, which is what a template ships")
        else:
            r.fail(f"this is the template but `display_name` is `{fed['display_name']}` — a "
                   f"real name here seeds every wiki created from it with someone else's")
    elif placeholder_display:
        r.fail(f"`display_name` is still the template placeholder "
               f"(`{fed['display_name']}`). export_shared.py titles the colleague mirror "
               f"with it, so the mirror is anonymous until this is set.")
    else:
        r.ok(f"`display_name` is set (`{fed['display_name']}`)")

    # ---- the graph --------------------------------------------------------------------
    if name in ups:
        r.fail(f"`contributes_to` contains this wiki's own name (`{name}`) — a wiki cannot "
               f"contribute to itself, and sync_commons.py would clone the repo into itself")

    if role == "spoke" and not ups:
        r.fail("a spoke with an empty `contributes_to` has nowhere to contribute and nothing "
               "to sync down. Either name a commons, or declare `role: commons`.")
    elif ups:
        r.ok(f"`contributes_to` names {len(ups)} target(s): {', '.join(ups)}")
    else:
        r.ok("top commons: nothing sits above it, and `contributes_to` is correctly empty")

    known = known_federation(root)
    if known:
        unknown = [u for u in ups if u not in known]
        if unknown:
            r.fail(f"`contributes_to` names {', '.join(unknown)}, which the federation "
                   f"manifest ({MANIFEST}) does not list. contribute.py would open a pull "
                   f"request against a repo nothing else knows about.")
        else:
            r.ok("every contribution target is a known federation member")
    else:
        r.skip(f"contribution targets unverified — {MANIFEST} is missing, so there is no "
               f"list to check them against")

    # ---- role-dependent: the commons two-cut export -------------------------------------
    # SETUP.md calls this one not optional, and it is the failure that looks most like
    # success: a commons defaults every page to `internal`, so a spoke's exporter publishes
    # an empty public graph, green, forever.
    is_commons = (role == "commons")
    export = root / EXPORT
    if not is_commons:
        r.skip("two-cut export not checked — this is a spoke, which correctly publishes only "
               "wiki.public.json")
    elif not export.exists():
        r.fail(f"{EXPORT} does not exist in a commons")
    elif SHARED_CUT_MARKER in export.read_text(encoding="utf-8"):
        r.ok(f"commons exporter writes the shared cut ({SHARED_CUT_MARKER})")
    else:
        r.fail(f"this is a commons but {EXPORT} never writes {SHARED_CUT_MARKER}. It is the "
               f"spoke exporter. A commons defaults its pages to `internal`, so the public "
               f"cut is empty by construction and every spoke syncing from it is told the "
               f"sync succeeded. Copy the commons version:\n"
               f"      cp ../xco-team-wiki/tools/export.py tools/export.py\n"
               f"      cp ../xco-team-wiki/.github/workflows/export.yml .github/workflows/")

    # ---- advisories: real cases exist on both sides -------------------------------------
    if is_commons and (root / DEPLOY_PAGES).exists():
        r.advise(f"a commons with {DEPLOY_PAGES}. SETUP.md says a commons is not a publishing "
                 f"surface — but power-project-wiki was given one on 2026-09-04 by an explicit "
                 f"decision, so this is a question, not a defect. Confirm it was decided.")

    card, card_err = _read_json(SOCIAL_CARD, root)
    if card_err:
        r.skip(f"card wording not checked — {SOCIAL_CARD} is absent, and a wiki with no site "
               f"does not need one")
    elif any(str(l).strip().lower() in PLACEHOLDER_CARD_LINES for l in card.get("lines") or []):
        if is_template:
            r.ok("template: card wording is a placeholder, which is what a template ships")
        else:
            r.advise(f"{SOCIAL_CARD} still carries the placeholder wording. Every social card "
                     f"this wiki generates will say it.")
    else:
        r.ok(f"{SOCIAL_CARD} carries this wiki's own wording")

    return r


# ---------------------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------------------

def render_federation(name, role, display_name, ups) -> dict:
    return {
        "_comment": "This wiki's place in the federation. Per-repo and deliberately NOT part "
                    "of the synced design layer — the design system travels between wikis, a "
                    "wiki's position in the graph does not.",
        "name": name,
        "display_name": display_name,
        "role": role,
        "contributes_to": ups,
        "_note": "Generated by tools/init_wiki.py. `contributes_to` does double duty: the "
                 "UP-flow target for contribute.py, and the list sync-commons.yml clones DOWN "
                 "into .commons/<name>/export.",
        "pre_split_months": [],
        "_pre_split_note": "Months kept as a single log file because they predate the "
                           "2026-08-13 per-day split. Empty in any wiki created after it.",
    }


def render_card(display_name) -> dict:
    return {
        "_comment": "This wiki's own card wording. Deliberately NOT part of the shared design "
                    "layer — sync_design_system.py copies the generator, never this file, so "
                    "no wiki inherits another's tagline. Replace these lines.",
        "kicker": "DARK MATTER LABS",
        "lines": [display_name],
        "footer": "dark-matter-labs.github.io",
    }


def init(name, role, display_name, ups, force=False, root=None) -> tuple[int, list[str]]:
    root = root or ROOT
    written, refused = [], []

    if role not in ROLES:
        return 1, [f"role must be one of {', '.join(ROLES)} — got `{role}`"]
    if role == "spoke" and not ups:
        return 1, ["a spoke needs at least one --contributes-to target"]
    if name in ups:
        return 1, [f"`{name}` cannot contribute to itself"]

    for rel, payload in ((FEDERATION, render_federation(name, role, display_name, ups)),
                         (SOCIAL_CARD, render_card(display_name))):
        p = root / rel
        if p.exists() and not force:
            refused.append(f"{rel} already exists — not overwritten (pass --force to replace)")
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(rel)

    lines = [f"wrote {r}" for r in written] + refused
    return 0, lines


def human_remainder(role) -> list[str]:
    """What a script must not do on someone's behalf.

    Each of these is a judgement or a piece of writing. Listing them here rather than leaving
    them in prose means the generator's output ends with the real remaining work, instead of
    implying setup is finished.
    """
    items = [
        "Decide who can READ the repo. `visibility:` governs publication, not repo access — "
        "on GitHub anyone who can open the repo reads every private page and all of raw/. "
        "See SHARING-AND-ACCESS.md, and verify it with a second account.",
        "Write the owner's section of CLAUDE.md (\"Who you are working with\"). This is what "
        "makes the wiki a librarian for one person rather than a generic one.",
        "Write wiki/overview.md — a sentence or two on what is being accumulated here.",
        f"Replace the placeholder line in {SOCIAL_CARD} with this wiki's own wording.",
    ]
    if role == "commons":
        items += [
            f"Copy the two-cut exporter, which this tool will not invent:\n"
            f"       cp ../xco-team-wiki/tools/export.py tools/export.py\n"
            f"       cp ../xco-team-wiki/.github/workflows/export.yml .github/workflows/\n"
            f"     then verify with: python3 tools/export.py && ls export/",
            "Copy tools/check_no_private.py from a commons and wire it into checks.yml as an "
            "advisory step (it warns; a reviewer decides).",
            "Delete .github/workflows/deploy-pages.yml unless publishing was decided on "
            "purpose — a commons is not a publishing surface by default.",
        ]
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate and check a wiki's own configuration.")
    ap.add_argument("--check", action="store_true", help="verify this repo's configuration")
    ap.add_argument("--init", action="store_true", help="write the configuration files")
    ap.add_argument("--name", help="repository name, e.g. alex-llm-wiki")
    ap.add_argument("--role", choices=ROLES, default="spoke")
    ap.add_argument("--display-name", dest="display_name", help='e.g. "Alex\'s LLM Wiki"')
    ap.add_argument("--contributes-to", dest="ups", default="",
                    help="comma-separated commons this wiki contributes up to")
    ap.add_argument("--force", action="store_true", help="overwrite existing configuration")
    args = ap.parse_args(argv)

    if args.init:
        if not args.name or not args.display_name:
            print("--init needs --name and --display-name", file=sys.stderr)
            return 1
        ups = [u.strip() for u in args.ups.split(",") if u.strip()]
        code, lines = init(args.name, args.role, args.display_name, ups, force=args.force)
        for l in lines:
            print(f"  {l}")
        if code:
            return code
        print(f"\nGenerated. Still yours to do — a script must not decide these:\n")
        for i, item in enumerate(human_remainder(args.role), 1):
            print(f"  {i}. {item}")
        print(f"\nThen: python3 tools/init_wiki.py --check")
        return 0

    if not args.check:
        ap.print_help()
        return 0

    r = check()
    for m in r.passed:
        print(f"  ok       {m}")
    for m in r.skipped:
        print(f"  skipped  {m}")
    for m in r.advisories:
        print(f"  ADVISORY {m}")
    for m in r.failures:
        print(f"  FAIL     {m}", file=sys.stderr)

    print()
    if r.failures:
        print(f"{len(r.failures)} problem(s) with this wiki's configuration.", file=sys.stderr)
        return 1
    note = f" ({len(r.skipped)} check(s) not applicable to this role)" if r.skipped else ""
    print(f"configuration OK{note}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
