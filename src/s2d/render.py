"""Render a Decision Card as Markdown.

Labels live in one table so more languages can be added later without touching the
rendering logic. Version 0.1 ships English only.
"""

from __future__ import annotations

from .card import DecisionCard

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "question": "The question",
        "decision": "The decision",
        "confidence": "Confidence",
        "why": "Why",
        "cost": "The cost of waiting",
        "trust": "When not to trust this",
        "not_modelled": "Not modelled",
        "ask_expert": "Ask a local expert if",
        "receipt": "Receipt",
        "follow_up": "Follow-up check",
        "deadline": "Deadline",
        "illustrative": "Illustrative example: the numbers show the format, not a real result.",
        "act": "ACT",
        "wait": "WAIT",
        "uncertain": "UNCERTAIN",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "days": "days",
    },
}


def to_markdown(card: DecisionCard, lang: str = "en") -> str:
    if lang not in LABELS:
        raise ValueError(f"unsupported language {lang!r}; choose from {sorted(LABELS)}")
    t = LABELS[lang]
    loc = card.location
    lines: list[str] = []

    lines.append(f"# {card.id}")
    if card.illustrative:
        lines.append(f"> {t['illustrative']}")
    lines.append("")
    lines.append(f"## {t['question']}")
    lines.append(card.question)
    lines.append(
        f"{loc.name}, {loc.country_code} · {loc.lat:.2f}, {loc.lon:.2f} · {card.crop.value} · {card.issued_on.isoformat()}"
    )
    lines.append("")
    lines.append(f"## {t['decision']}: **{t[card.decision.status.value]}**")
    lines.append(card.decision.action)
    if card.decision.deadline:
        lines.append(f"{t['deadline']}: {card.decision.deadline.isoformat()}")
    conf = f"{t['confidence']}: {t[card.confidence.level.value]}"
    if card.confidence.interval:
        iv = card.confidence.interval
        conf += f" · {iv.lower:g}–{iv.upper:g} {iv.unit} ({iv.level:.0%})"
    lines.append(conf)
    lines.append("")
    lines.append(f"## {t['why']}")
    for ev in card.evidence:
        lines.append(f"- {ev.statement} [{', '.join(ev.call_ids)}]")
    if card.cost_of_waiting:
        cw = card.cost_of_waiting
        lines.append("")
        lines.append(f"## {t['cost']}")
        lines.append(f"| {t['days']} | {cw.metric} ({cw.unit}) |")
        lines.append("|---|---|")
        for p in cw.points:
            lines.append(f"| {p.delay_days} | {p.value:g} |")
        lines.append(cw.summary)
    lines.append("")
    lines.append(f"## {t['trust']}")
    lines.append(f"**{t['not_modelled']}:** " + "; ".join(card.trust.not_modelled))
    lines.append(f"**{t['ask_expert']}:** " + "; ".join(card.trust.ask_expert_if))
    lines.append("")
    lines.append(f"## {t['receipt']}")
    for c in card.receipt:
        version = f", {c.data_version}" if c.data_version else ""
        lines.append(f"- `{c.id}` **{c.tool}** v{c.tool_version} → {c.data_source}{version}")
    if card.follow_up:
        fu = card.follow_up
        tool = f" (`{fu.tool}`)" if fu.tool else ""
        lines.append("")
        lines.append(f"## {t['follow_up']}")
        lines.append(f"{fu.check_on.isoformat()}: {fu.method}{tool}")
    return "\n".join(lines) + "\n"
