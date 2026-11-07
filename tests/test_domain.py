import pytest

from face_workbench.domain import (
    InvalidPersonName,
    normalize_person_name,
    unknown_prediction,
)


def test_normalize_person_name_collapses_whitespace_and_unicode() -> None:
    assert normalize_person_name("  Zhang　San  ") == "Zhang San"


@pytest.mark.parametrize("name", ["", "   ", ".", "..", "../alice", "a/b", "a\\b"])
def test_normalize_person_name_rejects_unsafe_values(name: str) -> None:
    with pytest.raises(InvalidPersonName):
        normalize_person_name(name)


def test_unknown_prediction_has_no_identity_and_zero_confidence() -> None:
    prediction = unknown_prediction((1, 2, 30, 40))

    assert prediction.label == "Unknown"
    assert prediction.known is False
    assert prediction.confidence == 0.0
    assert prediction.box == (1, 2, 30, 40)
