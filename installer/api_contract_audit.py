"""Static API/import contract audit used before freezing the Windows build.

The GUI is intentionally lazy-loaded, so a successful startup does not prove
that a feature module can be imported when its page/dialog is opened. This
scanner resolves every ``from app... import ...`` and ``import app...`` found
under ``app/`` and verifies that the referenced module/symbol exists.
Qt-dependent modules are reported as deferred when PySide6 is unavailable.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class Issue:
    source: str
    target: str
    kind: str
    detail: str


def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _local_module_roots() -> set[str]:
    """Return top-level names belonging to this project's app package."""
    app_root = ROOT / "app"
    roots: set[str] = set()
    for child in app_root.iterdir():
        if child.is_dir() and (child / "__init__.py").exists():
            roots.add(child.name)
        elif child.is_file() and child.suffix == ".py":
            roots.add(child.stem)
    return roots


def _normalize_local_target(name: str, local_roots: set[str]) -> str | None:
    """Map legacy absolute project imports (e.g. proxy.cache) to app.proxy.cache."""
    top = name.split(".", 1)[0]
    if top in local_roots and not name.startswith("app."):
        return f"app.{name}"
    return None


def audit() -> tuple[list[Issue], list[str]]:
    issues: list[Issue] = []
    deferred: list[str] = []
    local_roots = _local_module_roots()

    def check_module(source: Path, target: str, original: str | None = None) -> None:
        normalized = _normalize_local_target(target, local_roots)
        if normalized:
            issues.append(Issue(
                str(source), target, "local-import",
                f"project-local import must use canonical '{normalized}'"
            ))
            target = normalized

        if not target.startswith("app"):
            return
        if not _module_exists(target):
            issues.append(Issue(str(source), target, "module", "module not found"))
            return
        try:
            importlib.import_module(target)
        except ModuleNotFoundError as exc:
            if exc.name == "PySide6":
                deferred.append(target)
            else:
                issues.append(Issue(str(source), target, "import", str(exc)))
        except Exception as exc:
            issues.append(Issue(str(source), target, "import", f"{type(exc).__name__}: {exc}"))

    for path in sorted((ROOT / "app").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            issues.append(Issue(str(path), "", "syntax", str(exc)))
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target.startswith("app") or target.split(".", 1)[0] in local_roots:
                        check_module(path, target)

            elif isinstance(node, ast.ImportFrom) and node.module:
                # Resolve relative imports against the importing file's package.
                # Example: app/agents/orchestrator.py -> "from .agents import ..."
                if node.level:
                    rel_parts = path.relative_to(ROOT).with_suffix("").parts
                    package_parts = list(rel_parts[:-1])
                    up = node.level - 1
                    if up:
                        package_parts = package_parts[:-up]
                    target = ".".join(package_parts + node.module.split("."))
                    if not target.startswith("app."):
                        continue
                    check_target = target
                else:
                    target = node.module
                    if not (target.startswith("app") or target.split(".", 1)[0] in local_roots):
                        continue
                    normalized = _normalize_local_target(target, local_roots)
                    if normalized:
                        issues.append(Issue(
                            str(path), target, "local-import",
                            f"project-local import must use canonical '{normalized}'"
                        ))
                        check_target = normalized
                    else:
                        check_target = target

                if not _module_exists(check_target):
                    issues.append(Issue(str(path), check_target, "module", "module not found"))
                    continue
                try:
                    module = importlib.import_module(check_target)
                except ModuleNotFoundError as exc:
                    if exc.name == "PySide6":
                        deferred.append(check_target)
                    else:
                        issues.append(Issue(str(path), check_target, "import", str(exc)))
                    continue
                except Exception as exc:
                    issues.append(Issue(str(path), check_target, "import", f"{type(exc).__name__}: {exc}"))
                    continue

                for alias in node.names:
                    if alias.name == "*":
                        continue
                    child = f"{check_target}.{alias.name}"
                    if _module_exists(child):
                        continue
                    if not hasattr(module, alias.name):
                        issues.append(Issue(
                            str(path), child, "symbol",
                            "symbol not exported by module"
                        ))


    return issues, sorted(set(deferred))


if __name__ == "__main__":
    issues, deferred = audit()
    if issues:
        print("API contract audit FAILED")
        for item in issues:
            print(f"- {item.source}: {item.target} [{item.kind}] {item.detail}")
        raise SystemExit(1)
    print("API contract audit OK: app import/module/symbol references resolve.")
    if deferred:
        print(f"Qt-deferred modules: {len(deferred)} (PySide6 unavailable in this environment)")
