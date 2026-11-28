"""Deterministic evidence-link verification for structured AJUSTA claims.

This module checks provenance and declared evidence direction; it does not browse,
authenticate publishers, or infer semantic entailment from excerpt text.
"""
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

EvidenceRelation = Literal["supports", "contradicts", "context"]


@dataclass(frozen=True)
class EvidenceRecord:
    source_id: str
    url: str
    title: str
    excerpt: str
    relation: EvidenceRelation

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip() or len(self.source_id) > 100:
            raise ValueError("source_id must contain 1 to 100 characters")
        parsed = urlparse(self.url) if isinstance(self.url, str) else None
        if parsed is None or parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("evidence URLs must use HTTPS")
        if parsed.username or parsed.password:
            raise ValueError("evidence URLs must not contain embedded credentials")
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 300:
            raise ValueError("title must contain 1 to 300 characters")
        if not isinstance(self.excerpt, str) or not self.excerpt.strip() or len(self.excerpt) > 5000:
            raise ValueError("excerpt must contain 1 to 5000 characters")
        if self.relation not in ("supports", "contradicts", "context"):
            raise ValueError("relation must be supports, contradicts, or context")


@dataclass(frozen=True)
class VerificationClaim:
    claim_id: str
    statement: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.claim_id, str) or not self.claim_id.strip() or len(self.claim_id) > 100:
            raise ValueError("claim_id must contain 1 to 100 characters")
        if not isinstance(self.statement, str) or not self.statement.strip() or len(self.statement) > 4000:
            raise ValueError("statement must contain 1 to 4000 characters")
        if not isinstance(self.source_ids, tuple) or any(
            not isinstance(value, str) or not value.strip() for value in self.source_ids
        ):
            raise ValueError("source_ids must be a tuple of non-empty strings")


@dataclass(frozen=True)
class VerifiedClaim:
    claim_id: str
    statement: str
    status: Literal["supported", "contradicted", "contested", "unsupported", "invalid"]
    supporting_sources: tuple[str, ...]
    contradicting_sources: tuple[str, ...]
    context_sources: tuple[str, ...]
    unknown_source_ids: tuple[str, ...]


@dataclass(frozen=True)
class VerificationReport:
    claims: tuple[VerifiedClaim, ...]
    source_count: int
    claim_count: int

    @property
    def summary(self) -> dict[str, int]:
        return {
            status: sum(item.status == status for item in self.claims)
            for status in ("supported", "contradicted", "contested", "unsupported", "invalid")
        }


def verify_claims(
    claims: tuple[VerificationClaim, ...],
    evidence: tuple[EvidenceRecord, ...],
) -> VerificationReport:
    """Validate explicit source links and report declared support/conflict.

    A source affects a claim only when its ID is explicitly linked by that claim.
    This is provenance validation, not an automated truth or fact-check verdict.
    """
    if not isinstance(claims, tuple) or any(not isinstance(item, VerificationClaim) for item in claims):
        raise TypeError("claims must be a tuple of VerificationClaim records")
    if not isinstance(evidence, tuple) or any(not isinstance(item, EvidenceRecord) for item in evidence):
        raise TypeError("evidence must be a tuple of EvidenceRecord records")

    source_map: dict[str, EvidenceRecord] = {}
    for source in evidence:
        if source.source_id in source_map:
            raise ValueError(f"duplicate evidence source_id: {source.source_id}")
        source_map[source.source_id] = source

    claim_ids: set[str] = set()
    verified: list[VerifiedClaim] = []
    for claim in claims:
        if claim.claim_id in claim_ids:
            raise ValueError(f"duplicate claim_id: {claim.claim_id}")
        claim_ids.add(claim.claim_id)

        linked_ids = tuple(dict.fromkeys(claim.source_ids))
        unknown = tuple(source_id for source_id in linked_ids if source_id not in source_map)
        linked = tuple(source_map[source_id] for source_id in linked_ids if source_id in source_map)
        supporting = tuple(item.source_id for item in linked if item.relation == "supports")
        contradicting = tuple(item.source_id for item in linked if item.relation == "contradicts")
        context = tuple(item.source_id for item in linked if item.relation == "context")

        if unknown:
            status = "invalid"
        elif supporting and contradicting:
            status = "contested"
        elif supporting:
            status = "supported"
        elif contradicting:
            status = "contradicted"
        else:
            status = "unsupported"

        verified.append(VerifiedClaim(
            claim_id=claim.claim_id,
            statement=claim.statement.strip(),
            status=status,
            supporting_sources=supporting,
            contradicting_sources=contradicting,
            context_sources=context,
            unknown_source_ids=unknown,
        ))

    return VerificationReport(tuple(verified), len(source_map), len(verified))


@dataclass(frozen=True)
class DepartmentEvidenceResponse:
    """Optional structured department result with explicit claim/source links.

    Plain-string department outputs remain supported; only this explicit contract
    is eligible for deterministic evidence verification.
    """
    text: str
    claims: tuple[VerificationClaim, ...]
    evidence: tuple[EvidenceRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip() or len(self.text) > 20000:
            raise ValueError("text must contain 1 to 20000 characters")
        if not isinstance(self.claims, tuple) or len(self.claims) > 100:
            raise ValueError("claims must be a tuple containing at most 100 records")
        if not isinstance(self.evidence, tuple) or len(self.evidence) > 100:
            raise ValueError("evidence must be a tuple containing at most 100 records")
        if any(not isinstance(item, VerificationClaim) for item in self.claims):
            raise TypeError("claims must contain VerificationClaim records")
        if any(not isinstance(item, EvidenceRecord) for item in self.evidence):
            raise TypeError("evidence must contain EvidenceRecord records")
