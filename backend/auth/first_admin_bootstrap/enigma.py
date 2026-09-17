"""Production bridge for the governed private Developer Enigma lookup authority.

The shared PostgreSQL catalogue intentionally excludes ``profile_lookup_word``.
Production Developer authentication therefore proves two independent facts before
accepting a response:

* PostgreSQL supplied the active challenge words for the principal's assigned
  catalogue; and
* the locked private source file that originally admitted that catalogue still
  has the same SHA-256 and row words.

Only then is the private ``profile_lookup_word`` used to construct the Developer
challenge signature. The lookup token is never persisted to PostgreSQL.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
from pathlib import Path

from backend.auth.enigma import EnigmaAuthority

from .contracts import AuthenticationRejected


class ProductionDeveloperEnigmaAuthority:
    """Read-only private lookup authority paired with PostgreSQL challenge rows."""

    def __init__(self, catalogue_dir: Path):
        self._authority = EnigmaAuthority(Path(catalogue_dir))
        self._source_sha256 = {
            length: sha256(catalogue.path.read_bytes()).hexdigest()
            for length, catalogue in self._authority.catalogues.items()
        }

    def expected_signature(
        self,
        *,
        word_length: int,
        day: int,
        period: str,
        postgres_words: tuple[str, str, str],
        postgres_source_sha256: str,
        lookup_index: int,
    ) -> str:
        try:
            catalogue = self._authority.catalogues[int(word_length)]
            row = catalogue.row(int(day), str(period))
            local_sha256 = self._source_sha256[int(word_length)]
        except (KeyError, ValueError) as exc:
            raise AuthenticationRejected("Production Developer Enigma authority is unavailable") from exc

        if not postgres_source_sha256 or not hmac.compare_digest(
            local_sha256,
            str(postgres_source_sha256).strip().lower(),
        ):
            raise AuthenticationRejected("Production Developer Enigma source parity failed")

        db_words = tuple(str(value).upper() for value in postgres_words)
        if row.words != db_words:
            raise AuthenticationRejected("Production Developer Enigma row parity failed")

        return f"{int(lookup_index)}{row.profile_lookup_word}"

    @staticmethod
    def verify(response: str, expected_signature: str) -> bool:
        return EnigmaAuthority.verify(response, expected_signature)
