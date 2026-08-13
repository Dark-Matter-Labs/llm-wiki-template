#!/usr/bin/env python3
"""Gravity instrument for the wiki — measures the corpus's centre of mass and its trajectory.

Model (documented in wiki/repository-gravity.md):
  - Every wiki page body is a TF-IDF vector in the corpus's own term space
    (sublinear TF, IDF from the CURRENT corpus so all snapshots share one lens).
  - Structural mass w_p = 1 + ln(1 + inbound wiki-links to p), links counted
    within the snapshot, index.md/log.md excluded as catalogues.
  - Gravity G(t) = mass-weighted centroid of the page vectors at time t.
  - Trajectory V(t1→t2) = G(t2) − G(t1); its largest +/− components are the
    rising/falling terms — the human-readable direction of motion.
  - An input document d is read against both objects:
      radial    r = cos(v_d, G)                     alignment with the mass
      tangent   τ = cos(v_d − G, V)                 ahead (+) / behind (−) the motion
      novelty   n = 1 − max_p cos(v_d, v_p)         distance to nearest page
  - All outputs are ORDINAL instruments under the Rσ rule: they route attention,
    they never certify. No threshold here is a verdict.

Modes:
  snapshot [--at YYYY-MM-DD]      centroid summary at a date (default: worktree)
  series --dates d1,d2,...        trajectory table across snapshot dates
  eval FILE [FILE...]             read input document(s) against G and V
  weekly                          report: current snapshot + 7-day trajectory

Stdlib only; deterministic; safe to re-run.
"""
import argparse, collections, math, os, re, subprocess, sys, tarfile, tempfile

STOP = set("""a about above after again all also am an and any are as at be because been
before being below between both but by can did do does doing down during each few for from
further had has have having he her here hers him his how i if in into is it its itself just
me more most my no nor not now of off on once only or other our ours out over own same she
should so some such than that the their theirs them then there these they this those through
to too under until up very was we were what when where which while who whom why will with
you your yours would could may might must shall one two three per via vs eg ie etc
pdf html png jpg svg csv raw docs wiki assets http https www com org""".split())

EXCLUDE = {"index.md", "log.md"}

def tokenize(text):
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)  # frontmatter off
    text = text.replace("[[", " ").replace("]]", " ")
    toks = re.findall(r"[a-z][a-z\-]{2,}", text.lower())
    out = []
    for t in toks:
        t = t.strip("-")
        if t in STOP or len(t) <= 2 or t.count("-") >= 3:  # 3+ hyphens = filename slug
            continue
        out.append(t)
    return out

def wiki_files_from_dir(root):
    out = {}
    wiki = os.path.join(root, "wiki")
    for dirpath, _, files in os.walk(wiki):
        # wiki/log/ holds the monthly log files — catalogue prose, not corpus content.
        if os.path.basename(dirpath) == "log" and os.path.dirname(dirpath) == wiki:
            continue
        for f in files:
            if f.endswith(".md") and f not in EXCLUDE:
                p = os.path.join(dirpath, f)
                out[os.path.relpath(p, root)] = open(p, encoding="utf-8", errors="replace").read()
    return out

