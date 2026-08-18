#!/usr/bin/env python3
"""
build_tokens.py — generate docs/assets/xco-tokens.css from design/xco.tokens.json.

The JSON is the source of truth. The CSS is derived and must never be hand-edited;
`--check` fails if the committed CSS has drifted from the JSON, so CI catches an
edit to the wrong file.

The register model
------------------
Register and theme are two axes and were being conflated by both predecessors.

  register  AUTHORED     paper | inverse — a section-level rhetorical choice
  theme     ENVIRONMENTAL light | dark   — the reader's preference

`inverse` means maximal contrast against the CURRENT ground, not a fixed dark
colour. So in a light theme it is a dark band in a light document; in a dark theme
it is a light band in a dark one. The rhetorical move survives either way, which is
what "inverse is not a dark-mode proxy" was protecting — while the reader still
gets the theme they asked for.

In CSS that falls out as a swap: the theme decides which value set `:root` carries,
and `[data-register="inverse"]` always carries the other one.

Usage:
  python3 tools/build_tokens.py            # write the CSS
  python3 tools/build_tokens.py --check    # exit 1 if the CSS is out of date
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "design", "xco.tokens.json")
OUT = os.path.join(HERE, "..", "docs", "assets", "xco-tokens.css")

ALIAS = re.compile(r"^\{([a-zA-Z0-9_.]+)\}$")


def load():
    with open(SRC, encoding="utf-8") as fh:
        return json.load(fh)


def walk(node, path=()):
    """Yield (path, value) for every token, skipping $-metadata."""
    if isinstance(node, dict):
        if "$value" in node:
            yield path, node["$value"]
            return
        for k, v in node.items():
            if k.startswith("$"):
                continue
            yield from walk(v, path + (k,))


def resolve(value, index, seen=()):
    """Follow {dotted.path} aliases to a literal."""
    if isinstance(value, list):
        return ", ".join(f'"{v}"' if " " in v else v for v in value)
    if not isinstance(value, str):
        return str(value)
    m = ALIAS.match(value.strip())
    if not m:
        return value
    target = m.group(1)
    if target in seen:
        raise ValueError(f"circular alias: {' -> '.join(seen)} -> {target}")
    if target not in index:
        raise ValueError(f"alias points at nothing: {{{target}}}")
    return resolve(index[target], index, seen + (target,))


def build_index(doc):
    return {".".join(p): v for p, v in walk(doc)}


def css_name(path):
    """primitive.color.paper.050 -> --paper-050 ; semantic.meaning.risk -> --meaning-risk"""
    parts = list(path)
    if parts[0] in ("primitive", "semantic", "component", "register"):
        parts = parts[1:]
    if parts and parts[0] == "color":
        parts = parts[1:]
    return "--" + "-".join(parts)


def emit_block(doc, index, prefix, skip=()):
    """CSS declarations for every token under `prefix`."""
    lines = []
    for path, raw in walk(doc):
        dotted = ".".join(path)
        if not dotted.startswith(prefix):
            continue
        if any(dotted.startswith(s) for s in skip):
            continue
        rel = path[len(prefix.split(".")):] if prefix else path
        lines.append((css_name(path if not prefix else ("x",) + rel),
                      resolve(raw, index)))
    return lines


def render():
    doc = load()
    index = build_index(doc)
    meta = doc["$extensions"]["org.xco"]

    def decls(prefix, rename=None):
        out = []
        for path, raw in walk(doc):
            dotted = ".".join(path)
            if not dotted.startswith(prefix + "."):
                continue
            tail = path[len(prefix.split(".")):]
            name = "--" + "-".join(t for t in tail if t != "color")
            if rename:
                name = rename(name)
            out.append((name, resolve(raw, index)))
        return out

    # --- the two value sets the theme swaps between -------------------------
    paper = (decls("semantic.surface", lambda n: n.replace("--", "--surface-", 1))
             + decls("semantic.text",   lambda n: n.replace("--", "--text-", 1))
             + decls("semantic.border", lambda n: n.replace("--", "--border-", 1))
             + decls("semantic.meaning", lambda n: n.replace("--", "--meaning-", 1))
             + decls("semantic.tint",    lambda n: n.replace("--", "--tint-", 1)))
    inverse = (decls("register.inverse.surface", lambda n: n.replace("--", "--surface-", 1))
               + decls("register.inverse.text",   lambda n: n.replace("--", "--text-", 1))
               + decls("register.inverse.border", lambda n: n.replace("--", "--border-", 1))
               + decls("register.inverse.meaning", lambda n: n.replace("--", "--meaning-", 1))
               + decls("register.inverse.tint",    lambda n: n.replace("--", "--tint-", 1)))

    # --- everything that does not change with register or theme -------------
    stable = []
    for prefix, pre in (("primitive.font.family", "--font-"),
                        ("primitive.font.size", "--size-"),
                        ("primitive.font.lineHeight", "--leading-"),
                        ("primitive.font.tracking", "--tracking-"),
                        ("primitive.font.weight", "--weight-"),
                        ("primitive.space", "--space-"),
                        ("primitive.size", "--measure-"),
                        ("primitive.radius", "--radius-"),
                        ("primitive.stroke", "--stroke-"),
                        ("primitive.duration", "--duration-"),
                        ("primitive.easing", "--easing-"),
                        ("primitive.breakpoint", "--bp-")):
        for path, raw in walk(doc):
            if ".".join(path).startswith(prefix + "."):
                stable.append((pre + "-".join(path[len(prefix.split(".")):]),
                               resolve(raw, index)))
    for prefix, pre in (("domain", "--domain-"),
                        ("semantic.orientation", "--orient-"),
                        ("semantic.measure", "--measure-"),
                        ("semantic.motion.duration", "--motion-"),
                        ("semantic.motion.easing", "--ease-")):
        for path, raw in walk(doc):
            if ".".join(path).startswith(prefix + "."):
                stable.append((pre + "-".join(path[len(prefix.split(".")):]),
                               resolve(raw, index)))
    # component markers and shapes, as CSS strings
    def kebab(x):
        return re.sub(r"(?<!^)(?=[A-Z])", "-", x).lower()

    comp = []
    for path, raw in walk(doc):
        if ".".join(path).startswith("component."):
            comp.append(("--" + "-".join(kebab(p) for p in path[1:]), f'"{raw}"'))

    def block(pairs, indent="  "):
        return "\n".join(f"{indent}{k}: {v};" for k, v in pairs)

    rm = meta["registerModel"]
    return f"""/* ==========================================================================
   xCO tokens v{meta['version']} — GENERATED from design/xco.tokens.json
   Do not edit this file. Run: python3 tools/build_tokens.py
   --------------------------------------------------------------------------
   {rm['principle']}

     register  {rm['register'][:64]}
     theme     {rm['theme'][:64]}

   {rm['resolution'][:76]}
   {rm['resolution'][76:152]}

   Accessibility is enforced, not described: tools/test_tokens.py fails CI on a
   violation. Known measured limit — {meta['accessibilityContract']['knownLimit'][:60]}
   ========================================================================== */

