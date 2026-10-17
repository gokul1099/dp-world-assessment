import pytest
from pydantic import ValidationError

from app.schemas.chat import AskRequest
from app.schemas.licence import ExtractedField, LicenceFields


def test_licence_fields_default_to_empty() -> None:
    fields = LicenceFields()

    assert fields.full_name.value is None
    assert fields.other_fields == {}


def test_dates_serialize_as_iso_strings() -> None:
    fields = LicenceFields.model_validate(
        {"date_of_expiry": {"value": "2031-05-04", "confidence": 0.9, "source_page": 1}}
    )

    assert fields.model_dump(mode="json")["date_of_expiry"]["value"] == "2031-05-04"


def test_invalid_date_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LicenceFields.model_validate({"date_of_birth": {"value": "31/02/1990"}})


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_confidence_must_be_between_0_and_1(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ExtractedField[str](value="x", confidence=confidence)


def test_blank_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AskRequest(question="   ")
