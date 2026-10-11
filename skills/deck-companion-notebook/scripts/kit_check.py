#!/usr/bin/env python3
"""kit_check.py — deterministic static checker for the Foundry demo-notebook kit.

Runs on a LOCAL copy of the kit folder (the one downloaded fresh in Step 0 of the
deck-companion-notebook skill). It never executes notebook code and never imports
the packages it inspects; everything is derived from the notebook JSON, the AST of
each code cell, requirements.txt (with -r includes), .env.example and README.md.

What it reports
  * compile    every code cell parses (IPython magics / shell escapes stripped,
               top-level await allowed)
  * imports    top-level modules imported per notebook, classified stdlib / mapped
               to a requirement / unmapped
  * api        API-usage inventory: imported names and attribute chains per cell
               (input for breaking-change collision checks, see --breaking)
  * preview    preview-surface markers per notebook (.beta., allow_preview=True,
               *PreviewTool, Foundry-Features header)
  * env        variables read per notebook vs .env.example; collision heuristics
               (different defaults, differing comments, duplicate definitions,
               README "per notebook" warnings)
  * hygiene    per-package %pip/!pip installs, stored outputs, likely secrets
  * reqs       every requirement with spec, comment, section and notebook tags;
               missing comments, uncapped GA ranges, preview packages without a
               minor cap, conflicting specs across -r includes
  * naming     notebook naming pattern, nbformat and the next free notebook number

Usage
  python kit_check.py <kit-dir> [--new foundry-demo-9-x.ipynb ...]
                      [--breaking breaking.json] [--json-output report.json]
                      [--md-output report.md] [--resolve-with /path/to/venv/bin/python]

  --breaking   JSON list of {"package": str, "symbol": str, "change": str, "url": str}
               — each symbol (dotted name or attribute fragment, e.g. "beta.toolboxes"
               or "agent_session_id") is matched against the API inventory and every
               hit is reported with notebook + cell as a collision (FAIL).
  --resolve-with  python executable of a throwaway venv built from requirements.txt;
               imports are then checked with importlib.util.find_spec in that
               interpreter (no notebook code is run).

Exit code: 0 when no FAIL finding, 1 otherwise, 2 on usage error.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

CELL_INDEX_CONVENTION = "cell N = 0-based index over all cells (markdown included), as VS Code counts them"
NB_PATTERN = re.compile(r"^foundry-demo-(\d+)-([a-z0-9][a-z0-9-]*)\.ipynb$")
MAGIC_LINE = re.compile(r"^(\s*)([%!])")
HELP_LINE = re.compile(r"^(\s*)[\w.]+\?{1,2}\s*$")
PIP_LINE = re.compile(r"^\s*[%!]\s*(?:python3?\s+-m\s+)?pip3?\s+install\b(.*)$", re.I)
ALLOWED_PIP = re.compile(r"^\s*(?:(?:-q|--quiet|-U|--upgrade)\s+)*-r\s+\S*requirements\.txt\s*$")

# import-name -> distribution name, for packages whose import name differs from the dist name.
IMPORT_TO_DIST = {
    "dotenv": "python-dotenv",
    "a2a": "a2a-sdk",
    "google.protobuf": "protobuf",
    "yaml": "pyyaml",
    "jwt": "pyjwt",
    "dateutil": "python-dateutil",
    "pydantic_settings": "pydantic-settings",
    "agent_framework": "agent-framework",
    "IPython": "ipython",
    "nest_asyncio": "nest-asyncio",
    "opentelemetry.sdk": "opentelemetry-sdk",
    "opentelemetry.instrumentation.openai_v2": "opentelemetry-instrumentation-openai-v2",
    "opentelemetry.exporter.otlp": "opentelemetry-exporter-otlp",
    "opentelemetry": "opentelemetry-api",
}
PREVIEW_MARKERS = [
    ("attribute .beta.", re.compile(r"\.beta\.")),
    ("allow_preview=True", re.compile(r"allow_preview\s*=\s*True")),
    ("*PreviewTool class", re.compile(r"\b\w+PreviewTool\b")),
    ("Foundry-Features header", re.compile(r"Foundry-Features", re.I)),
]
SECRET_PATTERNS = [
    ("key/secret/password/token literal",
     re.compile(r"(?i)\b\w*(api[_-]?key|secret|password|passwd|token|access[_-]?key)\w*\s*[:=]\s*[\"']"
                r"(?!<)[^\"'\s<>{}]{12,}[\"']")),
    ("connection string", re.compile(r"(?i)(AccountKey|SharedAccessKey|InstrumentationKey)=[A-Za-z0-9+/=-]{16,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
SECRET_NAME = re.compile(r"(?i)(KEY|SECRET|PASSWORD|TOKEN|CONNECTION_STRING)$")
TAG_RANGE = re.compile(r"\bNB\s?(\d+)\s*[–-]\s*(?:NB\s?)?(\d+)\b")
TAG_ONE = re.compile(r"\bNB\s?(\d+)\b")
REQ_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<extras>\[[^\]]*\])?\s*(?P<spec>[^;#]*)(?:;(?P<marker>[^#]*))?$"
)


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# ── notebook parsing ─────────────────────────────────────────────────────────


def cell_source(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src)


def cell_magic(src: str) -> str | None:
    """First line of a `%%` cell magic (leading blank lines ignored, as IPython does), else None."""
    for line in src.splitlines():
        if line.strip():
            return line.strip() if line.lstrip().startswith("%%") else None
    return None


def strip_magics(src: str) -> tuple[str, list[str]]:
    """Replace magic / shell / help lines with `pass` at the same indent; return (code, magics).

    A `!` / `%` line magic continued with a trailing backslash swallows the following lines
    while the previous stripped line ends with `\\`; those continuation lines become blank, so
    line numbers in compile errors still match the cell.
    """
    lines = src.splitlines()
    cm = cell_magic(src)
    if cm:
        return "", [cm]  # whole-cell magic (%%bash, %%writefile …) is not Python
    out, magics = [], []
    continuing = False
    for line in lines:
        if continuing:
            magics[-1] += " " + line.strip()
            out.append("")
            continuing = line.rstrip().endswith("\\")
            continue
        m = MAGIC_LINE.match(line)
        if m:
            magics.append(line.strip())
            out.append(f"{m.group(1)}pass")
            continuing = line.rstrip().endswith("\\")
            continue
        m = HELP_LINE.match(line)
        if m:
            magics.append(line.strip())
            out.append(f"{m.group(1)}pass")
        else:
            out.append(line)
    return "\n".join(out), magics


def compile_cell(code: str, label: str) -> tuple[ast.AST | None, str | None]:
    flags = ast.PyCF_ONLY_AST | getattr(ast, "PyCF_ALLOW_TOP_LEVEL_AWAIT", 0)
    try:
        return compile(code, label, "exec", flags=flags, dont_inherit=True), None
    except SyntaxError as exc:
        return None, f"line {exc.lineno}: {exc.msg}"


def attr_chain(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):  # project.get_openai_client().responses.create
        inner = attr_chain(node.func)
        if inner:
            parts.append(inner + "()")
            return ".".join(reversed(parts))
    return None


def str_arg(call: ast.Call, idx: int = 0) -> str | None:
    if len(call.args) > idx and isinstance(call.args[idx], ast.Constant) and isinstance(call.args[idx].value, str):
        return call.args[idx].value
    return None


def env_reads(tree: ast.AST, src_lines: list[str]) -> list[dict]:
    reads = []
    for node in ast.walk(tree):
        name, default = None, None
        if isinstance(node, ast.Call):
            chain = attr_chain(node.func) or ""
            if chain in ("os.getenv", "getenv", "os.environ.get", "environ.get", "env"):
                name = str_arg(node)
                d = node.args[1] if len(node.args) > 1 else None
                if d is None:
                    for kw in node.keywords:
                        if kw.arg in ("default", "d"):
                            d = kw.value
                if isinstance(d, ast.Constant) and isinstance(d.value, str):
                    default = d.value
        elif isinstance(node, ast.Subscript):
            chain = attr_chain(node.value) or ""
            if chain in ("os.environ", "environ") and isinstance(node.slice, ast.Constant):
                name = node.slice.value if isinstance(node.slice.value, str) else None
        if name and re.match(r"^[A-Z][A-Z0-9_]*$", name):
            ln = getattr(node, "lineno", 0)
            line = src_lines[ln - 1] if 0 < ln <= len(src_lines) else ""
            comment = line.split("#", 1)[1].strip() if "#" in line else ""
            reads.append({"name": name, "default": default, "comment": comment, "line": ln})
    return reads


def analyse_notebook(path: Path) -> dict[str, Any]:
    rel = path.name
    res: dict[str, Any] = {
        "notebook": rel, "cells": 0, "code_cells": 0, "compile_errors": [], "magics": [],
        "imports": [], "imported_names": [], "api_chains": [], "env_reads": [],
        "pip_lines": [], "stored_outputs": [], "secrets": [], "preview": [], "verify_lines": 0,
        "cell_magics": [],
    }
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # malformed JSON is a FAIL finding, not a crash
        res["load_error"] = str(exc)
        return res
    res["nbformat"] = nb.get("nbformat")
    imports, names, chains = set(), set(), defaultdict(set)
    # idx = 0-based index over ALL cells (markdown included), as VS Code counts them
    for idx, cell in enumerate(nb.get("cells", [])):
        res["cells"] += 1
        src = cell_source(cell)
        for label, rx in SECRET_PATTERNS:
            for m in rx.finditer(src):
                res["secrets"].append({"cell": idx, "kind": label, "excerpt": m.group(0)[:12] + "…"})
        if cell.get("cell_type") != "code":
            continue
        res["code_cells"] += 1
        if cell.get("outputs") or cell.get("execution_count") is not None:
            res["stored_outputs"].append(idx)
        for line in src.splitlines():
            pm = PIP_LINE.match(line)
            if pm and not ALLOWED_PIP.match(pm.group(1)):
                res["pip_lines"].append({"cell": idx, "line": line.strip()})
            if "# verify" in line:
                res["verify_lines"] += 1
        for label, rx in PREVIEW_MARKERS:
            if rx.search(src):
                res["preview"].append({"cell": idx, "marker": label})
        code, magics = strip_magics(src)
        res["magics"].extend({"cell": idx, "magic": m} for m in magics)
        cm = cell_magic(src)
        if cm:
            res["cell_magics"].append({"cell": idx, "magic": cm})
            continue
        if not code.strip():
            continue
        tree, err = compile_cell(code, f"{rel}#cell{idx}")
        if err:
            res["compile_errors"].append({"cell": idx, "error": err})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name)
                    names.add(a.name)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imports.add(node.module)
                for a in node.names:
                    names.add(f"{node.module}.{a.name}")
            elif isinstance(node, ast.Attribute):
                c = attr_chain(node)
                if c and "." in c:
                    chains[c].add(idx)
            elif isinstance(node, ast.keyword) and node.arg:
                chains[f"kw:{node.arg}"].add(idx)
        res["env_reads"].extend(dict(r, cell=idx) for r in env_reads(tree, code.splitlines()))
    # keep maximal attribute chains only (drop prefixes covered by a longer chain in the same cells)
    kept: dict[str, set] = {}
    for k in sorted(chains, key=len, reverse=True):
        if not any(o.startswith(k + ".") and chains[k] <= kept[o] for o in kept):
            kept[k] = chains[k]
    res["imports"] = sorted(imports)
    res["imported_names"] = sorted(names)
    res["api_chains"] = [{"chain": k, "cells": sorted(v)} for k, v in sorted(kept.items())]
    return res


# ── shared files ─────────────────────────────────────────────────────────────


def tags_in(text: str) -> list[int]:
    out: set[int] = set()
    for a, b in TAG_RANGE.findall(text):
        lo, hi = sorted((int(a), int(b)))
        out.update(range(lo, hi + 1))
    out.update(int(n) for n in TAG_ONE.findall(text))
    return sorted(out)


def parse_requirements(path: Path, seen: set | None = None) -> list[dict]:
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return []
    if not path.exists():
        return [{"include_error": f"-r include not found: {path}"}]
    seen.add(path)
    reqs, section = [], ""
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if re.match(r"^#\s*-{2,}", line):
                section = line.strip("# -").strip()
            continue
        body, _, comment = line.partition(" #")
        body, comment = body.strip(), comment.strip()
        if body.startswith(("-r ", "--requirement")):
            inc = body.split(None, 1)[1].strip()
            reqs.append({"include": inc, "file": str(path), "line": n, "comment": comment})
            reqs.extend(parse_requirements(path.parent / inc, seen))
            continue
        if body.startswith("-"):
            reqs.append({"option": body, "file": str(path), "line": n})
            continue
        m = REQ_LINE.match(body)
        if not m:
            reqs.append({"unparsed": body, "file": str(path), "line": n})
            continue
        reqs.append({
            "name": m.group("name"), "norm": norm(m.group("name")), "extras": m.group("extras") or "",
            "spec": m.group("spec").replace(" ", ""), "marker": (m.group("marker") or "").strip(),
            "comment": comment, "section": section,
            "tags": sorted(set(tags_in(comment)) | set(tags_in(section))),
            "file": str(path), "line": n,
        })
    return reqs


def split_env_value(rest: str) -> tuple[str, str]:
    """Split the text after `NAME=` into (value, inline comment).

    A quoted value runs to its closing quote; otherwise a `#` that starts the value or is
    preceded by whitespace starts an inline comment (`KEY=   # optional` has an EMPTY value).
    """
    rest = rest.strip()
    if rest[:1] in ("'", '"'):
        end = rest.find(rest[0], 1)
        if end > 0:
            tail = rest[end + 1:].strip()
            return rest[1:end], tail[1:].strip() if tail.startswith("#") else ""
    m = re.search(r"(?:^|\s)#", rest)
    value, inline = (rest[:m.start()], rest[m.end():]) if m else (rest, "")
    return value.strip().strip("\"'"), inline.strip()


def parse_env_example(path: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    if not path.exists():
        return out
    block, pending = "", []
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")  # CRLF / CR kits
    for n, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()
        if not line:
            pending = []
            continue
        commented = False
        if line.startswith("#"):
            inner = line.lstrip("#").strip()
            if re.match(r"^[A-Z][A-Z0-9_]*\s*=", inner):
                line, commented = inner, True
            else:
                if re.match(r"(?i)^(notebook\s+\d+|shared)", inner):
                    block = inner
                pending.append(inner)
                continue
        m = re.match(r"^(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", line)
        if not m:
            continue
        value, inline = split_env_value(m.group(2))
        out[m.group(1)].append({
            "value": value,
            "comment": (inline.strip() or " ".join(pending[-2:])).strip(),
            "block": block, "line": n, "commented_out": commented,
        })
        pending = []
    return out


def parse_readme_env(path: Path) -> tuple[dict[str, str], str]:
    rows: dict[str, str] = {}
    if not path.exists():
        return rows, ""
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2:
            m = re.match(r"^`?([A-Z][A-Z0-9_]{2,})`?$", cells[0])
            if m:
                rows[m.group(1)] = cells[1]
    return rows, text


def module_to_dist(mod: str, req_names: set[str]) -> str | None:
    for key in sorted(IMPORT_TO_DIST, key=len, reverse=True):
        if mod == key or mod.startswith(key + "."):
            return IMPORT_TO_DIST[key]
    parts = mod.split(".")
    for i in range(len(parts), 0, -1):  # azure.ai.projects.models -> azure-ai-projects
        cand = norm("-".join(parts[:i]))
        if cand in req_names:
            return cand
    return None


def resolve_in_venv(python: str, modules: list[str]) -> dict[str, bool]:
    code = ("import importlib.util,json,sys\nmods=json.loads(sys.argv[1])\nr={}\n"
            "for m in mods:\n  try: r[m]=importlib.util.find_spec(m) is not None\n"
            "  except Exception: r[m]=False\nprint(json.dumps(r))")
    try:
        proc = subprocess.run([python, "-c", code, json.dumps(modules)],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    return json.loads(proc.stdout) if proc.returncode == 0 else {}


def jaccard(a: str, b: str) -> float:
    wa, wb = set(re.findall(r"[a-z]{3,}", a.lower())), set(re.findall(r"[a-z]{3,}", b.lower()))
    return len(wa & wb) / len(wa | wb) if wa | wb else 1.0


# ── main check ───────────────────────────────────────────────────────────────


def nb_sort_key(p: Path) -> tuple[int, str]:
    m = NB_PATTERN.match(p.name)
    return (int(m.group(1)) if m else 10**6, p.name)


def run(kit: Path, new: list[str], breaking: list[dict], resolve_with: str | None) -> dict[str, Any]:
    findings: list[dict] = []
    kit_root = kit.resolve()

    def rel(f: str) -> str:
        try:
            return str(Path(f).resolve().relative_to(kit_root))
        except ValueError:
            return str(f)

    def add(level: str, check: str, where: str, msg: str) -> None:
        findings.append({"level": level, "check": check, "where": where, "message": msg})

    notebooks = sorted(kit.glob("*.ipynb"), key=nb_sort_key)
    req_path = kit / "requirements.txt"
    reqs = parse_requirements(req_path) if req_path.exists() else []
    if not req_path.exists():
        add("FAIL", "reqs", "requirements.txt", "requirements.txt not found at kit root")
    env_ex = parse_env_example(kit / ".env.example")
    if not (kit / ".env.example").exists():
        add("FAIL", "env", ".env.example", ".env.example not found at kit root")
    readme_env, readme_text = parse_readme_env(kit / "README.md")
    req_by_name: dict[str, dict] = {}
    for r in reqs:
        if "norm" in r:
            req_by_name.setdefault(r["norm"], r)
    stdlib = set(getattr(sys, "stdlib_module_names", ()))

    nbs = [analyse_notebook(p) for p in notebooks]
    for n in new:
        if not (kit / n).exists():
            add("FAIL", "naming", n, "--new notebook not found in the kit folder")
    numbers = []
    for nb in nbs:
        name = nb["notebook"]
        m = NB_PATTERN.match(name)
        if m:
            numbers.append(int(m.group(1)))
        else:
            add("WARN", "naming", name, "does not match foundry-demo-<n>-<topic>.ipynb")
        if "load_error" in nb:
            add("FAIL", "compile", name, f"notebook JSON unreadable: {nb['load_error']}")
            continue
        if nb.get("nbformat") != 4:
            add("WARN", "naming", name, f"nbformat is {nb.get('nbformat')}, expected 4")
        for e in nb["compile_errors"]:
            add("FAIL", "compile", f"{name} cell {e['cell']}", e["error"])
        for p in nb["pip_lines"]:
            add("FAIL", "hygiene", f"{name} cell {p['cell']}",
                f"per-notebook install `{p['line']}` — install via requirements.txt only")
        for s in nb["secrets"]:
            add("FAIL", "hygiene", f"{name} cell {s['cell']}", f"likely secret ({s['kind']}): {s['excerpt']}")
        if nb["stored_outputs"]:
            add("FAIL" if name in new else "WARN", "hygiene", name,
                f"stored outputs / execution counts in cells {nb['stored_outputs']}")
        nb["import_resolution"] = {}
        for mod in nb["imports"]:
            top = mod.split(".")[0]
            if top in stdlib:
                nb["import_resolution"][mod] = "stdlib"
                continue
            dist = module_to_dist(mod, set(req_by_name))
            if dist and norm(dist) in req_by_name:
                nb["import_resolution"][mod] = f"requirement:{norm(dist)}"
            else:
                nb["import_resolution"][mod] = "unmapped"
                add("WARN", "imports", name,
                    f"import `{mod}` has no matching requirement (expected: {dist or norm(top)}) — "
                    "add it, or confirm it arrives transitively and say so in a comment")
        for cm in nb.get("cell_magics", []):
            add("INFO", "compile", f"{name} cell {cm['cell']}",
                f"cell magic `{cm['magic'][:60]}` — whole cell is not Python, not compiled")
        for pv in nb["preview"]:
            add("INFO", "preview", f"{name} cell {pv['cell']}", f"preview surface: {pv['marker']}")
        for r in nb["env_reads"]:
            if r["name"] not in env_ex:
                add("FAIL", "env", f"{name} cell {r['cell']}", f"`{r['name']}` is read but missing from .env.example")

    nb_numbers = sorted(set(numbers))
    next_free = (max(nb_numbers) + 1) if nb_numbers else 1

    # ── env collisions (heuristics) ──
    usage: dict[str, list[dict]] = defaultdict(list)
    for nb in nbs:
        for r in nb.get("env_reads", []):
            usage[r["name"]].append(dict(r, notebook=nb["notebook"]))
    collisions = []
    for var in sorted(set(usage) | {k for k, v in env_ex.items() if len(v) > 1}):
        uses = usage.get(var, [])
        reasons = []
        per_nb_defaults: dict[str, str] = {}
        for u in uses:
            if u["default"]:
                per_nb_defaults.setdefault(u["notebook"], u["default"])
        if len(set(per_nb_defaults.values())) > 1:
            reasons.append("different defaults per notebook: " +
                           "; ".join(f"{k}={v!r}" for k, v in per_nb_defaults.items()))
        comments: dict[str, str] = {}
        for u in uses:
            if u["comment"]:
                comments.setdefault(u["notebook"], u["comment"])
        cv = list(comments.items())
        for i in range(len(cv)):
            for j in range(i + 1, len(cv)):
                if jaccard(cv[i][1], cv[j][1]) < 0.34:
                    reasons.append(f"inline comments differ: {cv[i][0]} '{cv[i][1]}' vs {cv[j][0]} '{cv[j][1]}'")
        defs = env_ex.get(var, [])
        if len(defs) > 1:
            reasons.append("defined %d times in .env.example (blocks: %s)" %
                           (len(defs), ", ".join(d["block"] or "top" for d in defs)))
        rd = readme_env.get(var, "")
        if re.search(r"(?i)per notebook|differs|separately for each|meaning .* notebook", rd):
            reasons.append(f"README env table warns: '{rd}'")
        nbs_using = sorted({u["notebook"] for u in uses})
        if reasons and (len(nbs_using) > 1 or len(defs) > 1):
            collisions.append({"variable": var, "notebooks": nbs_using, "reasons": reasons})
            add("WARN", "env-collision", var, " | ".join(reasons))
    unused_env = sorted(k for k in env_ex if k not in usage)
    for var, defs in env_ex.items():
        for d in defs:
            if SECRET_NAME.search(var) and d["value"] and not d["value"].startswith("<") and not d["commented_out"]:
                add("FAIL", "hygiene", f".env.example line {d['line']}", f"`{var}` has a value — secrets stay empty")

    # ── requirements ──
    preview_nbs = sorted(nb["notebook"] for nb in nbs if nb.get("preview"))
    seen_names: dict[str, dict] = {}
    for r in reqs:
        if "include_error" in r:
            add("FAIL", "reqs", "requirements", r["include_error"])
        if "unparsed" in r:
            add("WARN", "reqs", f"{rel(r['file'])}:{r['line']}", f"could not parse `{r['unparsed']}`")
        if "norm" not in r:
            continue
        where = f"{rel(r['file'])}:{r['line']}"
        is_root = Path(r["file"]).resolve() == req_path.resolve()
        prev = seen_names.get(r["norm"])
        if prev and prev["spec"] != r["spec"]:
            add("WARN", "reqs", where, f"{r['name']} also specified as `{prev['spec'] or '(any)'}` in "
                f"{rel(prev['file'])}:{prev['line']} — the resolver must satisfy both")
        seen_names.setdefault(r["norm"], r)
        if is_root and not r["comment"]:
            add("WARN", "reqs", where, f"{r['name']} has no inline comment naming its notebooks")
        prerelease = bool(re.search(r"\d(a|b|rc)\d", r["spec"]))
        has_upper = bool(re.search(r"<(?!=)|==|~=", r["spec"]))
        if is_root and ">=" in r["spec"] and not has_upper and not prerelease:
            add("INFO", "reqs", where, f"{r['name']}{r['spec']} has no upper bound — a major bump arrives silently")
    projects = req_by_name.get("azure-ai-projects")
    if projects and preview_nbs:
        minor_capped = bool(re.search(r"<\d+\.\d+", projects["spec"])) or "==" in projects["spec"]
        if not minor_capped:
            add("WARN", "reqs", "azure-ai-projects",
                f"preview surfaces used in {preview_nbs} but spec `{projects['spec']}` has no minor cap")

    # ── breaking-change collisions ──
    collisions_bc = []
    for bc in breaking:
        sym = bc.get("symbol", "")
        if not sym:
            continue
        for nb in nbs:
            cells: set[int] = set()
            imported = False
            for c in nb.get("api_chains", []):
                if sym in c["chain"]:
                    cells.update(c["cells"])
            for nm in nb.get("imported_names", []):
                if nm == sym or nm.endswith("." + sym):
                    imported = True
            if cells or imported:
                hit = {"notebook": nb["notebook"], "cells": sorted(cells), "imported": imported, **bc}
                collisions_bc.append(hit)
                add("FAIL", "breaking", f"{nb['notebook']} cells {sorted(cells) or '(import)'}",
                    f"{bc.get('package', '?')}: `{sym}` — {bc.get('change', '')} ({bc.get('url', 'no URL')})")

    # ── optional executed import resolution ──
    resolution = None
    if resolve_with:
        mods = sorted({m for nb in nbs for m in nb.get("imports", []) if m.split(".")[0] not in stdlib})
        resolution = resolve_in_venv(resolve_with, mods)
        if not resolution:
            add("WARN", "imports", "venv", f"could not query {resolve_with}; import resolution not executed")
        for m, ok in (resolution or {}).items():
            if not ok:
                add("FAIL", "imports", m, "module not importable in the resolved venv")

    per_nb = []
    for nb in nbs:
        lv = [f["level"] for f in findings if f["where"].split(" ")[0] == nb["notebook"]]
        per_nb.append({
            "notebook": nb["notebook"],
            "status": "FAIL" if "FAIL" in lv else ("WARN" if "WARN" in lv else "PASS"),
            "code_cells": nb.get("code_cells", 0), "imports": len(nb.get("imports", [])),
            "env_vars": sorted({r["name"] for r in nb.get("env_reads", [])}),
            "preview": bool(nb.get("preview")), "verify_lines": nb.get("verify_lines", 0),
        })
    counts = {lvl: sum(1 for f in findings if f["level"] == lvl) for lvl in ("FAIL", "WARN", "INFO")}
    return {
        "kit": str(kit), "verdict": "FAIL" if counts["FAIL"] else "PASS", "counts": counts,
        "cell_index_convention": CELL_INDEX_CONVENTION,
        "import_resolution_mode": ("executed (find_spec in venv)" if resolution
                                   else "mapped by reading requirements, not executed"),
        "next_free_notebook_number": next_free, "notebook_summary": per_nb, "findings": findings,
        "env": {"example": dict(env_ex), "unused_in_notebooks": unused_env,
                "collisions": collisions, "readme_table": readme_env},
        "requirements": [dict(r, file=rel(r["file"])) for r in reqs if "norm" in r or "include" in r],
        "breaking_collisions": collisions_bc, "notebooks": nbs,
    }


def to_markdown(rep: dict) -> str:
    esc = lambda s: str(s).replace("|", "/")  # noqa: E731
    L = [f"# Kit check — {rep['kit']}", "",
         f"**Verdict:** {rep['verdict']} · FAIL {rep['counts']['FAIL']} · WARN {rep['counts']['WARN']} · "
         f"INFO {rep['counts']['INFO']}  ", f"**Import resolution:** {rep['import_resolution_mode']}  ",
         f"**Next free notebook number:** {rep['next_free_notebook_number']}  ",
         f"**Cell references:** {rep['cell_index_convention']}", "",
         "## Notebooks", "| Notebook | Status | Code cells | Imports | Preview | `# verify` | Env vars read |",
         "|---|---|---|---|---|---|---|"]
    for n in rep["notebook_summary"]:
        L.append(f"| {n['notebook']} | {n['status']} | {n['code_cells']} | {n['imports']} | "
                 f"{'yes' if n['preview'] else 'no'} | {n['verify_lines']} | {', '.join(n['env_vars']) or '—'} |")
    L += ["", "## Findings", "| Level | Check | Where | Message |", "|---|---|---|---|"]
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    for f in sorted(rep["findings"], key=lambda f: (order[f["level"]], f["check"], f["where"])):
        L.append(f"| {f['level']} | {f['check']} | {esc(f['where'])} | {esc(f['message'])} |")
    if rep["env"]["collisions"]:
        L += ["", "## Environment-variable collisions", "| Variable | Notebooks | Why flagged |", "|---|---|---|"]
        for c in rep["env"]["collisions"]:
            L.append(f"| {c['variable']} | {', '.join(c['notebooks'])} | {esc('; '.join(c['reasons']))} |")
    L += ["", "## Requirements", "| Package | Spec | Section | Notebook tags | Comment | File |",
          "|---|---|---|---|---|---|"]
    for r in rep["requirements"]:
        if "include" in r:
            L.append(f"| -r {r['include']} | | | | {esc(r['comment'])} | {r['file']} |")
        else:
            L.append(f"| {r['name']}{r['extras']} | `{r['spec'] or '(any)'}` | {esc(r['section'])} | "
                     f"{', '.join(map(str, r['tags'])) or '—'} | {esc(r['comment'])} | {r['file']} |")
    L += ["", "## Imports per notebook"]
    for nb in rep["notebooks"]:
        res = nb.get("import_resolution", {})
        L.append(f"- **{nb['notebook']}**: " +
                 (", ".join(f"`{m}` ({res.get(m, '?')})" for m in nb.get("imports", [])) or "none"))
    if rep["env"]["unused_in_notebooks"]:
        L += ["", "## In .env.example but read by no notebook (may be used by agent/ or .http files)",
              ", ".join(f"`{v}`" for v in rep["env"]["unused_in_notebooks"])]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Static checker for the Foundry demo-notebook kit.")
    ap.add_argument("kit", help="local kit folder (README.md, requirements.txt, .env.example, *.ipynb)")
    ap.add_argument("--new", nargs="*", default=[], help="file names of newly generated notebooks (strict outputs check)")
    ap.add_argument("--breaking", help="JSON list of breaking changes {package, symbol, change, url}")
    ap.add_argument("--resolve-with", help="python of a throwaway venv built from requirements.txt")
    ap.add_argument("--json-output")
    ap.add_argument("--md-output")
    a = ap.parse_args()
    kit = Path(a.kit)
    if not kit.is_dir():
        print(f"not a directory: {kit}", file=sys.stderr)
        return 2
    breaking = json.loads(Path(a.breaking).read_text(encoding="utf-8")) if a.breaking else []
    rep = run(kit, a.new, breaking, a.resolve_with)
    md = to_markdown(rep)
    if a.json_output:
        Path(a.json_output).write_text(json.dumps(rep, indent=2, default=list), encoding="utf-8")
    if a.md_output:
        Path(a.md_output).write_text(md, encoding="utf-8")
    if not a.json_output and not a.md_output:
        print(md)
    else:
        print(f"verdict {rep['verdict']} · FAIL {rep['counts']['FAIL']} · WARN {rep['counts']['WARN']} · "
              f"INFO {rep['counts']['INFO']} · next free notebook {rep['next_free_notebook_number']}")
    return 1 if rep["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
