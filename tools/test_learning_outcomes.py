#!/usr/bin/env python3
"""
Properties of learning_outcomes.py.

The one that matters is `the funder cut never names an internal page`: this read-out exists to
be shown to funders, and the first version that leaked an internal title would be the last one
anyone trusted. The second is `the repository's first commit is not learning`: the first real run
claimed 799 pages learned in 100 days, because the repo was created on 2026-07-03 and carried the
whole corpus in at once. Same clock failure staleness.py documents; it must stay caught.

Real git repositories with controlled commit dates, because every date here comes from git.
"""
from __future__ import annotations

import datetime
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import learning_outcomes as lo  # noqa: E402

FAILED = []
DAY = 86400
T0 = 1780000000  # 2026-05-28


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(title, *, type="concept", visibility="internal", body="body\n", tags="[t]", **extra):
    fm = [f"type: {type}", f"title: {title}", "description: d", f"tags: {tags}", "status: draft",
          f"visibility: {visibility}", "confidence: medium", "timestamp: 2026-08-01", "sources: []"]
    fm += [f"{k}: {v}" for k, v in extra.items()]
    return "---\n" + "\n".join(fm) + "\n---\n\n" + body


def day(ts):
    return datetime.date.fromtimestamp(ts)


class Repo:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        (self.root / "wiki").mkdir(parents=True)
        for a in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"],
                  ["config", "user.name", "T"], ["config", "commit.gpgsign", "false"]):
            subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)

    def write(self, slug, text):
        f = self.root / "wiki" / f"{slug}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def commit(self, at, msg="c"):
        stamp = f"{int(at)} +0000"
        env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-q", "-m", msg],
                       check=True, capture_output=True, env=env)

    def activate(self):
        lo.ROOT, lo.WIKI, lo.AXIOMS = self.root, self.root / "wiki", self.root / "wiki" / "axioms.md"


