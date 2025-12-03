from __future__ import annotations

from typing import Any, Mapping, Sequence, TextIO

from snbtlib.formatter import dumps as d, loads as l

__all__ = [
    "dump",
    "dumps",
    "load",
    "loads",
]


def dump(obj: Any, fp: TextIO, **kwargs: Any) -> None:
    """Serialize obj to SNBT and write it to a text file object.

    This is a thin wrapper around snbtlib.formatter.dumps.
    """
    fp.write(d(obj, **kwargs))


def dumps(obj: Any, **kwargs: Any) -> str:
    """Serialize a Python object (dict/list/str/bool/bytes) to SNBT text."""
    return d(obj, **kwargs)


def load(fp: TextIO, **kwargs: Any) -> Any:
    """Read text from a file-like object and parse it from SNBT."""
    return l(fp.read(), **kwargs)


def loads(s: str, **kwargs: Any) -> Any:
    """Parse an SNBT string into Python types.

    Note: when passing format=True, a JSON string is returned for convenience.
    """
    return l(s, **kwargs)