def snapshot_at(date):
    """Materialise wiki/ at the last commit on or before `date`; return {relpath: text}."""
    if date is None:
        return wiki_files_from_dir(".")
    commit = subprocess.run(["git", "rev-list", "-1", f"--before={date} 23:59", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    if not commit:
        return {}
    with tempfile.TemporaryDirectory() as td:
        ar = subprocess.run(["git", "archive", commit, "wiki/"], capture_output=True, check=True)
        with tarfile.open(fileobj=__import__("io").BytesIO(ar.stdout)) as t:
            t.extractall(td)
        return wiki_files_from_dir(td)

def page_meta(text, fallback):
    m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text, re.M)
    return m.group(1) if m else fallback

# How much a page counts toward the corpus's centre, by who has stood behind it.
# Unvalidated material is admitted, indexed and searchable — it simply does not yet
# move the centre. This is the mechanical form of the failure the owner named: a bulk
# load of well-formed but out-of-date thinking should not drag the whole model
# backwards just because it is voluminous.
#
# These are calibration values, not findings. What matters is the ordering and the
# gap between machine and collective; tune with real use.
VALIDATION_WEIGHT = {"machine": 0.25, "self": 0.6, "peer": 0.85, "collective": 1.0}
DEFAULT_VALIDATION = "machine"

def page_validation(text):
    m = re.search(r"^validation:\s*([a-z]+)\s*$", text, re.M)
    v = m.group(1) if m else DEFAULT_VALIDATION
    return v if v in VALIDATION_WEIGHT else DEFAULT_VALIDATION

def build_space(current_pages):
    """IDF lens from the CURRENT corpus (one lens for all snapshots — a modelling choice)."""
    df = collections.Counter()
    for text in current_pages.values():
        for t in set(tokenize(text)):
            df[t] += 1
    n = len(current_pages)
    return {t: math.log(n / c) for t, c in df.items() if c >= 3}

def vectorize(text, idf):
    tf = collections.Counter(t for t in tokenize(text) if t in idf)
    v = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}
    norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
    return {t: x / norm for t, x in v.items()}

def inbound_mass(pages):
    titles = {f: page_meta(txt, os.path.basename(f)) for f, txt in pages.items()}
    inbound = collections.Counter()
    for f, txt in pages.items():
        for link in re.findall(r"\[\[([^\]|#]+)", txt):
            link = link.strip()
            if link != titles[f]:
                inbound[link] += 1
    # Two multipliers: how connected a page is, and how far anyone has stood behind
    # it. Link mass alone lets volume win; validation is the counterweight.
    return ({f: (1 + math.log(1 + inbound[titles[f]]))
                * VALIDATION_WEIGHT[page_validation(pages[f])]
             for f in pages}, inbound)

def cos(a, b):
    if len(b) < len(a):
        a, b = b, a
    s = sum(x * b.get(t, 0.0) for t, x in a.items())
    na = math.sqrt(sum(x * x for x in a.values())) or 1.0
    nb = math.sqrt(sum(x * x for x in b.values())) or 1.0
    return s / (na * nb)

def sub(a, b):
    out = dict(a)
    for t, x in b.items():
        out[t] = out.get(t, 0.0) - x
    return out

def centroid(pages, idf):
    w, _ = inbound_mass(pages)
    G, W = collections.defaultdict(float), 0.0
    vecs = {}
    for f, txt in pages.items():
        v = vectorize(txt, idf)
        vecs[f] = v
        for t, x in v.items():
            G[t] += w[f] * x
        W += w[f]
    G = {t: x / W for t, x in G.items()}
    disp = sum(w[f] * (1 - cos(v, G)) for f, v in vecs.items()) / W
    return dict(G), vecs, disp

def top_terms(vec, k=12, reverse=True):
    items = sorted(vec.items(), key=lambda kv: kv[1], reverse=reverse)[:k]
    return ", ".join(t for t, _ in items)

def fmt_snapshot(date, pages, G, disp):
    return (f"[{date or 'now'}] pages={len(pages)} dispersion={disp:.3f} "
            f"| core terms: {top_terms(G)}")