:root {{
  /* --- stable across register and theme --- */
{block(stable)}

  /* --- component markers and shapes: the second channel --- */
{block(comp)}

  /* --- paper register --- */
{block(paper)}
}}

/* The inverse register: authored, and always the opposite ground to its theme. */
[data-register="inverse"] {{
{block(inverse)}
}}

/* Dark theme swaps which value set is the page and which is the inverse band. */
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
{block(inverse, "    ")}
  }}
  :root:not([data-theme="light"]) [data-register="inverse"] {{
{block(paper, "    ")}
  }}
}}

:root[data-theme="dark"] {{
{block(inverse, "    ")}
}}
:root[data-theme="dark"] [data-register="inverse"] {{
{block(paper, "    ")}
}}

/* --------------------------------------------------------------------------
   Compatibility layer.

   Three vocabularies preceded this file and 125 published pages still speak them.
   These aliases are generated, so they cannot drift from the tokens they point at,
   and they are the ONLY place old names survive. New work uses the names above.

   v1  (xco.css / xco-dusk.css)  --shadow --highlight --midtone --midtone-ink
   v2  (this morning's extraction) --paper --ink --rule --serif --s1..--s7
   -------------------------------------------------------------------------- */
:root {{
  /* v1 */
  --shadow: var(--text-primary);
  --highlight: var(--surface-page);
  --midtone: var(--domain-bio-base);
  --midtone-ink: var(--domain-bio-ink);
  --midtone-lift: var(--domain-bio-ink);
  /* v2 */
  --paper: var(--surface-page);
  --paper-deep: var(--surface-quiet);
  --panel: var(--surface-raised);
  --ink: var(--text-primary);
  --ink-soft: var(--text-secondary);
  --ink-faint: var(--text-muted);
  --rule: var(--border-default);
  --serif: var(--font-serif);
  --sans: var(--font-sans);
  --mono: var(--font-mono);
  --measure: var(--measure-prose);
  --content: min(var(--measure-canvas), calc(100vw - 128px));
  --touch: var(--measure-hitTarget);
  --t-fast: var(--motion-interaction);
  --t-mid: var(--motion-stateChange);
  --t-slow: var(--motion-semanticOpen);
  --ease: var(--ease-default);
  --s1: var(--space-100); --s2: var(--space-150); --s3: var(--space-300);
  --s4: var(--space-400); --s5: var(--space-600); --s6: var(--space-1200);
  --s7: var(--space-1600);
  --bio: var(--domain-bio-base); --inst: var(--domain-inst-base);
  --tech: var(--domain-tech-base); --culture: var(--domain-culture-base);
  --bio-ink: var(--domain-bio-ink); --inst-ink: var(--domain-inst-ink);
  --tech-ink: var(--domain-tech-ink); --culture-ink: var(--domain-culture-ink);
  --bio-tint: var(--domain-bio-tint); --inst-tint: var(--domain-inst-tint);
  --tech-tint: var(--domain-tech-tint); --culture-tint: var(--domain-culture-tint);
  --grain: var(--border-default); --grain-blend: multiply; --grain-opacity: .16;
  --elevation: 0 18px 70px rgba(33, 30, 22, .18);
  --label: 210px; --gutter: 42px; --hang: 252px;
  --phi-major: 61.8fr; --phi-minor: 38.2fr;
}}

@media (prefers-reduced-motion: reduce) {{
  :root {{
    --motion-interaction: var(--duration-instant);
    --motion-stateChange: var(--duration-instant);
    --motion-semanticOpen: var(--duration-instant);
    --motion-enunciation: var(--duration-instant);
    --motion-hold: var(--duration-instant);
  }}
}}
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate the token CSS from the JSON source.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed CSS differs from the JSON")
    args = ap.parse_args(argv)

    try:
        css = render()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    existing = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    if args.check:
        if existing == css:
            print("  tokens CSS is in sync with the JSON source.")
            return 0
        print("error: docs/assets/xco-tokens.css is out of date with design/xco.tokens.json.\n"
              "       The CSS is generated. Edit the JSON, then run:\n"
              "         python3 tools/build_tokens.py", file=sys.stderr)
        return 1

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(css)
    n = css.count("--")
    print(f"  wrote {os.path.relpath(OUT)} — {n} declarations from {os.path.relpath(SRC)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
