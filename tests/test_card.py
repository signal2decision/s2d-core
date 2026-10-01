import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from s2d import DecisionCard, json_schema, to_markdown
from s2d.__main__ import main

EXAMPLE = Path(__file__).parent.parent / "examples" / "S2D-WHT-0001.json"


@pytest.fixture
def card_data() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def build(data: dict) -> DecisionCard:
    return DecisionCard.model_validate(data)


def test_example_card_is_valid(card_data):
    card = build(card_data)
    assert card.id == "S2D-WHT-0001"
    assert card.illustrative is True


def test_round_trip_json(card_data):
    card = build(card_data)
    again = DecisionCard.model_validate_json(card.model_dump_json())
    assert again == card


# --- Honesty rule 1: receipts, not guesses ---------------------------------

def test_evidence_must_cite_existing_call(card_data):
    card_data["evidence"][0]["call_ids"] = ["c99"]
    with pytest.raises(ValidationError, match="not in the receipt"):
        build(card_data)


def test_evidence_needs_at_least_one_call(card_data):
    card_data["evidence"][0]["call_ids"] = []
    with pytest.raises(ValidationError):
        build(card_data)


def test_cost_of_waiting_must_cite_existing_call(card_data):
    card_data["cost_of_waiting"]["call_ids"] = ["c42"]
    with pytest.raises(ValidationError, match="cost_of_waiting cites"):
        build(card_data)


def test_cost_of_waiting_is_optional(card_data):
    del card_data["cost_of_waiting"]
    assert build(card_data).cost_of_waiting is None


def test_cost_of_waiting_starts_at_zero(card_data):
    card_data["cost_of_waiting"]["points"][0]["delay_days"] = 3
    with pytest.raises(ValidationError, match="delay_days = 0"):
        build(card_data)


def test_cost_of_waiting_delays_increase(card_data):
    card_data["cost_of_waiting"]["points"][2]["delay_days"] = 7
    with pytest.raises(ValidationError, match="strictly increasing"):
        build(card_data)


def test_receipt_ids_unique(card_data):
    card_data["receipt"][1]["id"] = "c1"
    with pytest.raises(ValidationError, match="unique"):
        build(card_data)


def test_receipt_required(card_data):
    card_data["receipt"] = []
    with pytest.raises(ValidationError):
        build(card_data)


# --- Honesty rule 2: no confident guessing -----------------------------------

def test_low_confidence_cannot_act(card_data):
    card_data["confidence"]["level"] = "low"
    with pytest.raises(ValidationError, match="must have status 'uncertain'"):
        build(card_data)


def test_low_confidence_uncertain_is_fine(card_data):
    card_data["confidence"]["level"] = "low"
    card_data["decision"] = {"status": "uncertain", "action": "Check with a local agronomist before sowing"}
    assert build(card_data).decision.status.value == "uncertain"


# --- Honesty rule 3: always state limits ---------------------------------------

def test_limits_are_mandatory(card_data):
    card_data["trust"]["not_modelled"] = []
    with pytest.raises(ValidationError):
        build(card_data)


# --- Honesty rule 4: acting needs a deadline ------------------------------------

def test_act_requires_deadline(card_data):
    del card_data["decision"]["deadline"]
    with pytest.raises(ValidationError, match="requires a deadline"):
        build(card_data)


def test_deadline_not_before_issue(card_data):
    card_data["decision"]["deadline"] = "2026-10-01"
    with pytest.raises(ValidationError, match="before issued_on"):
        build(card_data)


# --- Honesty rule 5: ID matches crop ------------------------------------------------

def test_id_must_match_crop(card_data):
    card_data["crop"] = "maize"
    with pytest.raises(ValidationError, match="does not match crop"):
        build(card_data)


def test_maize_card(card_data):
    card_data["crop"] = "maize"
    card_data["id"] = "S2D-MAZ-0001"
    assert build(card_data).crop.value == "maize"


# --- Other checks -------------------------------------------------------------------

def test_interval_must_be_ordered(card_data):
    card_data["confidence"]["interval"]["lower"] = 5.0
    with pytest.raises(ValidationError, match="greater than upper"):
        build(card_data)


def test_unknown_fields_rejected(card_data):
    card_data["confidance"] = "typo"
    with pytest.raises(ValidationError):
        build(card_data)


def test_bad_coordinates_rejected(card_data):
    card_data["location"]["lat"] = 120
    with pytest.raises(ValidationError):
        build(card_data)


def test_schema_export():
    schema = json_schema()
    assert schema["title"] == "S2D Decision Card"
    assert "receipt" in schema["required"]
    assert "trust" in schema["required"]


def test_render(card_data):
    md = to_markdown(build(card_data))
    assert "When not to trust this" in md
    assert "Receipt" in md
    assert "S2D-WHT-0001" in md


def test_render_rejects_unknown_language(card_data):
    with pytest.raises(ValueError):
        to_markdown(build(card_data), lang="fr")


def test_cli_validate(tmp_path, card_data, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(card_data), encoding="utf-8")
    bad_data = copy.deepcopy(card_data)
    bad_data["confidence"]["level"] = "low"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(bad_data), encoding="utf-8")

    assert main(["validate", str(good)]) == 0
    assert main(["validate", str(good), str(bad)]) == 1
    out = capsys.readouterr().out
    assert "OK" in out and "FAIL" in out


# --- Follow-through -------------------------------------------------------------

def test_follow_up_present_in_example(card_data):
    assert build(card_data).follow_up.tool == "field_stress"


def test_follow_up_must_be_after_issue(card_data):
    card_data["follow_up"]["check_on"] = "2026-11-01"
    with pytest.raises(ValidationError, match="follow_up.check_on"):
        build(card_data)


def test_follow_up_rendered(card_data):
    assert "Follow-up check" in to_markdown(build(card_data))