def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="mode", required=True)
    s1 = sp.add_parser("snapshot"); s1.add_argument("--at")
    s2 = sp.add_parser("series"); s2.add_argument("--dates", required=True)
    s3 = sp.add_parser("eval"); s3.add_argument("files", nargs="+"); s3.add_argument("--window", type=int, default=7)
    sp.add_parser("weekly")
    args = ap.parse_args()

    current = wiki_files_from_dir(".")
    idf = build_space(current)

    if args.mode == "snapshot":
        pages = snapshot_at(args.at)
        G, _, disp = centroid(pages, idf)
        print(fmt_snapshot(args.at, pages, G, disp))
        return

    if args.mode == "series":
        dates = args.dates.split(",")
        Gs = {}
        for d in dates:
            pages = snapshot_at(d)
            if not pages:
                print(f"[{d}] no commits yet"); continue
            G, _, disp = centroid(pages, idf)
            Gs[d] = G
            print(fmt_snapshot(d, pages, G, disp))
        ds = [d for d in dates if d in Gs]
        print("\nTrajectory legs:")
        prevV = None
        for a, b in zip(ds, ds[1:]):
            V = sub(Gs[b], Gs[a])
            mag = math.sqrt(sum(x * x for x in V.values()))
            persist = f" persistence(cos vs prev leg)={cos(V, prevV):+.2f}" if prevV else ""
            print(f"  {a} → {b}: |V|={mag:.4f}{persist}")
            print(f"    rising:  {top_terms(V, 10)}")
            print(f"    falling: {top_terms(V, 10, reverse=False)}")
            prevV = V
        return

    # eval and weekly both need current G and a trailing V
    from datetime import date as _date, timedelta
    today = subprocess.run(["git", "log", "-1", "--pretty=%ad", "--date=short"],
                           capture_output=True, text=True).stdout.strip() or str(_date.today())
    win = getattr(args, "window", 7)
    y, m, dd = map(int, today.split("-"))
    past = str(_date(y, m, dd) - timedelta(days=win))
    G_now, vecs, disp_now = centroid(current, idf)
    past_pages = snapshot_at(past)
    G_past, _, disp_past = centroid(past_pages, idf) if past_pages else (None, None, None)
    V = sub(G_now, G_past) if G_past else {}

    if args.mode == "eval":
        for f in args.files:
            v = vectorize(open(f, encoding="utf-8", errors="replace").read(), idf)
            r = cos(v, G_now)
            offset = sub(v, G_now)
            tau = cos(offset, V) if V else float("nan")
            near = sorted(((cos(v, pv), pf) for pf, pv in vecs.items()), reverse=True)[:4]
            nov = 1 - near[0][0]
            print(f"\n== {f}")
            print(f"  radial (cos to mass)      r = {r:+.3f}")
            print(f"  tangential (cos offset,V) τ = {tau:+.3f}   (+ahead of motion / −behind / ~0 orthogonal)")
            print(f"  novelty (1−nearest page)  n = {nov:.3f}")
            print(f"  nearest pages: " + "; ".join(f"{p} ({c:.2f})" for c, p in near))
            print(f"  its pull (top offset terms): {top_terms(offset, 8)}")
        return

    if args.mode == "weekly":
        print(f"GRAVITY WEEKLY — as of {today}, window {past} → {today}")
        print(fmt_snapshot(today, current, G_now, disp_now))
        if G_past:
            print(fmt_snapshot(past, past_pages, G_past, disp_past))
            mag = math.sqrt(sum(x * x for x in V.values()))
            print(f"\ncentroid displacement |V| = {mag:.4f} over {win}d "
                  f"(dispersion Δ = {disp_now - disp_past:+.4f}: + spreading / − tightening)")
            print(f"rising terms:  {top_terms(V, 12)}")
            print(f"falling terms: {top_terms(V, 12, reverse=False)}")
            print("\nPages most ahead of the motion (cos(offset, V)):")
            scored = sorted(((cos(sub(v, G_now), V), f) for f, v in vecs.items()), reverse=True)
            for t, f in scored[:6]:
                print(f"  {t:+.3f}  {f}")
            print("Pages most behind the motion (drag / prior-mass anchors):")
            for t, f in scored[-6:]:
                print(f"  {t:+.3f}  {f}")
        print("\nRσ note: ordinal instrument — routes attention, certifies nothing.")

if __name__ == "__main__":
    main()
