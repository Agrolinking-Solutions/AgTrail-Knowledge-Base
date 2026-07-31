# AgTrail Crop Knowledge Base — v1 Starter

This is the first working slice of the knowledge base discussed with the tech team: instead of the app "knowing farming" through hardcoded logic or an AI guess, every crop is a data file the Workflow & Validation Engine loads at runtime.

## What's in here

```
knowledge-base/
├── schema.json          ← the contract every crop file must follow
├── crops/
│   ├── maize.json       ← template: annual/staple crop
│   └── cocoa.json       ← template: perennial/tree crop
└── README.md            ← this file
```

**Why two templates, not one:** Maize and Cocoa deliberately stress the schema in opposite directions.

- **Maize** is the simple case: linear workflow, harvest happens once, then the cycle ends (storage). Day 0 is planting.
- **Cocoa** is the hard case: nursery happens *before* field day-zero, the tree doesn't bear for ~2 years, and harvest **repeats every season indefinitely** without a new planting record. If a crop template can handle cocoa correctly, it can handle most other perennials (citrus, oil palm, plantain, etc.) with only parameter changes — no schema changes.

That's the test for whether the schema is genuinely reusable: can you describe a totally different crop lifecycle without touching `schema.json`, only writing a new JSON file? Try sketching cassava or rice next as a gut-check.

## How this maps to the original conversation

| What you and Victor discussed | Where it lives here |
|---|---|
| "Can't plant unless land preparation is done" | `validation_rules` → `depends_on_operation_id`, `severity: "block"` |
| "What's the interval before the next operation" | `validation_rules` → `min_days_after_dependency` / `max_days_after_dependency` |
| "Don't allow backdating" | `validation_rules` → `allow_backdate: false` (global rule at the bottom of each file) + a **global** rule (`operation_id: "*"`) blocking any date earlier than the prior logged operation |
| "Some things should warn, not block" | `severity: "block"` vs `severity: "warning"` |
| "Different crops need different bases" | one JSON file per crop, same schema |
| "AI reasons on top, doesn't invent the rules" | AI reads `workflow` + `validation_rules` + `growth_stages`; it never edits them |

## The severity model, concretely

- **`block`** — physically/logically impossible or fraud-shaped (harvest before planting, second harvest on an annual with no new planting, backdating that reorders the sequence). Reject outright.
- **`warning`** — statistically unusual but not impossible (fertilizer applied 40 days late, harvest slightly outside the typical window). Allow, flag, let AI or an agronomist follow up.

This directly answers the "how do we not just block everything" problem from the transcript — most of the *timing* rules are warnings; only *sequence-breaking* and *impossible-date* rules are blocks.

## Where the actual numbers should come from (Step 5 from before)

Every number I've put in `maize.json` and `cocoa.json` right now (day intervals, pH ranges, disease lists) is a **provisional draft** built from general public agronomic knowledge — not verified against a named source document, and not reviewed by an agronomist. That's flagged in each file's `version_history.summary` on purpose so nobody mistakes draft data for validated data.

Before this goes anywhere near production validation logic, each crop file needs a real review pass against:

1. IITA / CRIN / NIHORT extension guides for the specific crop
2. Federal Ministry of Agriculture recommendations
3. Local agronomists in the actual growing regions (Kaduna maize timing ≠ Cross River maize timing — that's what `regional_overrides` is for)
4. Once you have real farm data: tighten intervals based on what actually happened across your own farmer base, not just literature values

Treat `confidence` fields (in diseases/pests/yield_model) as a literal signal to the AI layer later — low-confidence entries should be phrased more cautiously in farmer-facing messages.

## Suggested next steps, in order

1. **Get one agronomist (or Shade/John's team) to review `maize.json` line by line.** Don't build more crops until one is fully validated — you want to find schema gaps on the *first* crop, not the fifth.
2. **Add a third crop that's neither purely annual nor tree-perennial** — cassava is a good stress test (long single cycle, ~9-12 months, but harvest timing is flexible/staggered rather than a hard window).
3. **Wire `schema.json` into actual JSON Schema validation** in CI, so a malformed crop file can never be merged (e.g. `ajv` in Node, `jsonschema` in Python).
4. **Only after 2-3 crops are validated**, start the Workflow Engine code that loads these files and runs the rule checks — resist writing the engine against a schema that's only been tested with one crop.

## A note on scope

I did not build out the full 10-crop list from the transcript (Maize, Cassava, Rice, Soybean, Cocoa, Sesame, Ginger, Tomato, Pepper, Yam) yet. Two templates are enough to prove the schema works for both major crop shapes; multiplying more crops now, before an agronomist has reviewed the shape itself, means re-doing work if the schema needs to change.
