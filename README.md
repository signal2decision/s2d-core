<p align="center">
  <img src="assets/signal2decision-logo-white.png" alt="Signal2Decision" width="560">
</p>

# s2d-core

**The Decision Card format for Signal2Decision: AI agents that use real crop science.**

Most AI in agriculture answers from memory. Signal2Decision agents answer by running real science (crop models, satellite data, weather, soil) and return every answer as a **Decision Card**: one decision, the evidence behind it, how sure it is, what waiting costs, when not to trust it, and a receipt of every tool call that produced it.

`s2d-core` defines that card and **enforces its honesty rules in code**, so a card that guesses, hides its sources or overstates its confidence cannot be built.

## The honesty rules

| # | Rule | What the code does |
|---|---|---|
| 1 | **Receipts, not guesses** | Every evidence item and the cost-of-waiting block must cite a tool call in the receipt |
| 2 | **No confident guessing** | A low-confidence card must have status `uncertain` |
| 3 | **Always state limits** | Every card must list what the tools don't model and when to ask a local expert |
| 4 | **Acting needs a deadline** | Status `act` requires a deadline on or after the issue date |
| 5 | **IDs match crops** | `S2D-WHT-0001` must be a wheat card, `S2D-MAZ-0001` a maize card |

## Install

```bash
pip install -e ".[dev]"
```

## Use

```python
from s2d import DecisionCard, to_markdown

card = DecisionCard.model_validate_json(open("examples/S2D-WHT-0001.json").read())
print(to_markdown(card))
```

Command line:

```bash
s2d validate examples/*.json          # check cards against the honesty rules
s2d render examples/S2D-WHT-0001.json
s2d schema > schema/decision-card-0.1.0.json
```

## Card anatomy

1. **Question:** place, crop, date
2. **Decision:** `act`, `wait` or `uncertain`, with an action and deadline
3. **Confidence:** level, range and its basis
4. **Evidence:** up to five statements, each linked to receipt calls
5. **Cost of waiting:** only when a tool computed it
6. **Trust:** what isn't modelled; when to ask an expert
7. **Receipt:** every tool call, its inputs, data source and version
8. **Follow-up:** when and how the result will be checked (an agent follows through)
9. **Outcome:** filled in later, when someone reports what happened

The JSON Schema is in [`schema/`](schema/), so tools in any language can produce valid cards.

## Crops

Wheat (`WHT`) and maize (`MAZ`) at launch; rice, potato, sorghum, soybean and millet are reserved for later releases.

## Status

Version 0.1.0. The example card is **illustrative**: its numbers show the format, not a real result.

## Cite

See [`CITATION.cff`](CITATION.cff).

## Licence

MIT © Arshad Abbas
