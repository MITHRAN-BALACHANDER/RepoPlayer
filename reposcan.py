"""
Compatibility shim — the canonical CLI entry point is now cli.py.

This file is kept so that existing `python reposcan.py` commands still work,
but it shadows the reposcan/ package on sys.path. Prefer cli.py for new usage.
"""
import runpy
import pathlib

if __name__ == "__main__":
    runpy.run_path(
        str(pathlib.Path(__file__).with_name("cli.py")),
        run_name="__main__",
    )
