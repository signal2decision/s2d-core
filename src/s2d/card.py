"""The Signal2Decision Decision Card.

A Decision Card is the single output format of every S2D tool. It is not just a
data container: the validators below enforce the platform's honesty rules, so a
card that guesses, hides its sources or overstates its confidence cannot be built.

Honesty rules (enforced at construction time):
  1. Receipts, not guesses: every evidence item and the cost-of-waiting block must
     point to a tool call that exists in the receipt.
  2. No confident guessing: a card with LOW confidence must have status UNCERTAIN.
  3. Always state limits: every card says what the tools do not model and when to
     ask a local expert.
  4. Acting needs a deadline: status ACT requires a deadline on or after the issue date.
  5. The card ID must match the crop (S2D-WHT-0001 is a wheat card).

Cards can also carry a follow-up: when and how the agent will check whether the
decision worked. An agent doesn't stop at the answer; it checks the result afterwards.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "0.1.0"


class _Strict(BaseModel):
    """Base model: unknown fields are rejected so typos never pass silently."""

    model_config = ConfigDict(extra="forbid")


class Crop(str, Enum):
    wheat = "wheat"
    maize = "maize"
    rice = "rice"
    potato = "potato"
    sorghum = "sorghum"
    soybean = "soybean"
    millet = "millet"


CROP_CODES: dict[Crop, str] = {
    Crop.wheat: "WHT",
    Crop.maize: "MAZ",
    Crop.rice: "RIC",
    Crop.potato: "POT",
    Crop.sorghum: "SRG",
    Crop.soybean: "SOY",
    Crop.millet: "MIL",
}


class Status(str, Enum):
    act = "act"
    wait = "wait"
    uncertain = "uncertain"


class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Location(_Strict):
    name: str = Field(min_length=2, description="Human-readable place name, e.g. 'Sargodha'.")
    country_code: str = Field(pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2 code, e.g. 'PK'.")
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ToolCall(_Strict):
    """One entry in the receipt: exactly what ran, on what, and when."""

    id: str = Field(pattern=r"^c[0-9]+$", description="Call ID referenced by evidence, e.g. 'c1'.")
    tool: str = Field(description="Tool name, e.g. 'sowing_window'.")
    tool_version: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    data_source: str = Field(description="Dataset or model behind the call, e.g. 'NASA POWER daily'.")
    data_version: Optional[str] = None
    run_at: datetime


class Evidence(_Strict):
    statement: str = Field(min_length=10, max_length=240)
    call_ids: list[str] = Field(min_length=1, description="Receipt calls that support this statement.")


class Interval(_Strict):
    lower: float
    upper: float
    unit: str
    level: float = Field(default=0.9, gt=0, lt=1, description="Coverage, e.g. 0.9 for a 90% range.")

    @model_validator(mode="after")
    def _ordered(self) -> "Interval":
        if self.lower > self.upper:
            raise ValueError(f"interval lower ({self.lower}) is greater than upper ({self.upper})")
        return self


class Confidence(_Strict):
    level: ConfidenceLevel
    interval: Optional[Interval] = None
    basis: str = Field(min_length=10, description="What the confidence is based on.")


class DelayPoint(_Strict):
    delay_days: int = Field(ge=0)
    value: float


class CostOfWaiting(_Strict):
    """Only present when a tool actually computed it. Never estimated by hand."""

    metric: str = Field(description="e.g. 'median grain yield'.")
    unit: str
    points: list[DelayPoint] = Field(min_length=2)
    summary: str = Field(min_length=10, max_length=200)
    call_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _starts_now_and_increases(self) -> "CostOfWaiting":
        delays = [p.delay_days for p in self.points]
        if delays[0] != 0:
            raise ValueError("cost_of_waiting must start at delay_days = 0 (acting now)")
        if any(b <= a for a, b in zip(delays, delays[1:])):
            raise ValueError("cost_of_waiting delays must be strictly increasing")
        return self


class Trust(_Strict):
    """'When not to trust this' — mandatory on every card."""

    not_modelled: list[str] = Field(min_length=1, description="What the tools do not account for.")
    ask_expert_if: list[str] = Field(min_length=1, description="Situations where a local expert should decide.")


class Decision(_Strict):
    status: Status
    action: str = Field(min_length=5, max_length=120)
    deadline: Optional[date] = None


class FollowUp(_Strict):
    """Follow-through: how and when the agent will check whether the decision worked."""

    check_on: date = Field(description="When the result will be checked.")
    method: str = Field(min_length=10, max_length=200, description="e.g. 'Sentinel-2 NDVI rise confirming emergence'.")
    tool: Optional[str] = Field(default=None, description="Tool that will run the check, e.g. 'field_stress'.")


class Outcome(_Strict):
    """Filled in later, when someone reports what happened."""

    reported_on: date
    followed: Optional[bool] = None
    result: str
    source: Literal["farmer", "agronomist", "dataset", "other"]


class DecisionCard(_Strict):
    schema_version: Literal["0.1.0"] = SCHEMA_VERSION
    id: str = Field(pattern=r"^S2D-[A-Z]{3}-[0-9]{4}$", description="e.g. 'S2D-WHT-0001'.")
    question: str = Field(min_length=10, max_length=160)
    crop: Crop
    location: Location
    issued_on: date
    decision: Decision
    confidence: Confidence
    evidence: list[Evidence] = Field(min_length=1, max_length=5)
    cost_of_waiting: Optional[CostOfWaiting] = None
    trust: Trust
    receipt: list[ToolCall] = Field(min_length=1)
    follow_up: Optional[FollowUp] = None
    outcome: Optional[Outcome] = None
    illustrative: bool = Field(
        default=False, description="True for demo cards whose numbers show the format, not a real result."
    )

    @model_validator(mode="after")
    def _honesty_rules(self) -> "DecisionCard":
        call_ids = [c.id for c in self.receipt]
        if len(call_ids) != len(set(call_ids)):
            raise ValueError("receipt call IDs must be unique")
        known = set(call_ids)

        # Rule 1: receipts, not guesses.
        for i, ev in enumerate(self.evidence):
            missing = set(ev.call_ids) - known
            if missing:
                raise ValueError(f"evidence[{i}] cites calls not in the receipt: {sorted(missing)}")
        if self.cost_of_waiting is not None:
            missing = set(self.cost_of_waiting.call_ids) - known
            if missing:
                raise ValueError(f"cost_of_waiting cites calls not in the receipt: {sorted(missing)}")

        # Rule 2: no confident guessing.
        if self.confidence.level is ConfidenceLevel.low and self.decision.status is not Status.uncertain:
            raise ValueError("a card with low confidence must have status 'uncertain'")

        # Rule 4: acting needs a deadline.
        if self.decision.status is Status.act:
            if self.decision.deadline is None:
                raise ValueError("status 'act' requires a deadline")
            if self.decision.deadline < self.issued_on:
                raise ValueError("deadline cannot be before issued_on")

        # Follow-through: the check must come after the decision is issued.
        if self.follow_up is not None and self.follow_up.check_on <= self.issued_on:
            raise ValueError("follow_up.check_on must be after issued_on")

        # Rule 5: the ID matches the crop.
        expected = CROP_CODES[self.crop]
        if self.id.split("-")[1] != expected:
            raise ValueError(f"card ID {self.id!r} does not match crop {self.crop.value!r} (expected S2D-{expected}-####)")

        return self


def json_schema() -> dict[str, Any]:
    """The published JSON Schema for Decision Cards."""
    schema = DecisionCard.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://signal2decision.org/schema/decision-card/{SCHEMA_VERSION}.json"
    schema["title"] = "S2D Decision Card"
    return schema