def main():
    print("learning_outcomes — what the corpus learned, never typed\n")

    # THE CASE THIS EXISTS FOR: a funder cut never names an internal or private page.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        r.write("seed", page("Seed", visibility="public"))
        r.commit(T0)                                  # the repo's first commit
        r.write("pub-summary", page("A Public Source", type="summary", visibility="public", tags="[finance, governance]"))
        r.write("int-summary", page("An Internal Source", type="summary", visibility="internal", tags="[finance]"))
        r.write("priv-entity", page("A Private Person", type="entity", visibility="private"))
        r.write("int-entity", page("An Internal Org", type="entity", visibility="internal"))
        r.write("pub-entity", page("A Public Org", type="entity", visibility="public"))
        r.commit(T0 + 20 * DAY)
        r.activate()
        since, until = day(T0 + 10 * DAY), day(T0 + 30 * DAY)
        f = lo.build(since, until, "funder")
        i = lo.build(since, until, "internal")
        text_f = lo.render(f)
        check("the funder cut names no internal page",
              "An Internal Org" not in text_f and "An Internal Source" not in text_f)
        check("...and no private page", "A Private Person" not in text_f)
        check("...but counts them as not shown, rather than pretending they do not exist",
              f["entered"]["not_shown_to_this_audience"] == 3, str(f["entered"]))
        check("the internal cut names internal pages", "An Internal Org" in lo.render(i))
        check("...and still never names a private page", "A Private Person" not in lo.render(i))
        check("fields are read from tags on the sources the audience may see",
              [x["tag"] for x in f["entered"]["fields"]] == ["finance", "governance"]
              and f["entered"]["fields"][0]["sources"] == 1,
              str(f["entered"]["fields"]))
        check("the internal cut counts both sources under finance",
              next(x for x in i["entered"]["fields"] if x["tag"] == "finance")["sources"] == 2)

    # THE SECOND CASE: pages carried in by the repository's first commit are imported, not learned.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        for k in range(5):
            r.write(f"old{k}", page(f"Old {k}", type="summary", visibility="public"))
        r.commit(T0)
        r.write("new", page("New", type="summary", visibility="public"))
        r.commit(T0 + 5 * DAY)
        r.activate()
        v = lo.build(day(T0 - 2 * DAY), day(T0 + 10 * DAY), "internal")
        check("the repo's first commit does not count as learning even inside the window",
              v["entered"]["total"] == 1 and v["entered"]["imported_at_repo_start_not_counted"] == 5,
              str(v["entered"]))
        check("...and the read-out says so", "imported, not learned" in lo.render(v))

    # Movement: a declared contradiction in the window, a closed one, and a moved axiom.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        r.write("a", page("Position A", visibility="internal"))
        r.write("axioms", page("Axioms Register", type="synthesis", visibility="internal",
                               body="## A1 — first\nevidence: assumptive\n\n## A2 — second\nevidence: contested\n"))
        r.commit(T0)
        r.write("b", page("Position B", visibility="internal", contradicts='"Position A"'))
        r.write("a", page("Position A", visibility="internal", superseded_by='"Position B"',
                          timestamp="2026-06-20"))
        r.write("axioms", page("Axioms Register", type="synthesis", visibility="internal",
                               body="## A1 — first\nevidence: evidenced\n\n## A2 — second\nevidence: contested\n\n## A3 — third\nevidence: assumptive\n"))
        r.commit(T0 + 20 * DAY)
        r.activate()
        v = lo.build(day(T0 + 10 * DAY), day(T0 + 30 * DAY), "internal")
        m = v["moved"]
        check("a contradiction declared in the window is counted, both sides named",
              m["contradictions_declared"] == [{"page": "Position B", "with": "Position A"}],
              str(m["contradictions_declared"]))
        check("a position closed by a person in the window is counted as superseded",
              m["positions_closed"] and m["positions_closed"][0]["how"] == "superseded",
              str(m["positions_closed"]))
        check("an axiom whose evidence status changed is reported from -> to",
              {"axiom": "A1", "from": "assumptive", "to": "evidenced"} in m["axioms"], str(m["axioms"]))
        check("a new axiom reads as new, an unchanged one is not reported",
              {"axiom": "A3", "from": None, "to": "assumptive"} in m["axioms"]
              and not any(a["axiom"] == "A2" for a in m["axioms"]), str(m["axioms"]))
        check("a resolved contradiction is not still open", v["still_open"]["contradictions"] == 0)

    # Standing behind: a person's validation and a verification mark, by date; never a model.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        r.write("v", page("Validated", visibility="internal", validation="peer",
                          validated_by="[Robyn Bennett]", validated_at="2026-06-20",
                          body="A claim (raw/x.pdf){✓ Robyn 2026-06-21}. Another (raw/y.pdf){✓ Indy 2026-01-01}.\n"))
        r.write("m", page("Machine", visibility="internal", validation="machine", validated_at="2026-06-20"))
        r.commit(T0)
        r.activate()
        v = lo.build(datetime.date(2026, 6, 1), datetime.date(2026, 6, 30), "internal")
        s = v["stood_behind"]
        check("a human validation dated in the window counts; a machine page does not",
              [x["page"] for x in s["validations"]] == ["Validated"], str(s["validations"]))
        check("verification marks are counted by their own date, not the page's",
              s["claims_verified"] == 1, str(s))

    # name() is the only door a private title has out of this tool. Mutation testing found the
    # first suite never walked through it: every private page it used was an entity, and entities
    # are filtered by visible() before name() is reached. So a name() that ignored visibility
    # failed no test. These do reach it — a private page validated in the window, and a private
    # goal with nothing committed — and the INTERNAL cut must still return None for both.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        r.write("pv", page("A Private Validated Page", visibility="private", validation="self",
                           validated_by="[Indy Johar]", validated_at="2026-06-20"))
        r.write("pg", page("A Private Goal", type="goal", visibility="private"))
        r.write("ig", page("An Internal Goal", type="goal", visibility="internal"))
        r.commit(T0)
        r.activate()
        v = lo.build(datetime.date(2026, 6, 1), datetime.date(2026, 6, 30), "internal")
        check("a private page's validation is counted but its title comes back as None",
              [x["page"] for x in v["stood_behind"]["validations"]] == [None], str(v["stood_behind"]))
        check("a private unbacked goal is counted, not named; an internal one is named",
              v["still_open"]["unbacked_goals_total"] == 2
              and set(v["still_open"]["unbacked_goals"]) == {None, "An Internal Goal"},
              str(v["still_open"]))
        check("...and neither private title appears anywhere in the rendered internal cut",
              "A Private Validated Page" not in lo.render(v) and "A Private Goal" not in lo.render(v))

    # THE BRIEF: the shareable form. A funder's copy names no internal page in any format;
    # Slack's markup has no headings; a zero is a sentence with a meaning, not a "0".
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        r.write("seed", page("Seed", visibility="public"))
        r.commit(T0)
        r.write("pub", page("A Public Source", type="summary", visibility="public", tags="[finance]"))
        r.write("int", page("An Internal Org", type="entity", visibility="internal"))
        r.write("g", page("A Goal Nobody Backed — long subtitle", type="goal", visibility="internal"))
        r.commit(T0 + 20 * DAY)
        r.activate()
        since, until = day(T0 + 10 * DAY), day(T0 + 30 * DAY)
        f = lo.build(since, until, "funder")
        i = lo.build(since, until, "internal")
        for fmt, fn in (("text", lo.render_text), ("markdown", lo.render_markdown),
                        ("slack", lo.render_slack), ("html", lo.render_html)):
            out = fn(f)
            check(f"the funder brief names no internal page — {fmt}",
                  "An Internal Org" not in out and "A Goal Nobody Backed" not in out)
        check("the funder brief still says what it is not naming",
              "not named for this audience" in lo.render_text(f))
        check("the internal brief names the internal goal by its short title, not its subtitle",
              "A Goal Nobody Backed" in lo.render_text(i) and "long subtitle" not in lo.render_text(i))
        sl = lo.render_slack(i)
        check("Slack markup: bold with single asterisks, no markdown heading",
              sl.startswith("*What ") and "###" not in sl and "**" not in sl)
        check("a zero is said as a sentence with a meaning, not as a number",
              "Nobody stood behind a page" in lo.render_text(i) and "0 page" not in lo.render_text(i))
        check("the HTML is a standalone document", lo.render_html(i).startswith("<!doctype html>")
              and "<script" not in lo.render_html(i))
        check("the plural is right", "1 source read" in lo.render_text(i) and "1 organisation, person or place met" in lo.render_text(i))

    # Nothing is typed: the same corpus gives the same read-out.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(t)
        r.write("x", page("X", visibility="public"))
        r.commit(T0)
        r.activate()
        a = lo.render(lo.build(day(T0 - DAY), day(T0 + DAY), "internal"))
        b = lo.render(lo.build(day(T0 - DAY), day(T0 + DAY), "internal"))
        check("the read-out is deterministic for an unchanged corpus", a == b)

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
