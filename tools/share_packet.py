#!/usr/bin/env python3
"""
share_packet.py — share a page with one person when you cannot reach their wiki, and receive one.

    python3 tools/share_packet.py PACKET_FILE            # receive a packet into this wiki
    pbpaste | python3 tools/share_packet.py -            # or from what was pasted
    python3 tools/share_packet.py PACKET_FILE --update   # replace a page received before

Asked for by Gurden on 6 November 2026. Sharing a page with one person used to need permission to
change their wiki, which most people do not have. Now the sender's tool writes a packet, a block
of plain text (`contribute.py --to-person NAME --packet`). They send it however they like, a Slack
message or an attached file. The recipient pastes it into Claude in their own wiki and says
"receive this". The page then arrives as their own proposed change, so their yes saves it.

What receiving checks, so the person does not have to:

  * the packet is addressed to this wiki, or to its owner;
  * each page arrived exactly as sent (a fingerprint of its text travels with it);
  * no hidden text or instructions addressed to a model (the same scan as for sources);
  * the page lands `private`, whatever it says, and never overwrites a page without --update;
  * links to pages this wiki does not have become plain words.

A team wiki does not receive packets: a commons takes pages through proposals a second person
approves (`contribute.py --to`).
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export        # noqa: E402
import source_scan   # noqa: E402

START, END = "===== WIKI SHARE PACKET v1 =====", "===== END PACKET ====="
PAGE_END = "----- END PAGE -----"
PAGE_RE = re.compile(r"^----- PAGE (\S+) sha256 ([0-9a-f]{64}) -----\n(.*?)\n" + re.escape(PAGE_END) + r"$",
                     re.M | re.S)
PATH_RE = re.compile(r"^wiki/[a-z0-9][a-z0-9-]{0,120}\.md$")
LINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\\?\|([^\]]+))?\]\]")
HOW_TO = ('To receive it: paste this whole block into Claude, in your own wiki, and say "receive this".\n'
          "It arrives as a private page, in a proposed change you can say no to.")


def normalise(text):
    """Chat apps trim trailing spaces and blank lines, so the fingerprint ignores both."""
    return "\n".join(line.rstrip() for line in text.strip("\n").split("\n"))


def digest(text):
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def make(bundle, sender, origin, to, today=None):
    """The packet text for a staged bundle ({rel: text})."""
    today = today or datetime.date.today().isoformat()
    out = [START, f"from: {sender} ({origin})", f"to: {to}", f"shared_on: {today}", HOW_TO, ""]
    for rel, text in bundle.items():
        if PAGE_END in text or END in text or START in text:
            raise ValueError(f"{rel}: the page contains a packet marker line; it cannot travel as a packet")
        out += [f"----- PAGE {rel} sha256 {digest(text)} -----", normalise(text), PAGE_END]
    return "\n".join(out + [END]) + "\n"


def parse(text):
    """{from, to, shared_on, pages: [(rel, sha, text)]} from a pasted packet, or raise ValueError."""
    text = normalise(text.replace("\r\n", "\n"))   # chat apps add or trim trailing spaces
    a, b = text.find(START), text.find(END)
    if a < 0 or b < a:
        raise ValueError("this is not a whole share packet: its first or last line is missing. "
                         "Ask the sender for the file itself")
    body = text[a + len(START):b]
    head = dict(re.findall(r"^(from|to|shared_on): (.+?)\s*$", body.split("----- PAGE", 1)[0], re.M))
    if not {"from", "to"} <= head.keys():
        raise ValueError("the packet does not say who sent it and who it is for")
    pages = [(m.group(1), m.group(2), m.group(3)) for m in PAGE_RE.finditer(body)]
    if not pages or len(pages) != body.count("----- PAGE "):
        raise ValueError("a page in the packet is cut short. Ask the sender for the file itself")
    return dict(head, pages=pages)


def delink(text, titles):
    """[[X]] stays a link only where this wiki has a page titled X; otherwise plain words."""
    def sub(m):
        target = export._norm_title(m.group(1))
        return m.group(0) if target in titles else (m.group(2) or target).strip()
    return LINK_RE.sub(sub, text)


def make_private(text):
    head, sep, rest = text[3:].partition("\n---")
    if not text.startswith("---") or not sep:
        raise ValueError("the page has no details block (frontmatter)")
    lines = [ln for ln in head.split("\n") if not ln.startswith("visibility:")]
    return "---" + "\n".join(lines + ["visibility: private"]) + sep + rest


def receive(text, wiki_dir, fed, update=False):
    """Check every page, then write them all. Returns [(path, title)]; raises ValueError."""
    packet = parse(text)
    if fed.get("role", "spoke") != "spoke":
        raise ValueError(f"{fed.get('name')} is a team wiki. It takes pages through proposals, not packets")
    me = {str(fed.get("name", "")).casefold(), str(fed.get("owner") or "").casefold()} - {""}
    if packet["to"].casefold() not in me:
        raise ValueError(f"this packet is for {packet['to']}, not this wiki ({fed.get('name')})")
    _nodes, title_to_slug = export.build_nodes(wiki_dir)
    titles = {export._norm_title(t) for t in title_to_slug}
    ready = []
    for rel, sha, page in packet["pages"]:
        if not PATH_RE.match(rel):
            raise ValueError(f"{rel}: not a plain page name; nothing received")
        if digest(page) != sha:
            raise ValueError(f"{rel}: the page changed on the way, probably in the chat app. "
                             f"Ask the sender to attach the file instead; nothing received")
        found = source_scan.scan_text(page, rel)
        if found:
            kinds = ", ".join(sorted({f["kind"] for f in found}))
            raise ValueError(f"{rel}: the scan found {kinds}. Read it with the sender before going on; "
                             f"nothing received")
        fm, _body = export.split_frontmatter(page)
        title = (fm or {}).get("title")
        if not isinstance(title, str) or not title:
            raise ValueError(f"{rel}: the page has no title; nothing received")
        dest = os.path.join(wiki_dir, os.path.basename(rel))
        same = title_to_slug.get(title)
        if same and same != os.path.basename(rel)[:-3]:
            raise ValueError(f"{rel}: this wiki already has a page called {title!r} ({same}.md); nothing received")
        if os.path.exists(dest) and not update:
            raise ValueError(f"{rel}: this wiki already has {os.path.basename(rel)}. "
                             f"Run again with --update to replace it; nothing received")
        ready.append((dest, title, make_private(normalise(page))))   # checked before anything is written
    titles |= {t for _d, t, _p in ready}   # pages in one packet may link to each other
    for dest, _title, page in ready:
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(delink(page, titles) + "\n")
    log(wiki_dir, packet, [t for _d, t, _p in ready])
    return [(d, t) for d, t, _p in ready]


def log(wiki_dir, packet, titles):
    today = datetime.date.today().isoformat()
    path = os.path.join(wiki_dir, "log", f"{today}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Log — {today}\n\nAppend-only record for {today}. Newest entries at the bottom. "
                     f"Month index: [`{today[:7]}.md`]({today[:7]}.md) · format: [`wiki/log.md`](../log.md).\n")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"\n## [{today}] contribute | received {', '.join(titles)} from {packet['from']}\n\n"
                 f"Shared on {packet.get('shared_on', 'an unstated date')}. Arrived private.\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Receive a share packet into this wiki.")
    ap.add_argument("packet", help="the packet file, or - to read what was pasted")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--update", action="store_true", help="replace a page received before")
    a = ap.parse_args(argv)
    try:
        text = sys.stdin.read() if a.packet == "-" else open(a.packet, encoding="utf-8").read()
        with open(os.path.join("design", "federation.json"), encoding="utf-8") as fh:
            fed = json.load(fh)
        done = receive(text, a.wiki, fed, a.update)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for dest, title in done:
        print(f"  received {dest}  ({title}), private")
    print("  Next: add its index row, run tools/sync_log_index.py, and propose the change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
