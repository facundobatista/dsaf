#!/usr/bin/env fades

# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Synchronize the indicated files/dir into a device that is running MicroPython."""

import json
import pathlib
import sys

import ampy.files  # fades adafruit-ampy
import ampy.pyboard

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


def sync(path):
    if path.name.startswith("_"):
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
    content = path.read_bytes()
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

    board.put(str(path), content)
    cache.set_stat(path, cur_mtime)


if len(sys.argv) < 2:
    print("USAGE: mpdev_sync.py PATH [PATH [...]]")
    exit()

for strpath in sys.argv[1:]:
    sync(pathlib.Path(strpath))
print("Done")
