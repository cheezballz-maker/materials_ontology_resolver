"""Inventory the workspace and apply a frozen, individually checked cleanup plan."""

import argparse
import ast
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical_registry"
OUTPUT = Path(__file__).parent / "hygiene_v1"
EXCLUDED = {".git", ".agents", ".codex", ".aws"}
ORPHAN_BRIDGE = "canonical_registry/cosing_pilot/tmp5y54g0ke/RegistryBridge.class"
SYNTHETIC = {
    "stage_c_03a01fd4c96a4a3696a0ee996f62564c.sqlite",
    "stage_c_3a45980af30b44d89c5fff3641880a1b.sqlite",
    "stage_c_8306c8ec602045af8a4116ffd6327759.sqlite",
    "stage_c_b4f532f5c6b54f10945bbf852611e3f8.sqlite",
}
FIXTURE_DIRS = (
    REGISTRY / "controlled_identity_reuse/fixtures",
    REGISTRY / "chemical_concept_registry/fixtures",
)
TEST_INDEX = "canonical_registry/enrichment/local/stage_c_test_index.sqlite"
TRACKED_CHECKOUT = ROOT / "materials_ontology_resolver"


def save(name, data):
    with (OUTPUT / name).open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def guard_paths():
    from canonical_registry.identity_sufficiency.evaluate import _guards

    paths = _guards()
    baseline = json.loads((REGISTRY / "stage_c/data/restricted_expansion/freeze.json").read_text())
    for pin in baseline["pins"].values():
        path = Path(pin["path"])
        if sha(path) != pin["sha256"]:
            raise ValueError(f"Changed development snapshot: {path}")
        paths[str(path)] = pin["sha256"]
    for directory in ("restricted_expansion", "pilot-expansion", "safety_closure", "pilot-safety-final"):
        for path in (REGISTRY / "stage_c/data" / directory).rglob("*"):
            if path.is_file():
                paths[str(path)] = sha(path)
    fixture = json.loads((REGISTRY / "stage_c/data/pilot-expansion/fixture.json").read_text())
    for path in (fixture["capability"]["path"], fixture["concept"]):
        paths[path] = sha(Path(path))
    return paths


def inventory():
    def inspect(path):
        info = path.lstat()
        row = {"path": path.relative_to(ROOT).as_posix(), "type": path.suffix.lower(),
               "bytes": info.st_size, "sha256": None}
        try:
            if path.is_symlink():
                row["hash_note"] = "Symbolic link excluded from content hashing"
            elif getattr(info, "st_file_attributes", 0) & 0x00401000:
                row["hash_note"] = "Cloud placeholder or offline file retained without hydration"
            else:
                row["sha256"] = sha(path)
        except OSError as exc:
            row["hash_note"] = f"Content unavailable ({type(exc).__name__}, OS error {exc.errno})"
        return row

    paths = []
    for directory, children, files in os.walk(ROOT, followlinks=False):
        parent = Path(directory)
        children[:] = [n for n in children if n not in EXCLUDED and parent / n != OUTPUT
                       and not (parent / n).is_symlink() and not (parent / n).is_junction()]
        paths.extend(parent / name for name in files)
    with ThreadPoolExecutor(max_workers=6) as pool:
        return sorted(pool.map(inspect, paths), key=lambda r: r["path"].casefold())


def sqlite_rows(path, query):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        return db.execute(query).fetchall()


