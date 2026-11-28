import pytest

from ajusta_core.verification import (
    EvidenceRecord,
    VerificationClaim,
    verify_claims,
)


def test_claim_is_supported_only_by_linked_supporting_evidence():
    evidence = (
        EvidenceRecord("s1", "https://example.org/a", "Report A", "The policy reduced costs.", "supports"),
        EvidenceRecord("s2", "https://example.org/b", "Report B", "Unrelated context.", "context"),
    )
    report = verify_claims((VerificationClaim("c1", "Costs fell.", ("s1",)),), evidence)
    assert report.claims[0].status == "supported"
    assert report.claims[0].supporting_sources == ("s1",)


def test_opposing_linked_evidence_marks_claim_contested():
    evidence = (
        EvidenceRecord("s1", "https://example.org/a", "A", "Costs fell.", "supports"),
        EvidenceRecord("s2", "https://example.org/b", "B", "Costs did not fall.", "contradicts"),
    )
    report = verify_claims((VerificationClaim("c1", "Costs fell.", ("s1", "s2")),), evidence)
    assert report.claims[0].status == "contested"
    assert report.claims[0].supporting_sources == ("s1",)
    assert report.claims[0].contradicting_sources == ("s2",)


def test_unlinked_evidence_cannot_support_claim():
    evidence = (EvidenceRecord("s1", "https://example.org/a", "A", "Claim is true.", "supports"),)
    report = verify_claims((VerificationClaim("c1", "Claim is true.", ()),), evidence)
    assert report.claims[0].status == "unsupported"


def test_unknown_source_reference_is_reported_as_invalid():
    report = verify_claims((VerificationClaim("c1", "Claim.", ("missing",)),), ())
    assert report.claims[0].status == "invalid"
    assert report.claims[0].unknown_source_ids == ("missing",)


def test_invalid_source_urls_and_duplicate_ids_are_rejected():
    with pytest.raises(ValueError):
        EvidenceRecord("s1", "http://example.org/a", "A", "Excerpt", "supports")
    with pytest.raises(ValueError):
        verify_claims((), (
            EvidenceRecord("s1", "https://example.org/a", "A", "Excerpt", "supports"),
            EvidenceRecord("s1", "https://example.org/b", "B", "Excerpt", "supports"),
        ))


def test_claim_source_references_are_deduplicated_and_deterministic():
    evidence = (EvidenceRecord("s1", "https://example.org/a", "A", "Excerpt", "supports"),)
    report = verify_claims((VerificationClaim("c1", "Claim.", ("s1", "s1")),), evidence)
    assert report.claims[0].supporting_sources == ("s1",)
    assert report.claims[0].status == "supported"
