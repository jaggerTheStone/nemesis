from pathlib import Path

import pytest

from nemesis_pipelines.checksum import ChecksumMismatchError, sha256_file, verify_sha256

# SHA-256 of the ASCII bytes "abc" (FIPS 180-2 test vector).
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_matches_reference_vector(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"abc")
    assert sha256_file(source) == ABC_SHA256


def test_verify_accepts_uppercase_expected_digest(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"abc")
    verify_sha256(source, ABC_SHA256.upper())


def test_verify_rejects_tampered_file(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"abd")
    with pytest.raises(ChecksumMismatchError):
        verify_sha256(source, ABC_SHA256)
