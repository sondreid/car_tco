"""Very small test runner."""

from __future__ import annotations

import inspect
from pathlib import Path
import runpy
import sys
from tempfile import TemporaryDirectory


def iter_test_files() -> list[Path]:
    root = Path(__file__).resolve().parent
    return sorted(path for path in root.glob("test_*.py") if path.stem != "run_tests")


def run_test(func) -> None:
    params = inspect.signature(func).parameters
    if not params:
        func()
        return
    if tuple(params) == ("tmp_path",):
        with TemporaryDirectory() as tmp_dir:
            func(Path(tmp_dir))
        return
    raise TypeError(f"unsupported test signature: {func.__name__}{inspect.signature(func)}")


def main() -> int:
    total = 0
    failures: list[tuple[str, Exception]] = []
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))
    for path in iter_test_files():
        namespace = runpy.run_path(str(path))
        for name, func in inspect.getmembers(type("ModuleProxy", (), namespace), inspect.isfunction):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                run_test(func)
            except Exception as exc:
                failures.append((f"{path.stem}.{name}", exc))

    if failures:
        print(f"{len(failures)}/{total} tests failed")
        for name, exc in failures:
            print(f"- {name}: {exc}")
        return 1

    print(f"{total} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
