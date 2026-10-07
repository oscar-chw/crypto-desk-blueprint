"""Shared harness for the evidence experiments: CLI, timing, result schema and the offline data loader.

Each experiment module defines META (id, the rule it backs, the claim, the control, its data) and
run(quick) -> dict. `execute` adds timing and provenance, validates the schema and writes
results/<id>.json. Quick mode shrinks n but runs the same code path; it is what CI runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
DATA = ROOT / "data"
SUPPORTS, NOT_SUPPORTED = "supports", "does not support"
REQUIRED = ("id", "backs", "claim", "script", "data", "inputs", "seeds", "quick", "metric", "treatment",
            "control", "effect", "verdict", "verdict_rule", "summary", "runtime_s")


def mean_se(x) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    return float(x.mean()), float(x.std(ddof=1) / math.sqrt(len(x)))


def prop_se(p: float, n: int) -> float:
    return math.sqrt(max(p * (1 - p), 1e-12) / n)


def boot_se(x, stat: Callable, rng: np.random.Generator, n_boot: int = 500) -> float:
    """Bootstrap standard error of `stat` (e.g. a quantile) over iid replications."""
    x = np.asarray(x, dtype=float)
    return float(np.std([stat(x[rng.integers(0, len(x), len(x))]) for _ in range(n_boot)], ddof=1))


def verdict(ok: bool) -> str:
    return SUPPORTS if ok else NOT_SUPPORTED


def _finite_numbers(d) -> int:
    if isinstance(d, dict):
        return sum(_finite_numbers(v) for v in d.values())
    if isinstance(d, (list, tuple)):
        return sum(_finite_numbers(v) for v in d)
    return int(isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d))


def validate(res: dict) -> None:
    """Raise if a result lacks a field, a computed arm, an uncertainty, or a valid verdict."""
    missing = [k for k in REQUIRED if k not in res]
    if missing:
        raise ValueError(f"{res.get('id')}: missing {missing}")
    for arm in ("treatment", "control"):
        if not isinstance(res[arm], dict) or _finite_numbers(res[arm]) == 0:
            raise ValueError(f"{res['id']}: {arm} arm has no finite metric value")
    eff = res["effect"]
    if not ({"se", "ci95"} & set(eff) or eff.get("uncertainty") == "none: exact count"):
        raise ValueError(f"{res['id']}: effect needs se, ci95 or an exact-count note")
    if res["verdict"] not in (SUPPORTS, NOT_SUPPORTED):
        raise ValueError(f"{res['id']}: bad verdict {res['verdict']!r}")
    if not res["seeds"] and res["data"]["kind"] == "synthetic":
        raise ValueError(f"{res['id']}: synthetic experiment without a seed")


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else round(float(o), 6)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def execute(meta: dict, run: Callable[[bool], dict], quick: bool, out_dir: Path | None = None) -> dict:
    t = time.perf_counter()
    body = run(quick)
    res = {**meta, **body, "quick": quick, "runtime_s": round(time.perf_counter() - t, 2),
           "env": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}}
    res = _clean(res)
    validate(res)
    out = Path(out_dir) if out_dir else RESULTS
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{meta['id']}.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def main(meta: dict, run: Callable[[bool], dict]) -> int:
    ap = argparse.ArgumentParser(description=meta["claim"])
    ap.add_argument("--quick", action="store_true", help="small n, same code path (CI)")
    ap.add_argument("--out", type=Path, default=None, help="directory for the JSON (default results/)")
    a = ap.parse_args()
    res = execute(meta, run, a.quick, a.out)
    print(f"{res['id']}: {res['verdict']} -- {res['summary']} ({res['runtime_s']} s)")
    return 0


# --- committed public-data extract ------------------------------------------------------------------
def load_csv(name: str) -> pd.DataFrame:
    """Read a committed extract after checking it against data/MANIFEST.json. A missing or altered file
    raises: an experiment must never run on data the manifest does not vouch for."""
    manifest = json.loads((DATA / "MANIFEST.json").read_text())
    entry = next(f for f in manifest["files"] if f["file"] == name)
    blob = (DATA / name).read_bytes()
    if hashlib.sha256(blob).hexdigest() != entry["sha256"]:
        raise ValueError(f"{name} does not match its SHA-256 in data/MANIFEST.json")
    return pd.read_csv(DATA / name)


def public_data(files: list[str], urls: list[str]) -> dict:
    manifest = json.loads((DATA / "MANIFEST.json").read_text())
    return {"kind": "public", "files": files, "source_urls": urls, "fetched_utc": manifest["fetched_utc"]}


def synthetic(process: str) -> dict:
    return {"kind": "synthetic", "process": process}
