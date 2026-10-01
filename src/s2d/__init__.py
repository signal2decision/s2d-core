"""Signal2Decision core: the Decision Card format and its honesty rules."""

from .card import (
    CROP_CODES,
    SCHEMA_VERSION,
    Confidence,
    ConfidenceLevel,
    CostOfWaiting,
    Crop,
    Decision,
    DecisionCard,
    DelayPoint,
    Evidence,
    FollowUp,
    Interval,
    Location,
    Outcome,
    Status,
    ToolCall,
    Trust,
    json_schema,
)
from .render import to_markdown

__version__ = "0.1.0"

__all__ = [
    "CROP_CODES",
    "SCHEMA_VERSION",
    "Confidence",
    "ConfidenceLevel",
    "CostOfWaiting",
    "Crop",
    "Decision",
    "DecisionCard",
    "DelayPoint",
    "Evidence",
    "FollowUp",
    "Interval",
    "Location",
    "Outcome",
    "Status",
    "ToolCall",
    "Trust",
    "json_schema",
    "to_markdown",
]
