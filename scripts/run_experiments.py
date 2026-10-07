"""Run every evidence experiment, write results/EXP-*.json, draw the figures, and regenerate every result
line in the docs from those JSON files (nothing in a results table is typed by hand).

    python scripts/run_experiments.py              # full run (minutes), rewrites the docs
    python scripts/run_experiments.py --quick --out /tmp/x   # small n, same code, docs untouched
    python scripts/run_experiments.py --only EXP-08-1        # one experiment, then rewrite the docs

Generated regions: the table between the results markers in blueprint/EVIDENCE.md and the summary
between the markers in README.md; the `result: ...` tag of each EXP bullet in blueprint/0N-*.md; the
EXP cell of each row in blueprint/FOUNDATIONS.md. Exits non-zero if any experiment fails, if a result
is missing for an EXP id the blueprint mentions, or if a result on disk came from a quick run.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments._common import RESULTS, SUPPORTS, execute, validate  # noqa: E402

BLUEPRINT = ROOT / "blueprint"
FIGURES = ROOT / "docs" / "figures"
FIGURE_IDS = ("EXP-08-1", "EXP-06-1", "EXP-04-1")
ID_RE = re.compile(r"EXP-\d\d-\d")


def scripts() -> list[Path]:
    return sorted((ROOT / "experiments").glob("EXP-*.py"))


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mentioned_ids() -> set[str]:
    return {m for f in BLUEPRINT.glob("0*.md") for m in ID_RE.findall(f.read_text())}


def read_results() -> dict[str, dict]:
    out = {}
    for f in sorted(RESULTS.glob("EXP-*.json")):
        res = json.loads(f.read_text())
        validate(res)
        if res["quick"]:
            raise SystemExit(f"{f.name} came from a quick run; rerun without --quick")
        if "|" in res["summary"]:
            raise SystemExit(f"{f.name}: summary contains '|', which would break a table")
        out[res["id"]] = res
    missing = mentioned_ids() - set(out)
    if missing:
        raise SystemExit(f"no result for {sorted(missing)}")
    return out


def _verdict_md(v: str) -> str:
    return v if v == SUPPORTS else f"**{v}**"


def _data_kind(res: dict) -> str:
    d = res["data"]
    if d["kind"] == "public":
        return "public"
    return "synthetic" if d["kind"] == "synthetic" and "public" not in d else "synthetic + public"


def replace_between(text: str, tag: str, body: str) -> str:
    start, end = f"<!-- {tag}:start -->", f"<!-- {tag}:end -->"
    if start not in text or end not in text:
        raise SystemExit(f"marker {start} missing")
    head, rest = text.split(start, 1)
    return head + start + "\n" + body + "\n" + end + rest.split(end, 1)[1]


def counts_line(res: dict[str, dict]) -> str:
    bad = [k for k, r in res.items() if r["verdict"] != SUPPORTS]
    n_ok = len(res) - len(bad)
    tail = f" Not supported: {', '.join(bad)}." if bad else ""
    return f"{n_ok} of {len(res)} experiments support their rule.{tail}"


def write_docs(res: dict[str, dict]) -> None:
    rows = ["| id | backs | claim under test | control | data | result | verdict |", "|---|---|---|---|---|---|---|"]
    for k, r in sorted(res.items()):
        stage = r["backs"].split(" ")[0]
        rows.append(f"| [{k}](../{r['script']}) | [{stage[:2]}]({stage}.md) {r['backs'].split(' ', 1)[1]} | {r['claim']} | "
                    f"{r['control']['arm']} | {_data_kind(r)} | {r['summary']} ([json](../results/{k}.json)) | "
                    f"{_verdict_md(r['verdict'])} |")
    ev = BLUEPRINT / "EVIDENCE.md"
    ev.write_text(replace_between(ev.read_text(), "results", counts_line(res) + "\n\n" + "\n".join(rows)))

    for f in sorted(BLUEPRINT.glob("0*.md")):
        text = f.read_text()
        for k, r in res.items():
            pat = re.compile(rf"(\*\*{k}\*\*.*?)`result: [^`]*`")
            text = pat.sub(lambda m, r=r: f"{m.group(1)}`result: {r['verdict']}: {r['summary']}`", text)
        f.write_text(text)

    fnd = BLUEPRINT / "FOUNDATIONS.md"
    cell = re.compile(r"\| \[?(EXP-\d\d-\d)(?:\]\(EVIDENCE\.md\))?[^|]* \|")
    fnd.write_text(cell.sub(lambda m: f"| [{m.group(1)}](EVIDENCE.md): {res[m.group(1)]['verdict']}; "
                                      f"{res[m.group(1)]['summary']} |", fnd.read_text()))

    readme = ROOT / "README.md"
    real = sorted(k for k, r in res.items() if "public" in r["data"] or r["data"]["kind"] != "synthetic")
    body = (f"{counts_line(res)} Experiments on public Binance data: {', '.join(real)}; the rest use synthetic data "
            f"with a stated generating process. Full table: [blueprint/EVIDENCE.md](blueprint/EVIDENCE.md).")
    readme.write_text(replace_between(readme.read_text(), "results", body))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small n, same code path; docs are not rewritten")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--only", default=None, help="run one id, e.g. EXP-08-1")
    a = ap.parse_args()
    if a.quick and a.out is None:
        ap.error("--quick needs --out so quick numbers never land in results/")
    paths = [p for p in scripts() if a.only is None or p.name.startswith(a.only + "-")]
    if not paths:
        print("run_experiments: no experiment scripts found")
        return 1
    failed = []
    for p in paths:
        mod = load(p)
        try:
            r = execute(mod.META, mod.run, a.quick, a.out)
        except Exception as e:  # report every failure, then fail the run
            failed.append(f"{p.name}: {type(e).__name__}: {e}")
            continue
        print(f"{r['id']}: {r['verdict']:<16} {r['runtime_s']:>7.1f} s  {r['summary']}")
        if not a.quick and r["id"] in FIGURE_IDS and hasattr(mod, "figure"):
            FIGURES.mkdir(parents=True, exist_ok=True)
            mod.figure(r, FIGURES / f"{r['id']}.png")
    if failed:
        print("run_experiments: FAILED\n  " + "\n  ".join(failed))
        return 1
    if not a.quick:
        res = read_results()
        write_docs(res)
        print(f"run_experiments: {counts_line(res)} Docs regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
