"""Project paths and lazy access to pinned upstream format readers."""
from pathlib import Path
import importlib
import sys
import types
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/python-deps"))


def upstream(repo, alias):
    candidates = sorted(p for p in (ROOT / "tools").glob(repo + "-*") if p.is_dir())
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one pinned {repo} checkout, found {len(candidates)}")
    # Namespace package avoids executing the addon's Blender UI __init__.
    if alias not in sys.modules:
        package = types.ModuleType(alias)
        package.__path__ = [str(candidates[0])]
        sys.modules[alias] = package
    return alias


def reader(repo, alias, module):
    return importlib.import_module(upstream(repo, alias) + "." + module)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def confined(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes output directory: {relative}")
    return path

