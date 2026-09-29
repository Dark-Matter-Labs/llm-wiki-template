#!/usr/bin/env python3
"""
Tests for export.py — run with:  python tools/test_export.py

The load-bearing test is test_private_leaks_nothing: a private page must leave no
trace in the public export — not its title, not its slug, not any link edge.
"""

import json
import os
import tempfile
import unittest

import export


def write(d, name, fm, body="Body text.\n"):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write("---\n" + fm.strip() + "\n---\n\n" + body)


def base_fm(type_, title, visibility, extra=""):
    return (
        f"type: {type_}\n"
        f"title: {title}\n"
        f"description: desc for {title}\n"
        f"tags: [t1, t2]\n"
        f"status: draft\n"
        f"visibility: {visibility}   # public | unlisted | private\n"
        f"confidence: medium\n"
        f"timestamp: 2026-07-10\n"
        f"sources: []\n"
        + (extra + "\n" if extra else "")
    )


class ExportTests(unittest.TestCase):

    def _fixture(self, d):
        # A private page with a deliberately unique, searchable title AND slug so the
        # leak assertions can't be tripped by ordinary vocabulary in other pages.
        PRIV = "Zzq Confidential Node 9f3a"
        write(d, "zzq-priv-9f3a.md", base_fm("concept", PRIV, "private"),
              "Sensitive internal content.\n")
        # A public page that links to the private page (both bare and piped), plus a
        # link to a real public page. The piped display deliberately avoids the slug/title.
        write(d, "alpha.md", base_fm("concept", "Alpha", "public"),
              "See [[%s]] and [[%s|the hidden one]]. Also [[Beta]].\n" % (PRIV, PRIV))
        # An unlisted page (must be included, flagged).
        write(d, "beta.md", base_fm("concept", "Beta", "unlisted"),
              "Beta links back to [[Alpha]].\n")
        # A navigation file with no frontmatter (must be skipped, not error).
        with open(os.path.join(d, "index.md"), "w") as f:
            f.write("# Wiki Index\n- [[Alpha]]\n")
        return PRIV

    def test_private_leaks_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            PRIV = self._fixture(d)
            SLUG = "zzq-priv-9f3a"
            nodes, t2s = export.build_nodes(d)
            public, private_slugs = export.make_public(nodes, t2s)

            self.assertIn(SLUG, private_slugs)
            # 1. private node absent
            self.assertNotIn(SLUG, public)
            # 2. private title / slug absent anywhere in the serialized public export
            blob = json.dumps({"meta": export.build_meta(public, "public"),
                               "nodes": [public[s] for s in sorted(public)]})
            self.assertNotIn(PRIV, blob, "private TITLE leaked into public export")
            self.assertNotIn(SLUG, blob, "private SLUG leaked into public export")
            # 3. no link edge references the private page
            for n in public.values():
                self.assertNotIn(SLUG, n["outbound_links"])
                self.assertNotIn(SLUG, n["inbound_links"])
            # 4. the public page survives, its private link markup neutralized,
            #    its real edge to Beta preserved
            self.assertIn("alpha", public)
            self.assertIn("the hidden one", public["alpha"]["body"])  # piped display kept
            self.assertNotIn("[[Zzq", public["alpha"]["body"])        # no link markup to private survived
            self.assertIn("beta", public["alpha"]["outbound_links"])
            # 5. unlisted page included and flagged
            self.assertIn("beta", public)
            self.assertEqual(public["beta"]["visibility"], "unlisted")

    def _cut(self, d, hide=export.HIDE_FROM_WEB):
        nodes, t2s = export.build_nodes(d)
        public, hidden = export.make_public(nodes, t2s, hide=hide)
        blob = json.dumps({"meta": export.build_meta(public, "public"),
                           "nodes": [public[s] for s in sorted(public)]})
        return public, hidden, blob

    def assertNoTrace(self, blob, title, slug):
        self.assertNotIn(title.casefold(), blob.casefold(), "hidden TITLE leaked")
        self.assertNotIn(slug, blob, "hidden SLUG leaked")

    def test_an_unknown_tier_is_hidden_not_published(self):
        """An allowlist, not a denylist (federation review, 2026-09-29).

        The cut used to hide a page only when its tier was exactly `private` or `internal`,
        so `Private`, `confidential` or a typo published it. --check refuses those values
        before a publish; this holds even when --check is skipped.
        """
        for tier in ("Private", "confidential", "privat", "INTERNAL"):
            with tempfile.TemporaryDirectory() as d:
                write(d, "zzq-odd-9f3a.md", base_fm("concept", "Zzq Odd Tier 9f3a", tier))
                write(d, "alpha.md", base_fm("concept", "Alpha", "public"))
                for hide in (export.HIDE_FROM_WEB, export.HIDE_FROM_SHARED):
                    public, hidden, blob = self._cut(d, hide)
                    self.assertIn("zzq-odd-9f3a", hidden, f"tier {tier!r} was published")
                    self.assertNoTrace(blob, "Zzq Odd Tier 9f3a", "zzq-odd-9f3a")
                    self.assertIn("alpha", public)

    def test_a_crm_page_never_travels_whatever_its_tier(self):
        """contribute.py refused CRM pages; the exporters did not. A crm/ page mislabelled
        `internal` would have reached the colleague mirror."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "crm"))
            write(d, os.path.join("crm", "zzq-contact-9f3a.md"),
                  base_fm("entity", "Zzq Contact 9f3a", "internal"))
            write(d, "alpha.md", base_fm("concept", "Alpha", "public"), "Met [[Zzq Contact 9f3a]].\n")
            public, hidden, blob = self._cut(d, export.HIDE_FROM_SHARED)
            self.assertIn("crm/zzq-contact-9f3a", hidden)
            self.assertNoTrace(blob, "Zzq Contact 9f3a", "zzq-contact-9f3a")

    def test_frontmatter_fields_are_cleaned_too(self):
        """Only the body was cleaned. A public page whose `contradicts`, `commits_to`,
        `superseded_by` or `description` named a private page carried its title out."""
        PRIV = "Zzq Confidential Node 9f3a"
        with tempfile.TemporaryDirectory() as d:
            write(d, "zzq-priv-9f3a.md", base_fm("goal", PRIV, "private"))
            extra = ('contradicts: "%s"\ncommits_to: "%s"\nfrom: "%s"\nparent: "%s"\n'
                     'superseded_by: "%s"\ndevalued_by: "%s"' % ((PRIV,) * 6))
            fm = base_fm("commitment", "Alpha", "public", extra).replace(
                "description: desc for Alpha", "description: builds on [[%s]] and more" % PRIV)
            write(d, "alpha.md", fm)
            public, _hidden, blob = self._cut(d)
            self.assertNoTrace(blob, PRIV, "zzq-priv-9f3a")
            self.assertIsNone(public["alpha"]["contradicts"])
            self.assertIn("and more", public["alpha"]["description"])

    def test_link_variants_are_redacted(self):
        """[[Title#Section]], a case variant and a markdown link each named the hidden page."""
        PRIV = "Zzq Confidential Node 9f3a"
        body = ("One [[%s#Terms]]. Two [[%s#Terms|the terms]]. Three [[%s]]. "
                "Four [notes](zzq-priv-9f3a.md). Five [more](./zzq-priv-9f3a.md#top).\n"
                % (PRIV, PRIV, PRIV.lower()))
        with tempfile.TemporaryDirectory() as d:
            write(d, "zzq-priv-9f3a.md", base_fm("concept", PRIV, "private"))
            write(d, "alpha.md", base_fm("concept", "Alpha", "public"), body)
            public, _hidden, blob = self._cut(d)
            self.assertNoTrace(blob, PRIV, "zzq-priv-9f3a")
            text = public["alpha"]["body"]
            for kept in ("the terms", "notes", "more"):
                self.assertIn(kept, text)

    def test_links_to_visible_pages_are_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "beta.md", base_fm("concept", "Beta", "public"))
            body = "See [[Beta#Why]], [[beta]] and [the page](beta.md).\n"
            write(d, "alpha.md", base_fm("concept", "Alpha", "public", 'contradicts: "Beta"'), body)
            public, _hidden, _blob = self._cut(d)
            self.assertEqual(public["alpha"]["body"], body)
            self.assertEqual(public["alpha"]["contradicts"], "Beta")

    def test_full_export_keeps_everything(self):
        with tempfile.TemporaryDirectory() as d:
            self._fixture(d)
            nodes, _ = export.build_nodes(d)
            self.assertIn("zzq-priv-9f3a", nodes)          # private present in full
            self.assertEqual(nodes["zzq-priv-9f3a"]["visibility"], "private")
            self.assertIn("zzq-priv-9f3a", nodes["alpha"]["outbound_links"])  # edge present in full
            # index.md (no frontmatter) is not a node
            self.assertNotIn("index", nodes)

    def test_lifecycle_fields_reach_the_graph(self):
        """`status` and `derivation` must survive the export, or no reader can see them.

        Both are gated at the file and were dropped here, so the checks passed while every
        reading interface was blind to the answer. `status` was fixed on 2026-09-15 for
        dormancy; a lint pass the same day found `derivation` in the same state, which is
        the field CLAUDE.md calls the layer where drift hides.
        """
        with tempfile.TemporaryDirectory() as d:
            write(d, "derived.md",
                  base_fm("synthesis", "Built from other pages", "internal",
                          "status: dormant\nderivation: derivative"))
            write(d, "plain.md", base_fm("concept", "Nothing declared", "internal"))
            nodes, _ = export.build_nodes(d)
            self.assertEqual(nodes["derived"]["derivation"], "derivative")
            self.assertEqual(nodes["derived"]["status"], "dormant")
            # A page that declares neither must read as absent, never as a default value.
            self.assertIsNone(nodes["plain"]["derivation"])

    def test_check_catches_schema_errors(self):
        with tempfile.TemporaryDirectory() as d:
            # missing visibility + bad type
            write(d, "bad.md",
                  "type: nonsense\ntitle: Bad\ndescription: d\ntags: []\n"
                  "status: draft\nconfidence: low\ntimestamp: 2026-07-10\nsources: []\n")
            errors = export.validate(d)
            msgs = " ".join(m for _, m in errors)
            self.assertIn("visibility", msgs)
            self.assertIn("invalid type", msgs)

    def test_inline_comment_and_quotes_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "q.md",
                  'type: summary\ntitle: "Quoted: Title"\ndescription: d\ntags: [a]\n'
                  "status: draft\nvisibility: private   # trailing comment\n"
                  "confidence: high\ntimestamp: 2026-07-10\nsources: []\n")
            nodes, _ = export.build_nodes(d)
            self.assertEqual(nodes["q"]["visibility"], "private")   # comment stripped
            self.assertEqual(nodes["q"]["title"], "Quoted: Title")  # quotes stripped

    def test_bracket_list_with_trailing_comment(self):
        """`sources: []   # why` must parse as an empty list, not the string "[]".

        The scalar comment-stripper is deliberately not applied to bracket lists, so a
        trailing comment made the value fail the endswith("]") test and fall through to
        the scalar branch. The whole string then became a one-element list, turning an
        EMPTY sources list into the phantom source "[]" -- which check_sources.py duly
        went looking for on disk. Found when contributing a commitment page whose empty
        sources carried a comment explaining why it was empty.
        """
        with tempfile.TemporaryDirectory() as d:
            write(d, "c.md",
                  "type: summary\ntitle: Commented\ndescription: d\ntags: [x]  # a note\n"
                  "status: draft\nvisibility: private\nconfidence: high\n"
                  "timestamp: 2026-07-10\nsources: []   # held in another repo\n")
            nodes, _ = export.build_nodes(d)
            self.assertEqual(nodes["c"]["sources"], [])
            self.assertEqual(nodes["c"]["tags"], ["x"])

    def test_hash_inside_a_bracket_list_survives(self):
        """Only text after the FINAL "]" is treated as a comment."""
        with tempfile.TemporaryDirectory() as d:
            write(d, "h.md",
                  "type: summary\ntitle: Hashy\ndescription: d\ntags: [a]\n"
                  "status: draft\nvisibility: private\nconfidence: high\n"
                  "timestamp: 2026-07-10\nsources: [raw/note#1.pdf, raw/b.pdf]\n")
            nodes, _ = export.build_nodes(d)
            self.assertEqual(nodes["h"]["sources"], ["raw/note#1.pdf", "raw/b.pdf"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
