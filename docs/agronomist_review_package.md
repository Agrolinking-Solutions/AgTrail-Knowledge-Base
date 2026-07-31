# AgTrail Knowledge Base — Agronomist Review Package

**Purpose:** Three crop files (Maize, Cocoa, Cassava) have been built as structured data for a farm-record validation system. They are internally consistent and pass automated schema checks — but "structurally valid" is not the same as "agronomically correct." This document exists so someone who actually knows Nigerian crop production can check the numbers without needing to read JSON.

**How to use this:** Each crop has two sections — **"Needs your eyes first"** (things we've flagged as unsourced, conflicting, or uncertain) and **"Full data for sanity-check"** (everything else, for a general read-through). If something looks wrong, wrong for your region, or is missing entirely, that's exactly the feedback this needs. You don't need to touch the JSON files — notes in any format (marked-up copy of this doc, email, a call) are fine; we'll translate corrections back into the data.

**What "block" and "warning" mean**, since it comes up constantly below: a **block** stops a farmer from submitting a record at all (used for things that should be physically impossible, like harvesting before planting). A **warning** lets the record through but flags it for review (used for things that are unusual but not impossible, like fertilizer applied later than typical). If any block below is too strict for real conditions, or any warning should actually be a block, please say so — getting this split wrong in either direction is a real problem once farmers are using it.

---

## 1. Maize

### Needs your eyes first

| Item | What we have | Why it's flagged |
|---|---|---|
| Second fertilizer (top-dress) timing | Guinea savanna: 28–35 days after planting. Sudan savanna: 21–28 days after planting. | Split by region based on IITA's guide, but we have not confirmed these are the only two zones that matter, or whether other regions (Southwest, Middle Belt, etc.) need their own window. |
| Maize Leaf Blight management | Generic advice (crop rotation, resistant varieties, fungicide) | Not tied to a Nigeria-specific source — this is closer to a placeholder than a verified recommendation. |
| Stem Borer management | Generic advice (field sanitation, timely planting, insecticide) | Same issue — not cross-checked against a Nigeria-specific primary source. |
| Harvest window | Hard block: 80–150 days after planting. Soft/typical: 90–120 days. | The 150-day upper bound came from one source describing "late-maturing varieties" and may be too generous, or not generous enough depending on variety mix actually grown by AgTrail's farmers. |

### Full data for sanity-check

**Lifecycle (days after planting):** Germination 0–7 → Seedling 8–20 → Vegetative 21–50 → Tasseling/Silking 51–65 → Grain fill 66–95 → Maturity 96–105.

**Sequence of operations:** Land clearing → Land preparation → Planting → (optional gap filling) → Basal fertilizer → First weeding → Top-dress fertilizer → (optional second weeding) → (optional pest scouting) → Harvest → Drying → (optional storage).

**Timing rules:**
- Land preparation must follow land clearing (no earlier than 0 days, no more than 30 days after).
- Planting must follow land preparation, within 0–14 days.
- Basal fertilizer: 0–14 days after planting (warning if outside).
- First weeding: 14–21 days after planting (warning if outside).
- Top-dress fertilizer: region-specific, see flagged item above.
- Second weeding: 28–35 days after planting.
- Fall Armyworm control: most effective 0–21 days after planting.
- Harvest: blocked before 80 days or after 150 days; flagged (warning) if outside 90–120 days.
- Only one harvest allowed per planting (a second harvest needs a new planting record).
- Drying should start within 0–10 days of harvest.

**Soil:** pH 5.5–7.0, sandy loam/loam/clay loam, well-drained, high nitrogen needs.

**Diseases:** Maize Streak Virus (leafhopper-transmitted, resistant varieties + vector control). Maize Leaf Blight (flagged above).

**Pests:** Fall Armyworm (weekly spray for first 3 weeks post-planting). Striga — parasitic weed, flagged by IITA as a major constraint (up to 74% infestation in northern Guinea savanna, 30–60% yield loss where present). Stem Borer (flagged above).

**Yield:** 1.2–2.0 t/ha typical smallholder; 2.5–3.5 t/ha (up to ~3+) with recommended practice.

---

## 2. Cassava

### Needs your eyes first

| Item | What we have | Why it's flagged |
|---|---|---|
| Land preparation → planting timing | Land prep within 0–45 days of clearing; planting within 0–21 days of land prep | These intervals were carried over from the maize template as a placeholder — not independently sourced for cassava at all. |
| Fertilizer timing | Window of 28–56 days after planting | Two sources directly conflict: a peer-reviewed IITA field trial applied fertilizer at 4 weeks (28 days); a farmer-facing guide says 8 weeks (56 days). We didn't pick one — need your judgment on which (or whether it varies by circumstance). |
| Cassava Brown Streak Disease (CBSD) | Included, but marked low-confidence | Only one source claims this is significant in Nigeria; our understanding is CBSD is mainly an East/Southern Africa problem. This entry might be wrong and could cause a false alert telling a farmer to destroy a healthy crop — please confirm whether this belongs in the file at all. |
| Rainfall requirements | 1000–1500mm/cycle | General figure, not cross-checked against a Nigeria-cassava-specific source. |
| Single-harvest assumption | Model currently allows only one harvest record per planting | Real cassava harvesting is sometimes staggered/partial across a field over weeks. We simplified this on purpose but flagged it — let us know if this simplification will cause real problems. |

### Full data for sanity-check

**Lifecycle (days after planting):** Sprouting 0–30 → Establishment 31–90 → Canopy closure/root bulking 91–270 → Maturity/in-ground storage 271–550.

**Sequence of operations:** Land clearing → Land preparation (ridging/mounding) → Planting (stem cuttings) → (optional gap filling) → First weeding → (optional fertilizer) → Second weeding → (optional pest/disease control) → Harvest → Processing → (optional storage of processed product).

**Timing rules:**
- First weeding: 21–28 days after planting.
- Fertilizer: see flagged item above.
- Second weeding: 56–84 days after planting (closes out the "critical weed interference period," sourced to 8–12 weeks after planting).
- Harvest: blocked before 240 days (8 months) after planting. **No upper block** — cassava can stay in the ground 12–15+ months without a hard cutoff (this is the one structural feature we specifically wanted your confirmation on — does this match what you see in the field?). Soft/typical window flagged as 270–450 days (9–15 months).
- Processing should start within 0–2 days (48 hours) of harvest, or quality/spoilage risk increases.

**Soil:** pH 5.5–6.5, sandy loam/loam, well-drained, low nitrogen needs (more fertility-tolerant than maize).

**Diseases:** Cassava Mosaic Disease (whitefly-transmitted, 20–90% yield loss depending on severity — use disease-free cuttings, resistant varieties). CBSD flagged above.

**Pests:** Cassava Mealybug (historically controlled via the parasitoid wasp Anagyrus lopezi — worth confirming this biocontrol program's current availability/status). Whitefly (mainly relevant as the CMD vector).

**Yield:** 10–15 t/ha typical smallholder; up to 25+ t/ha with mechanization/improved practice. Nigeria is the world's largest producer by volume but yields are roughly half those of leading Asian producers — poor weed timing is cited as a principal cause, which is part of why the weeding rules above matter more than they might first appear to.

---

## 3. Cocoa

**This file is more provisional than Maize or Cassava** — it hasn't been through a dedicated sourcing pass yet (no `source` field on the timing rules), so treat everything below as a first draft rather than "sourced but flagged."

**Lifecycle:** Nursery (~4 months before field transplanting) → Establishment/immature (0–2 years after transplanting) → Early bearing (2–3 years) → Full bearing (3+ years, recurring for ~25–30 years).

**Sequence of operations:** Land clearing → Nursery establishment → Transplanting → (optional gap filling) → (optional shade management) → Fertilizer → Weeding → Pruning → (optional pest/disease control) → Harvest → Fermentation → Drying.

**Timing rules (all unsourced — please treat every number here as a question, not a claim):**
- Nursery should start within 0–60 days of land clearing (warning only).
- Transplanting: seedlings need 90–150 days in the nursery (block if earlier).
- First fertilizer: no earlier than 30 days after transplanting; repeats indefinitely afterward.
- First harvest: blocked before 730 days (2 years) after transplanting; recurs every season afterward without needing a new planting record — **please confirm this 2-year figure**, since it drives when the whole harvest cycle unlocks.
- Fermentation should start within 0–2 days of harvest.
- Drying should follow 5–7 days of fermentation.

**Soil:** pH 5.5–7.5, loam/sandy loam, deep well-drained soil, medium nitrogen needs.

**Diseases:** Black Pod Disease, Swollen Shoot Virus — both cited only generally to "IITA/CRIN," not to a specific named document.

**Pests:** Capsids/Mirids — same general citation issue.

**Yield:** 0.3–0.8 t/ha (immature/early bearing), 0.6–1.2 t/ha (full bearing) — lowest-confidence number in any of the three files (0.45).

**Bottom line on cocoa:** if you only have time to review one file properly, review Maize or Cassava first — they've already had a sourcing pass and just need verification. Cocoa needs the sourcing pass itself, which is a bigger ask.

---

## What would help most from you

1. Corrections to anything flagged above, in whatever format is easiest.
2. A general read of the "Full data" sections for anything that looks wrong even though we didn't flag it — the flags mark what *we* know is uncertain, not necessarily everything that's wrong.
3. Confirmation (or correction) of the two structural claims we're most relying on: cassava's open-ended harvest window, and cocoa's ~2-year time-to-first-harvest.
4. Whether the block/warning split feels right anywhere — too strict, too loose, or a warning that should really be a hard block (e.g. a fraud-relevant pattern we haven't thought of).
