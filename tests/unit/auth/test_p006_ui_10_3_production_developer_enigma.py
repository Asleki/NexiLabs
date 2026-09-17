from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from backend.auth.first_admin_bootstrap.contracts import AuthenticationRejected
from backend.auth.first_admin_bootstrap.enigma import ProductionDeveloperEnigmaAuthority


def _word(index: int, length: int, salt: int = 0) -> str:
    value = index + salt
    chars = []
    for _ in range(length):
        chars.append(chr(ord("A") + value % 26))
        value //= 26
    return "".join(reversed(chars))


def _write_catalogues(directory: Path, lookup: str = "LOOKUP") -> dict[int, str]:
    directory.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for length in (3, 4, 5):
        lines = ["day,time_of_day,word_1,word_2,word_3,profile_lookup_word"]
        index = 0
        for day in range(1, 32):
            for period in ("Morning", "Noon", "Evening"):
                words = (
                    _word(index, length),
                    _word(index, length, 1000),
                    _word(index, length, 2000),
                )
                lines.append(f"{day},{period},{words[0]},{words[1]},{words[2]},{lookup}")
                index += 1
        path = directory / f"enigma_words_{length}.csv"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        hashes[length] = sha256(path.read_bytes()).hexdigest()
    return hashes


def test_production_developer_enigma_uses_private_lookup_word_only_after_source_and_row_parity(tmp_path: Path):
    hashes = _write_catalogues(tmp_path, lookup="END")
    authority = ProductionDeveloperEnigmaAuthority(tmp_path)
    row = authority._authority.catalogues[3].row(16, "Evening")

    expected = authority.expected_signature(
        word_length=3,
        day=16,
        period="Evening",
        postgres_words=row.words,
        postgres_source_sha256=hashes[3],
        lookup_index=25,
    )

    assert expected == "25END"
    assert authority.verify(" 25end ", expected) is True


def test_production_developer_enigma_rejects_private_source_hash_drift(tmp_path: Path):
    _write_catalogues(tmp_path)
    authority = ProductionDeveloperEnigmaAuthority(tmp_path)
    row = authority._authority.catalogues[4].row(15, "Noon")

    with pytest.raises(AuthenticationRejected, match="source parity"):
        authority.expected_signature(
            word_length=4,
            day=15,
            period="Noon",
            postgres_words=row.words,
            postgres_source_sha256="0" * 64,
            lookup_index=27,
        )


def test_production_developer_enigma_rejects_postgresql_private_row_drift(tmp_path: Path):
    hashes = _write_catalogues(tmp_path)
    authority = ProductionDeveloperEnigmaAuthority(tmp_path)

    with pytest.raises(AuthenticationRejected, match="row parity"):
        authority.expected_signature(
            word_length=5,
            day=15,
            period="Noon",
            postgres_words=("WRONG", "WORDS", "XXXXX"),
            postgres_source_sha256=hashes[5],
            lookup_index=30,
        )
