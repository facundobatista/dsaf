#!/usr/bin/env fades

# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Synchronize the indicated files/dir into a device that is running MicroPython."""

import json
import pathlib
import subprocess
import sys

import ampy.files  # fades adafruit-ampy
import ampy.pyboard
import mpy_cross  # fades

AMPY_PORT = "/dev/ttyUSB0"
AMPY_BAUD = 115200
AMPY_DELAY = 0


class Cache:
    _file = pathlib.Path(".mpdev_sync.stats")

    def __init__(self):
        self._board = None
        if self._file.exists():
            self._stats = json.loads(self._file.read_text())
        else:
            self._stats = {}

    def get_stat(self, path):
        return self._stats.get(str(path))

    def set_stat(self, path, value):
        self._stats[str(path)] = value
        self._file.write_text(json.dumps(self._stats))

    def get_board(self):
        if self._board is None:
            try:
                _board = ampy.pyboard.Pyboard(AMPY_PORT, baudrate=AMPY_BAUD, rawdelay=AMPY_DELAY)
            except ampy.pyboard.PyboardError as exc:
                print("*** Pyboard Error!", exc)
                exit()

            self._board = ampy.files.Files(_board)
        return self._board


cache = Cache()


def get_compiled_bytes(path):
    """Return the bytes of the *compiled* code."""
    if path == "main.py":
        return path.read_bytes(), path

    # we keep these hidden so it's easy to cache them
    compiled_path = path.parent / f".{path.stem}.mpy"

    # in the remote device they need to have the `m` at the end
    destination_path = path.parent / f"{path.stem}.mpy"

    if not compiled_path.exists() or compiled_path.stat().st_mtime < path.stat().st_mtime:
        # does not exist, or it's older than actual file: compile!
        process = mpy_cross.run(path, "-o", compiled_path, stdout=subprocess.PIPE)
        process.wait()
        if process.returncode:
            print(f"ERROR compiling {path}, returncode={process.returncode}, output:")
            print(process.stdout.read())

    return compiled_path.read_bytes(), destination_path


def sync(path):
    if path.name.startswith(("_", "test", ".")):
        # ignore private or test files
        # print(f"   (ignoring {path})")
        return

    if path.is_dir():
        for fpath in path.iterdir():
            sync(fpath)
        return

    cur_mtime = path.stat().st_mtime
    prv_mtime = cache.get_stat(path)
    if cur_mtime == prv_mtime:
        return

    print("Syncing", path)
    board = cache.get_board()

    # ensure parent directories
    for parent in reversed(path.parents):
        if cache.get_stat(parent) is None:
            print("Creating dir", parent)
            # need to create the dir
            try:
                board.mkdir(str(parent))
            except ampy.files.DirectoryExistsError:
                pass
            cache.set_stat(parent, True)

    # only compile Python code, except top-dir 'main.py' as it's the Micropython's entry point
    if str(path) == "main.py" or path.suffix != ".py":
        content = path.read_bytes()
        dest_path = path
    else:
        content, dest_path = get_compiled_bytes(path)
    board.put(str(dest_path), content)
    cache.set_stat(path, cur_mtime)


if len(sys.argv) < 2:
    print("USAGE: mpdev_sync.py PATH [PATH [...]]")
    exit()

for strpath in sys.argv[1:]:
    sync(pathlib.Path(strpath))
print("Done")
