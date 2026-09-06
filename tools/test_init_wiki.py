#!/usr/bin/env python3
"""
test_init_wiki.py — the properties that make a setup gate worth having.

A generator that only runs on setup day is SETUP.md with fewer words. What makes this tool
worth its file is that `--check` keeps firing afterwards, so the properties that matter are:
it must catch the three failures that LOOK LIKE SUCCESS (a wiki still called the template, a
commons running the spoke exporter, an anonymous colleague mirror); it must not fire on the
one repo where placeholders are correct; it must say out loud which checks its role skipped,
because this repo has shipped six gates that could not fire and every one reported success;
and anything it generates must pass its own check, or the two halves have drifted apart.

  python3 tools/test_init_wiki.py
"""

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import init_wiki as iw      # noqa: E402

FAILED = []

SPOKE_EXPORT = "writes export/wiki.public.json and nothing else\n"
COMMONS_EXPORT = "writes export/wiki.public.json and export/wiki.shared.json\n"

FEDERATION_MEMBERS = ["xco-team-wiki", "power-project-wiki", "alex-llm-wiki",
                      "llm-wiki-template"]


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def wiki(tmp, dirname, *, name=None, role="spoke", display_name="Alex's LLM Wiki",
         ups=("xco-team-wiki",), export=None, card_line="Something of our own.",
         deploy_pages=False, manifest=True, federation=True, bad_json=False):
    """A minimal wiki on disk. The directory name matters: `name` is checked against it."""
    root = pathlib.Path(tmp) / dirname
    (root / "design").mkdir(parents=True)
    (root / "tools").mkdir()

    if federation:
        p = root / "design" / "federation.json"
        if bad_json:
            p.write_text("{ not json", encoding="utf-8")
        else:
            p.write_text(json.dumps({
                "name": name if name is not None else dirname,
                "display_name": display_name,
                "role": role,
                "contributes_to": list(ups),
            }), encoding="utf-8")

    if card_line is not None:
        (root / "design" / "social-card.json").write_text(
            json.dumps({"kicker": "K", "lines": [card_line], "footer": "f"}), encoding="utf-8")

    if manifest:
        (root / "design" / "shared-layer.json").write_text(
            json.dumps({"source": "indy-llm-wiki", "siblings": FEDERATION_MEMBERS,
                        "shared": []}), encoding="utf-8")

    if export is not None:
        (root / "tools" / "export.py").write_text(export, encoding="utf-8")

    if deploy_pages:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "deploy-pages.yml").write_text("on: push\n",
                                                                         encoding="utf-8")
    return root


def fails_with(r, needle):
    return any(needle.lower() in f.lower() for f in r.failures)


