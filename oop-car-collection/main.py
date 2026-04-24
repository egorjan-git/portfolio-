from __future__ import annotations

import argparse
from pathlib import Path
import os

from storage import Storage, DEFAULT_DATA_FILE
from cli import run_cli
from gui import run_gui
from tests import run_all_tests


def main() -> None:
    parser = argparse.ArgumentParser(prog="car_collection")
    parser.add_argument("--cli", action="store_true", help="run console interface")
    parser.add_argument("--gui", action="store_true", help="run tkinter GUI")
    parser.add_argument("--test", action="store_true", help="run tests (assert)")
    args = parser.parse_args()

    if args.test or os.environ.get("RUN_TESTS") == "1":
        run_all_tests()
        return

    storage = Storage(DEFAULT_DATA_FILE)
    catalog = storage.load_catalog()
    data_path = storage.path

    if args.gui:
        run_gui(catalog, data_path)
    else:
        run_cli(catalog, data_path)


if __name__ == "__main__":
    main()