def check_fixture(name):
    substance, concept = (d / name for d in FIXTURE_DIRS)
    keys = sqlite_rows(substance, "SELECT source_key FROM stage_c_request ORDER BY source_key")
    expected = {"water", "natural", "isotope_1", "isotope_2", "broad", "failed_official", "partial"}
    if {key for key, in keys} != {"synthetic:" + s for s in expected}:
        raise ValueError(f"Unexpected source keys in {substance}")
    if not concept.is_file():
        raise ValueError(f"Missing paired Concept fixture: {concept}")
    for path in (substance, concept):
        if any(path.with_name(name + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
            raise ValueError(f"Unexpected active sidecar for disposable fixture: {path}")


def references(rows):
    """Gather readable source imports and literal references to removal candidates."""
    names = (*sorted(SYNTHETIC), "tmp5y54g0ke", "stage_c_test_index.sqlite")
    matches = {name: [] for name in names}
    imports = defaultdict(list)
    source_rows = [r for r in rows if r["sha256"] and not r["path"].startswith("materials_ontology_resolver/")]
    pattern = re.compile("|".join(re.escape(name) for name in names).encode("ascii"), re.I)

    def scan(row):
        if row["type"] not in {".py", ".json", ".jsonl", ".md", ".txt", ".log", ".ps1", ".yml", ".toml", ".xml"}:
            return None
        path = ROOT / row["path"]
        raw = path.read_bytes()
        lowered = raw.lower()
        found = {m.group(0).decode("ascii") for m in pattern.finditer(lowered)} if any(
            token in lowered for token in (b"stage_c_", b"tmp5y54g0ke")) else set()
        imported = set()
        if row["type"] == ".py":
            try:
                for node in ast.walk(ast.parse(raw)):
                    if isinstance(node, ast.Import):
                        imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.add(node.module.rsplit(".", 1)[-1])
            except SyntaxError:
                pass
        return row["path"], found, imported

    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(scan, source_rows):
            if result is None:
                continue
            path, found, imported = result
            for name in found:
                if path != "canonical_registry/maintenance/hygiene.py":
                    matches[name].append(path)
            for name in imported:
                imports[name].append(path)
    return matches, {key: sorted(set(values)) for key, values in imports.items()}


def make_plan():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / "archive_manifest.json").exists():
        raise FileExistsError("The completed cleanup plan is retained for audit and rollback")
    protected = guard_paths()
    baseline = json.loads((REGISTRY / "stage_c/data/restricted_expansion/freeze.json").read_text())
    if any(protected.get(k) != v for k, v in baseline["protected"].items()):
        raise ValueError("Protected files differ from the restricted expansion freeze")
    save("protected_before.json", protected)
    rows = inventory()
    save("inventory_before.json", rows)
    refs, imports = references(rows)
    tracked = set(subprocess.check_output(
        ["git", "-C", str(TRACKED_CHECKOUT), "ls-files"], text=True, encoding="utf-8").splitlines())
    for name in SYNTHETIC:
        check_fixture(name)
    fixture_paths = {p.relative_to(ROOT).as_posix() for d in FIXTURE_DIRS for p in d.glob("*.sqlite")
                     if p.name in SYNTHETIC and not refs[p.name]}
    bytecode_paths = {r["path"] for r in rows if r["type"] == ".pyc" and "__pycache__" in Path(r["path"]).parts}
    plan = []
    modules = []
    duplicate_groups = defaultdict(list)
    for row in rows:
        relative = row["path"]
        p = ROOT / relative
        if row["sha256"] and row["type"] in {".class", ".jar", ".sqlite", ".db", ".java", ".py"}:
            duplicate_groups[(row["type"], row["sha256"])].append(relative)
        if row["type"] == ".py":
            frozen = any(part in {"archive", "baseline", "baseline_implementation", "frozen_implementation"}
                         for part in Path(relative).parts)
            consumers = [v for v in imports.get(p.stem, []) if v != relative]
            modules.append({"path": relative, "sha256": row["sha256"],
                            "classification": ("HISTORICAL_ARCHIVE" if frozen else "ACTIVE" if consumers
                                               or p.name.startswith("test_") else "UNRESOLVED_DEPENDENCY"),
                            "possible_static_consumers": consumers,
                            "note": "Flat module names may collide. Static absence does not rule out a CLI or dynamic import."})
        if not row["sha256"] or str(p) in protected or relative.startswith("materials_ontology_resolver/"):
            continue
        if relative == ORPHAN_BRIDGE and not refs["tmp5y54g0ke"]:
            evidence = "Unreferenced abandoned Stage B temporary output, identical to the root compiled bridge"
        elif relative == TEST_INDEX and all(v.endswith("test_stage_c.py") for v in refs[p.name]):
            evidence = "Derived index exclusively selected by the Stage C pytest fixture"
        elif relative in fixture_paths:
            evidence = "Paired disposable Stage C test clone. Exact synthetic checkpoint key set verified in the Substance member. No literal consumer found."
        elif relative in bytecode_paths:
            try:
                source = Path(importlib.util.source_from_cache(str(p)))
            except ValueError:
                source = p.parent.parent / (p.name.split(".cpython-", 1)[0] + ".py")
            if not source.is_file():
                continue
            evidence = "CPython cache under __pycache__ with retained source " + source.relative_to(ROOT).as_posix()
        elif ".pytest_cache" in p.parts and (
                p.name in {"CACHEDIR.TAG", ".gitignore", "README.md"} or p.parent.name == "cache"):
            evidence = "pytest-generated cache metadata or runtime cache"
        else:
            continue
        if relative == TEST_INDEX and any(p.with_name(p.name + suffix).exists()
                                          for suffix in ("-wal", "-shm", "-journal")):
            continue
        plan.append(row | {"classification": "GENERATED_REBUILDABLE", "confidence": "HIGH",
                          "evidence": evidence, "action": "ARCHIVE_THEN_REMOVE",
                          "recovery": "Restore exact bytes from the verified rollback ZIP"})
    save("dependency_findings.json", {"literal_references": refs, "python_modules": modules,
         "tracked_checkout": {"files": len(tracked), "scope": "Preserved separate Git publication checkout"},
         "retained_cache_orphans": sorted(bytecode_paths - {x["path"] for x in plan})})
    save("duplicate_groups.json", [{"type": t, "sha256": d, "paths": paths} for (t, d), paths in sorted(duplicate_groups.items())
                                  if len(paths) > 1 or any(p.endswith("RegistryBridge.class") for p in paths)])
    save("cleanup_manifest.json", {"workspace": str(ROOT), "entries": plan,
                                   "gross_savings_bytes": sum(r["bytes"] for r in plan)})
    print(f"{len(rows):,} inventoried, {len(plan):,} proposed, {sum(r['bytes'] for r in plan):,} bytes", flush=True)


def checked_path(relative):
    path = ROOT / relative
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or ".." in parts or any(p in EXCLUDED for p in parts):
        raise PermissionError(f"Unexpected workspace-relative path: {relative}")
    if not path.resolve().is_relative_to(ROOT):
        raise PermissionError(f"Path escaped workspace: {path}")
    for parent in (path, *path.parents):
        if parent == ROOT:
            break
        if parent.is_symlink() or parent.is_junction():
            raise PermissionError(f"Link in cleanup path: {parent}")
    return path


def apply():
    plan = load("cleanup_manifest.json")
    if plan["workspace"] != str(ROOT) or guard_paths() != load("protected_before.json"):
        raise ValueError("Cleanup workspace or protected evidence changed")
    archive = OUTPUT / "rollback.zip"
    pending = archive.with_suffix(".pending")
    if archive.exists() or pending.exists():
        raise FileExistsError("Rollback archive already exists")
    for entry in plan["entries"]:
        p = checked_path(entry["path"])
        if p.stat().st_size != entry["bytes"] or sha(p) != entry["sha256"]:
            raise ValueError(f"Changed since assessment: {p}")
    members = {}
    by_digest = {}
    with ZipFile(pending, "x", compression=ZIP_DEFLATED, compresslevel=1) as z:
        for entry in plan["entries"]:
            member = by_digest.get(entry["sha256"])
            if member is None:
                member = entry["path"]
                z.write(checked_path(entry["path"]), member)
                by_digest[entry["sha256"]] = member
            members[entry["path"]] = member
    with ZipFile(pending) as z:
        for digest, member in by_digest.items():
            with z.open(member) as f:
                if hashlib.file_digest(f, "sha256").hexdigest() != digest:
                    raise ValueError(f"Archive verification failed: {member}")
    pending.replace(archive)
    save("archive_manifest.json", {"archive": archive.name, "bytes": archive.stat().st_size,
                                   "sha256": sha(archive), "verified_members": plan["entries"], "members": members})
    removed = []
    try:
        for entry in plan["entries"]:
            p = checked_path(entry["path"])
            if sha(p) != entry["sha256"]:
                raise ValueError(f"Changed after archive verification: {p}")
            p.unlink()
            removed.append(entry)
        if any(entry["path"] == ORPHAN_BRIDGE for entry in removed):
            directory = checked_path(ORPHAN_BRIDGE).parent
            if not any(directory.iterdir()):
                directory.rmdir()
    finally:
        save("removed_files.json", removed)
    print(f"Removed {len(removed):,} archived files", flush=True)


def restore():
    manifest = load("archive_manifest.json")
    archive = OUTPUT / manifest["archive"]
    if sha(archive) != manifest["sha256"]:
        raise ValueError("Rollback archive digest changed")
    with ZipFile(archive) as z:
        for entry in manifest["verified_members"]:
            path = checked_path(entry["path"])
            if path.exists():
                if sha(path) != entry["sha256"]:
                    print(f"Skipped existing changed file: {path}")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(manifest["members"][entry["path"]]) as source, path.open("xb") as dest:
                shutil.copyfileobj(source, dest)
            if sha(path) != entry["sha256"]:
                raise ValueError(f"Restore digest mismatch: {path}")


def finish():
    before, after = load("protected_before.json"), guard_paths()
    differences = {p: {"before": before.get(p), "after": after.get(p)}
                   for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    cache = str(REGISTRY / "enrichment/local/chemical_index.sqlite")
    result = {"passed": not (differences.keys() - {cache}), "byte_identical": not differences,
              "differences": differences, "before": before, "after": after}
    save("protected_comparison.json", result)
    if not result["passed"]:
        raise ValueError("Protected content changed")
    rows = inventory()
    save("inventory_after.json", rows)
    before_rows = load("inventory_before.json")
    prior = {r["path"]: r for r in before_rows}
    current = {r["path"]: r for r in rows}
    changes = {"added": sorted(current.keys() - prior.keys()),
               "removed": sorted(prior.keys() - current.keys()),
               "changed": sorted(p for p in prior.keys() & current.keys() if prior[p] != current[p])}
    save("inventory_diff.json", changes)
    evidence_bytes = sum(p.stat().st_size for p in OUTPUT.iterdir() if p.is_file()
                         and p.name != "size_summary.json")
    save("size_summary.json", {"before_files": len(before_rows), "after_files": len(rows),
                              "before_bytes": sum(r["bytes"] for r in before_rows),
                              "after_bytes": sum(r["bytes"] for r in rows),
                              "archive_bytes": (OUTPUT / "rollback.zip").stat().st_size,
                              "maintenance_artifact_bytes": evidence_bytes,
                              "unhashed_before": sum(r["sha256"] is None for r in before_rows),
                              "unhashed_after": sum(r["sha256"] is None for r in rows)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply", "restore", "finish"))
    args = parser.parse_args()
    {"plan": make_plan, "apply": apply, "restore": restore, "finish": finish}[args.action]()