def main():
    print("init_wiki — generated once, checked forever\n")

    # ---- THE THREE FAILURES THAT LOOK LIKE SUCCESS ------------------------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", name="llm-wiki-template"))
        check("a wiki still calling itself the template is caught",
              fails_with(r, "directory"),
              "it would contribute as llm-wiki-template, and nothing else would say so")

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "some-commons", role="commons", ups=(), export=SPOKE_EXPORT))
        check("a commons running the SPOKE exporter is caught",
              fails_with(r, "wiki.shared.json"),
              "SETUP.md's not-optional step; its absence leaves a green repo")
        check("and the failure names the file to copy and from where",
              any("cp ../xco-team-wiki/tools/export.py" in f for f in r.failures))

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", display_name="this LLM Wiki"))
        check("an anonymous colleague mirror is caught",
              fails_with(r, "display_name"), "export_shared.py titles the mirror with it")

    # ---- the commons that is set up correctly -----------------------------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "some-commons", role="commons", ups=(), export=COMMONS_EXPORT))
        check("a correctly configured top commons passes", not r.failures,
              "; ".join(r.failures)[:120])
        check("and its empty contributes_to is reported as correct, not missing",
              any("nothing sits above" in m.lower() for m in r.passed))

    # ---- a vacuous pass must be visible ------------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", export=SPOKE_EXPORT))
        check("a SPOKE is not failed for lacking the two-cut export", not r.failures)
        check("and is TOLD that check was skipped for its role",
              any("two-cut" in m for m in r.skipped),
              "a gate that cannot fire must not report a clean pass in silence")

    # ---- the graph ---------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", ups=()))
        check("a spoke with nowhere to contribute is caught", fails_with(r, "nowhere"))

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", ups=("alex-llm-wiki",)))
        check("a wiki contributing to itself is caught", fails_with(r, "itself"))

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", ups=("ghost-wiki",)))
        check("a contribution target no manifest knows is caught", fails_with(r, "ghost-wiki"),
              "contribute.py would open a PR against a repo nothing else knows about")

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", ups=("ghost-wiki",), manifest=False))
        check("with no manifest, targets are reported UNVERIFIED rather than passed",
              not fails_with(r, "ghost-wiki") and any("unverified" in m for m in r.skipped),
              "absent evidence is not evidence of absence")

    # ---- the template is the one repo where placeholders are correct --------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "llm-wiki-template", display_name="this LLM Wiki",
                          card_line="An LLM wiki."))
        check("the template's placeholders are correct, not failures", not r.failures,
              "; ".join(r.failures)[:120])
        check("and its placeholder card is not even an advisory", not r.advisories)

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "llm-wiki-template", display_name="Indy's LLM Wiki"))
        check("a template that has LOST its placeholder is caught",
              fails_with(r, "seeds every wiki"),
              "it would seed nine wikis with one person's name")

    # ---- advisories are surfaced, never fatal ------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "some-commons", role="commons", ups=(), export=COMMONS_EXPORT,
                          deploy_pages=True, card_line="An LLM wiki."))
        check("a commons publishing a site is an advisory, not a failure",
              not r.failures and len(r.advisories) == 2,
              "power-project-wiki was given one by an explicit decision")

    # ---- broken input fails cleanly ----------------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", federation=False))
        check("a wiki with no federation.json fails with a runnable remedy",
              fails_with(r, "init_wiki.py --init"))

    with tempfile.TemporaryDirectory() as t:
        r = iw.check(wiki(t, "alex-llm-wiki", bad_json=True))
        check("invalid JSON is reported, not raised", fails_with(r, "not valid json"))

    # ---- generation --------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t) / "alex-llm-wiki"
        (root / "design").mkdir(parents=True)
        (root / "design" / "shared-layer.json").write_text(
            json.dumps({"source": "indy-llm-wiki", "siblings": FEDERATION_MEMBERS,
                        "shared": []}), encoding="utf-8")

        code, _ = iw.init("alex-llm-wiki", "spoke", "Alex's LLM Wiki",
                          ["xco-team-wiki"], root=root)
        check("--init writes a configuration", code == 0 and
              (root / "design" / "federation.json").exists() and
              (root / "design" / "social-card.json").exists())

        # THE ROUND TRIP: the two halves of this tool must agree with each other.
        r = iw.check(root)
        check("and what it generates passes its own --check", not r.failures,
              "; ".join(r.failures)[:160])

        before = (root / "design" / "federation.json").read_text()
        code, lines = iw.init("alex-llm-wiki", "spoke", "Someone Else", ["xco-team-wiki"],
                              root=root)
        check("a second --init refuses to overwrite",
              (root / "design" / "federation.json").read_text() == before and
              any("not overwritten" in l for l in lines))
        iw.init("alex-llm-wiki", "spoke", "Someone Else", ["xco-team-wiki"],
                force=True, root=root)
        check("--force does overwrite",
              "Someone Else" in (root / "design" / "federation.json").read_text())

    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t) / "w"
        root.mkdir(parents=True)
        code, lines = iw.init("w", "spoke", "W", [], root=root)
        check("--init refuses a spoke with no targets", code == 1)
        check("and writes nothing when it refuses",
              not (root / "design" / "federation.json").exists())

    check("a commons is told to copy the exporter, which the tool will not invent",
          any("export.py" in i for i in iw.human_remainder("commons")))
    check("and a spoke is not told to",
          not any("export.py" in i for i in iw.human_remainder("spoke")))
    check("both are told read access is a separate decision from `visibility:`",
          all(any("visibility" in i for i in iw.human_remainder(role))
              for role in ("spoke", "commons")),
          "the boundary people most reliably confuse")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
