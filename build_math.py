# -*- coding: utf-8 -*-
"""Render the equations with KaTeX and cache the result in data/katex.json.

Run this after changing anything in equations.py. It is the only build step
that needs Node, and the cache it writes is committed, so the ordinary page
build stays a pure-Python affair.

    python build_math.py            render and write the cache
    python build_math.py --check    fail if the cache is stale, render nothing

The cache is keyed by the TeX itself, not by the equation name, so renaming an
equation costs nothing and editing one is caught.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import equations                                           # noqa: E402

CACHE = os.path.join(HERE, "data", "katex.json")
SCRIPT = os.path.join(HERE, "tools", "render_math.js")
NODE_DIRS = [os.path.join(os.path.expanduser("~"), "tools", "node"),
             r"C:\Users\mi\tools\node"]


def digest(item):
    """Keyed by the TeX and how it is set, so changing either re-renders."""
    tex = item["tex"] if isinstance(item, dict) else item
    mode = "d" if (not isinstance(item, dict) or item.get("display")) else "i"
    return hashlib.sha256((mode + tex).encode("utf-8")).hexdigest()[:16]


def load():
    if not os.path.exists(CACHE):
        return {}
    with io.open(CACHE, encoding="utf-8") as fh:
        return json.load(fh)


def stale(cache, payload):
    """Names whose TeX is absent from the cache or has changed since."""
    return sorted(name for name, tex in payload.items()
                  if cache.get(name, {}).get("sha") != digest(tex))


def node_cmd():
    for d in NODE_DIRS:
        exe = os.path.join(d, "node.exe")
        if os.path.exists(exe):
            return exe
    return "node"


def render(payload):
    env = dict(os.environ)
    modules = os.path.join(HERE, "node_modules")
    if os.path.isdir(modules):
        env["NODE_PATH"] = modules
    proc = subprocess.run([node_cmd(), SCRIPT],
                          input=json.dumps(payload).encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env)
    if proc.returncode != 0:
        raise SystemExit("KaTeX failed:\n" + proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))


def main(argv):
    payload = equations.tex_payload()
    cache = load()
    missing = stale(cache, payload)

    if "--check" in argv:
        if missing:
            print("stale or missing in %s: %s"
                  % (os.path.basename(CACHE), ", ".join(missing)))
            print("run: python build_math.py")
            return 1
        print("%d equations and symbols, all rendered" % len(payload))
        return 0

    if not missing:
        print("nothing to do: %d entries already rendered" % len(payload))
        return 0

    print("rendering %d of %d with KaTeX" % (len(missing), len(payload)))
    html = render({k: payload[k] for k in missing})
    for name in missing:
        cache[name] = {"sha": digest(payload[name]),
                       "tex": payload[name]["tex"],
                       "display": payload[name]["display"],
                       "html": html[name]}
    # drop anything no longer referenced, so the file does not accumulate
    for gone in set(cache) - set(payload):
        del cache[gone]
        print("  dropped %s, no longer referenced" % gone)
    with io.open(CACHE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(cache, fh, indent=1, ensure_ascii=False, sort_keys=True)
    print("wrote %s (%.1f KB)"
          % (os.path.relpath(CACHE, HERE), os.path.getsize(CACHE) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
