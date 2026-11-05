#!/usr/bin/env python3
"""
test_contribute.py — prove the flow up to the commons cannot leak, and cannot lie.

Two classes of failure this guards:

  * **Leaking** — a private page, a CRM page, a private page's *title* hidden in a YAML
    comment, or a link to one, crossing into a wider group.
  * **Lying** — provenance that was invented rather than stamped, or a validation level
    carried across a group boundary so the commons inherits a consensus it was never
    party to.

Usage:  python3 tools/test_contribute.py
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contribute as C  # noqa: E402


PAGE = """---
type: concept
title: {title}
description: {desc}
tags: [t]
status: draft
visibility: {vis}
confidence: medium
validation: {val}
timestamp: 2026-08-12
sources: []
{extra}---

{body}
"""


def write(root, slug, title, vis="internal", val="machine",
          desc="A description.", body="Body text.", extra=""):
    path = os.path.join(root, slug + ".md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PAGE.format(title=title, desc=desc, vis=vis, val=val,
                             extra=extra, body=body))


def check_topology(check):
    """The second commons.

    A spoke may now contribute to more than one, and the tool must refuse to pick.
    Contributing to the wrong commons publishes to the wrong audience, and the remedy
    afterwards is a deletion request, not a revert.
    """
    import os as _os
    import contribute as c

    one = {"role": "spoke", "contributes_to": ["xco-team-wiki"]}
    two = {"role": "spoke", "contributes_to": ["xco-team-wiki", "learning-system-wiki"]}
    none_ = {"role": "commons", "contributes_to": []}

    name, err = c.resolve_commons(None, one)
    check("one declared target resolves without --to",
          name == "xco-team-wiki" and not err, f"got {name!r} / {err!r}")

    name, err = c.resolve_commons(None, two)
    check("two targets REFUSE to be guessed",
          name is None and bool(err) and "--to" in (err or ""), f"got {name!r}")

    name, err = c.resolve_commons("learning-system-wiki", two)
    check("an explicit --to resolves",
          name == "learning-system-wiki" and not err, f"got {name!r} / {err!r}")

    name, err = c.resolve_commons("some-other-wiki", two)
    check("a target that is not declared is refused",
          name is None and bool(err), f"got {name!r}")

    name, err = c.resolve_commons(None, none_)
    check("a commons that contributes nowhere is refused",
          name is None and bool(err), "a top-level commons has nothing above it")

    # The cache lookup must still find the legacy flat path, or every existing spoke
    # silently loses its collision check the day it declares a topology.
    paths = c.commons_cache_paths("xco-team-wiki")
    check("per-commons cache path is preferred",
          paths[0].endswith(_os.path.join("xco-team-wiki", "export", "wiki.shared.json")),
          paths[0])
    check("legacy flat cache path is still a fallback",
          _os.path.join(".commons", "export", "wiki.shared.json") in paths, str(paths))


def check_who_will_see(check):
    """The owner sees who will read a page, what it covers and who it names, before it leaves.

    Added 2026-11-02 (Michelle's point on the d.INO call): people must know where their words
    travel. The block is built from the sanitised bundle, so a private title cannot reach it.
    """
    import contextlib
    import io
    tmp = tempfile.mkdtemp()
    wiki = os.path.join(tmp, "wiki")
    try:
        write(wiki, "secret", "The Secret Position", vis="private")
        write(wiki, "crm/contacts/jane-roe", "Jane Roe (contact)", vis="private")
        write(wiki, "crm/contacts/richard-doe", "Richard Doe (contact)", vis="private")
        write(wiki, "share-me", "A Page To Share", vis="internal",
              body="## What we found\n\nJane Roe said so. See [[The Secret Position]].\n\n"
                   "## What is open\n\nMore later.")
        bundle = C.build_bundle(wiki, ["share-me"], "tester", "abc1234")

        block = C.who_will_see("xco-team-wiki", bundle, wiki,
                               lookup=lambda _c: (["alice", "bob"], "none"))
        check("the readers are listed by login", "2 people with access: alice, bob" in block, block)
        check("the base permission is said plainly", "base permission is none" in block, block)
        check("the topics are the page's own headings",
              "What we found; What is open" in block, block)
        check("a person the page names is shown", "Jane Roe" in block, block)
        check("a contact the page does not name is never shown", "Richard Doe" not in block, block)
        check("a private page's title never reaches the block",
              "The Secret Position" not in block, block)

        unknown = C.who_will_see("xco-team-wiki", bundle, wiki, lookup=lambda _c: (None, None))
        check("an unreadable reader list says so, and never says nobody",
              "could not be read" in unknown and "0 people" not in unknown, unknown)

        old_cwd, old_readers = os.getcwd(), C.readers
        try:
            os.chdir(tmp)
            C.readers = lambda _c: (None, None)
            to = (C.topology().get("contributes_to") or ["xco-team-wiki"])[0]
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = C.main(["share-me", "--by", "tester", "--to", to])
            check("without --readers-confirmed nothing is staged",
                  rc == 1 and not os.path.exists(os.path.join(tmp, "contrib")), f"rc={rc}")
            check("the refusal names the flag", "--readers-confirmed" in err.getvalue(),
                  err.getvalue())
            check("the block is shown before the refusal", "WHO WILL SEE IT" in out.getvalue(),
                  out.getvalue()[:200])
        finally:
            C.readers = old_readers
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_share_with_person(check):
    """Sharing one page with one person, without the team commons (added 2026-11-03).

    Asked for on the 2 November d.INO call: a call between two people had no way to reach
    only the other one. The page goes to a person's own wiki, private, and only to someone
    the page itself names in `shared_with:`.
    """
    feds = {"michelle-llm-wiki": {"role": "spoke", "owner": "MiZuGH"},
            "gurden-llm-wiki": {"role": "spoke", "owner": "gurdenbatra"},
            "xco-team-wiki": {"role": "commons"}}
    fetch, listing = feds.get, lambda: ["michelle-llm-wiki", "gurden-llm-wiki"]

    wiki, owner, err = C.resolve_person("mizugh", fetch, listing)
    check("a GitHub login resolves to that person's own wiki",
          (wiki, owner, err) == ("michelle-llm-wiki", "MiZuGH", None), f"{wiki} {owner} {err}")
    check("a wiki's name resolves to itself",
          C.resolve_person("michelle-llm-wiki", fetch, listing)[0] == "michelle-llm-wiki")
    _w, _o, err = C.resolve_person("xco-team-wiki", fetch, listing)
    check("a team wiki is refused as a person", err and "--to xco-team-wiki" in err, str(err))
    _w, _o, err = C.resolve_person("nobody-here", fetch, listing)
    check("an unknown login is refused, never guessed", err and "no personal wiki" in err, str(err))

    tmp = tempfile.mkdtemp()
    wiki_dir = os.path.join(tmp, "wiki")
    try:
        write(wiki_dir, "secret", "The Secret Position", vis="private")
        write(wiki_dir, "our-call", "Our Call, 2 November", vis="private",
              extra="shared_with: [michelle-llm-wiki]\n",
              body="We agreed things. See [[The Secret Position]].")
        write(wiki_dir, "not-for-her", "Not For Her", vis="private",
              extra="shared_with: [gurden-llm-wiki]\n")
        write(wiki_dir, "crm/contacts/x", "X (contact)", vis="private",
              extra="shared_with: [michelle-llm-wiki]\n")
        to_her = {"wiki": "michelle-llm-wiki", "owner": "MiZuGH"}

        b = C.build_bundle(wiki_dir, ["our-call"], "tester", "abc1234", person=to_her)
        text = next(iter(b.values()))
        fm = text.split("---")[1]
        check("a private page named in shared_with is staged for that person", len(b) == 1)
        check("it arrives private in the recipient's wiki", "visibility: private" in fm, fm)
        check("provenance says who shared it, from where and when",
              "shared_by: tester" in fm and "from_wiki:" in fm and "shared_on:" in fm, fm)
        check("another private page's title never travels with it",
              "The Secret Position" not in text, text)
        check("the shared_with list itself stays at home", "shared_with" not in text, fm)

        for slug, why in (("not-for-her", "shared_with does not name"), ("crm/contacts/x", "CRM")):
            try:
                C.build_bundle(wiki_dir, [slug], "tester", "abc1234", person=to_her)
                ok, msg = False, "no error raised"
            except ValueError as e:
                ok, msg = why in str(e), str(e)
            check(f"refused: {slug}", ok, msg)

        block = C.who_will_see("michelle-llm-wiki", b, wiki_dir,
                               lookup=lambda _c: (["MiZuGH"], "none"), person=True)
        check("the readers block names the recipient's readers and says it stays private",
              "1 people with access: MiZuGH" in block and "arrives `private`" in block, block)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    failures = []

    def check(name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    wiki = os.path.join(tmp, "wiki")
    os.makedirs(wiki)
    try:
        write(wiki, "secret", "The Secret Position", vis="private")
        write(wiki, "shareable", "A Shareable Concept", vis="internal",
              body="Refers to [[The Secret Position]] and to [[Another Shared]].")
        write(wiki, "another-shared", "Another Shared", vis="internal")
        write(wiki, "crm/contact-x", "Contact X", vis="private")
        write(wiki, "peer-page", "A Peer Validated Page", vis="internal", val="peer",
              extra="validated_by: [Indy]\nvalidated_at: 2026-09-01\n")
        write(wiki, "coll-page", "A Collectively Validated Page", vis="internal", val="collective",
              extra="validated_by: [Indy]\nvalidated_at: 2026-09-01\n")
        write(wiki, "self-page", "A Self Validated Page", vis="internal", val="self",
              extra="validated_by: [Indy]\nvalidated_at: 2026-09-01\n")
        write(wiki, "self-unnamed", "Self With Nobody Named", vis="internal", val="self")
        write(wiki, "odd-tier", "An Odd Tier Page", vis="Private")
        # a private title hidden in a YAML comment — the reason frontmatter is rebuilt
        write(wiki, "sneaky", "Sneaky", vis="internal",
              extra="# see also: The Secret Position\n")

        def build(slugs):
            return C.build_bundle(wiki, slugs, "tester", "abc1234")

        # --- refusals -------------------------------------------------------
        try:
            build(["secret"]); ok = False; why = "no error raised"
        except ValueError as e:
            ok, why = "private" in str(e), str(e)
        check("a private page is refused", ok, why)

        try:
            build(["crm/contact-x"]); ok = False; why = "no error raised"
        except ValueError as e:
            ok, why = "CRM" in str(e), str(e)
        check("a CRM page is refused", ok, why)

        # --- the happy path --------------------------------------------------
        b = build(["shareable"])
        text = b["wiki/a-shareable-concept.md"]
        check("an internal page is staged", "wiki/a-shareable-concept.md" in b)

        # --- leaking ---------------------------------------------------------
        check("the private page's title never appears",
              "The Secret Position" not in text,
              text.split("\n\n")[1][:90] if "\n\n" in text else "")
        check("the link to the private page is redacted",
              "[[The Secret Position]]" not in text)
        check("the link to a shared page survives",
              "[[Another Shared]]" in text)

        sneaky = build(["sneaky"])["wiki/sneaky.md"]
        check("a private title hidden in a YAML comment is dropped",
              "The Secret Position" not in sneaky,
              "frontmatter is rebuilt from a whitelist, never copied")

        # --- lying -----------------------------------------------------------
        # Assert against the DERIVED origin, not a literal: origin now comes from the
        # git remote, so a hardcoded name only passes in the one repo it was written in.
        check("provenance is stamped",
              "contributed_by: tester" in text and f"origin: {C.ORIGIN}" in text
              and "origin_rev: abc1234" in text,
              f"origin resolved to {C.ORIGIN!r}")

        def val_of(slug, page_slug=None):
            t = next(iter(build([slug]).values()))
            for line in t.split("\n"):
                if line.startswith("validation:"):
                    return line.split(":", 1)[1].strip()
            return None

        check("peer is re-based to self (the commons must re-earn it)",
              val_of("peer-page") == "self", f"got {val_of('peer-page')}")
        check("collective is re-based to self",
              val_of("coll-page") == "self", f"got {val_of('coll-page')}")
        check("self travels unchanged (the author still stands behind it)",
              val_of("self-page") == "self", f"got {val_of('self-page')}")
        self_text = build(["self-page"])["wiki/a-self-validated-page.md"]
        check("a validated page carries who stood behind it, so the commons schema accepts it",
              "validated_by: [Indy]" in self_text and "validated_at: 2026-09-01" in self_text,
              self_text.split("---")[1][-160:])
        check("self with nobody named is re-based to machine, never passed on unbacked",
              val_of("self-unnamed") == "machine", f"got {val_of('self-unnamed')}")
        try:
            build(["odd-tier"]); ok = False; why = "no error raised"
        except ValueError as e:
            ok, why = True, str(e)
        check("a page whose tier is not a known one is refused", ok, why)
        bad = [b for b in ("tester\nvisibility: public", "Gurden\n", "A---", "A--B", "-x", "", "x" * 81, "a: b") if C.valid_by(b)]
        check("--by is refused when it could rewrite the frontmatter", not bad, f"accepted {bad!r}")
        check("--by accepts an ordinary name", C.valid_by("Gurden Batra") and C.valid_by("gurden") and C.valid_by("Jean-Luc O'Neil"))
        check("machine stays machine",
              val_of("another-shared") == "machine", f"got {val_of('another-shared')}")

        # --- the shared filename comes from the title (Fang's rule, extended) ----
        write(wiki, "call-with-jane-roe-2026-10-06", "Oceans tooling call, 6 October 2026",
              vis="internal")
        named = build(["call-with-jane-roe-2026-10-06"])
        check("a shared file is named from the title, not the spoke's filename",
              list(named) == ["wiki/oceans-tooling-call-6-october-2026.md"], f"got {list(named)}")
        check("nothing of the spoke's filename travels in the bundle",
              not any("jane" in k.lower() or "jane" in v.lower() for k, v in named.items()))
        kept = C.build_bundle(wiki, ["shareable"], "tester", "abc1234",
                              {C.title_key("A Shareable Concept"): "shareable-in-commons"})
        check("a page the commons holds keeps the commons' filename, so --update replaces it",
              list(kept) == ["wiki/shareable-in-commons.md"], f"got {list(kept)}")
        write(wiki, "twin", "A shareable concept!", vis="internal")
        try:
            build(["shareable", "twin"]); ok = False; why = "no error raised"
        except ValueError as e:
            ok, why = "same filename" in str(e), str(e)
        check("two pages whose titles make one filename are refused", ok, why)
        check("accents survive as plain letters",
              C.shared_name("Café Zürich, 2026") == "cafe-zurich-2026", C.shared_name("Café Zürich, 2026"))

        # --- collision with the commons ---------------------------------------
        # 577 of 595 contributable pages already existed in the commons when this was
        # found by rehearsing the loop. A silent overwrite would lose whatever the
        # commons had done to its copy — the two-canons failure, at the moment of
        # contribution, invisible in the staged bundle.
        import json as _json
        cache_dir = os.path.join(tmp, ".commons", "export")
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "wiki.shared.json"), "w", encoding="utf-8") as fh:
            _json.dump({"nodes": [{"title": "A Shareable Concept"}]}, fh)
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp)
            _t, hits = C.check_collisions("wiki", {"shareable"}, "xco-team-wiki")
            check("a page already in the commons is detected as a collision",
                  len(hits) == 1 and hits[0][0] == "shareable", f"hits={hits}")
            _t2, hits2 = C.check_collisions("wiki", {"another-shared"}, "xco-team-wiki")
            check("a page the commons does not have is not a collision",
                  hits2 == [], f"hits={hits2}")
        finally:
            os.chdir(old_cwd)

        # with no cache, it must say it cannot check rather than imply all-clear
        old_cwd = os.getcwd()
        try:
            os.chdir(tempfile.mkdtemp())
            os.makedirs("wiki", exist_ok=True)
            t3, hits3 = C.check_collisions("wiki", set(), "xco-team-wiki")
            check("with no commons cache it reports unknown, not clear",
                  t3 is None, f"titles={t3}")
        finally:
            os.chdir(old_cwd)

        # --- nothing escapes on its own --------------------------------------
        check("build_bundle writes nothing to disk by itself",
              not os.path.exists(os.path.join(tmp, "contrib")),
              "staging is the caller's explicit step")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    check_topology(check)
    check_who_will_see(check)
    check_share_with_person(check)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("All contribute checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
