"""Checksum helpers: every downloaded source is verified before import (I0.7)."""

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


class ChecksumMismatchError(Exception):
    """Raised when a file does not match its expected SHA-256 digest."""


def sha256_file(path: Path) -> str:
    """Returns the hexadecimal SHA-256 digest of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> None:
    """Raises ChecksumMismatchError unless the file matches `expected`."""
    actual = sha256_file(path)
    if actual != expected.strip().lower():
        raise ChecksumMismatchError(f"{path}: expected sha256 {expected}, got {actual}")
