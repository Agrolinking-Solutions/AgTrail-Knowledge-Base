# Reconciling the crop files with the master ruleset

The source is the AgTrail Master Agronomist & Validator Ruleset (Agrolinking Solutions Ltd., July 2026), 23 crops.
Checked on 24 Oct 2026. Sorghum, pearl millet and vitamin A cassava were written from it directly and match.

## Yield limits (done)
- Added, because the file had none: rice, cassava, cocoa.
- Replaced, because the earlier numbers came from general or global sources and not the ruleset: sweet potato (ofsp), cowpea.
- Every crop file now has yield limits (a test keeps it that way).

### Gaps the ruleset leaves, filled by the files (needs the agronomist's OK)
The ruleset often states "Pass a to b" and "warn above c" with c greater than b. The files extend the Pass band to c, so no yield falls in an undefined range. This applies to maize-style tables in: sorghum, pearl millet, rice, ofsp, cowpea, yam, ginger, groundnut, sesame, tomato, pepper, onion, cotton, hibiscus, cashew, coffee. Lower edges differ by a small step in ginger (4 vs 5) and hibiscus (0.2 vs 0.3), also gap fills.
The ruleset has no zero-yield row for many crops. Every file treats 0 t/ha as a loss event, as a platform rule.

## Timing rules (reconciled 25 Oct 2026)
Every crop's hard-block and flag sentences in the ruleset were compared with the file's rules, one by one.

| Crop | Result |
|---|---|
| maize, rice, yam, groundnut, tomato, pepper, onion, hibiscus | already matched |
| sesame, oil palm, cashew, rubber, coffee, ginger | already matched (the expressible rules; see "Cannot be expressed") |
| cassava | changed: planting flagged (not blocked) beyond 45 days after land prep; added hard blocks for first weeding before 14 days, fertilizer before 21 or after 90 days, processing more than 4 days after harvest |
| sweet potato (ofsp) | changed: weeding and earthing-up flagged after 45 days and blocked after 60; harvest blocked only before 75 days and flagged before 85 or after 130 (was 90-150, block after 180) |
| cowpea | changed: harvest blocked before 60 days (was 55) and not after 120; flagged before 70 or after 100; added an insecticide operation (block before 21 days, flag outside 30-60) and "storage needs a drying step, flagged after 7 days" |
| cocoa | changed: nursery blocked over 180 days (was 210) and flagged under 100 or over 150; first harvest blocked before 540 days (was 730) and flagged before 730; fermentation blocked under 3 or over 10 days and flagged under 4 or over 8 |
| cotton | added the thinning rule (flag after 21 days) |
| vitamin A maize | now follows maize, as section 23 says: planting is flagged (was blocked) beyond 30 days after land prep, and the first fertilizer, weeding, second fertilizer, scouting, harvest-window, fresh-harvest and drying rules were added or set to maize's numbers |

Rule differences that were not in the ruleset but were kept as the file's own choices: cassava second weeding (56-84 days), cassava land prep within 45 days of clearing, ofsp weeding lower flag (14 days) and earthing-up lower flag (30 days), cocoa nursery gating, fermentation within 2 days of harvest, and cocoa weeding and pruning sequence flags.

### Cannot be expressed by the engine (recorded here only)
- Anything about how long one step lasts when there is no later step to measure it against: sun-drying cocoa for 7-10 days (flag over 14), drying cashew nuts 2-3 days (flag under 2), drying ginger 5-8 days (flag under 5), sun-drying vitamin A maize for more than 10 days.
- "Soft warning if X is not logged" for cotton bollworm scouting between 45 and 90 days after planting, and for mulching ginger by 14 days (the engine only checks a step that was logged).
- Harvest bunch interval limits are in the file and match.

### Decision still needed: cassava harvest
The file blocks harvest before 240 days with no maximum, chosen on purpose by the earlier author. The ruleset (section 5) blocks harvest before 180 days and after 730 days, and flags before 270 or after 450. Changing the block to follow the ruleset is one edit to cassava_r6, and the vitamin A cassava file already uses the ruleset numbers. The CEO should say which applies to ordinary cassava.

### For the CEO's attention: cocoa first harvest
The earlier file blocked a first cocoa harvest before 730 days after transplanting and said the choice was deliberate. The ruleset blocks before 540 days and only flags before 730, so a harvest at 18 months (547 days) is now allowed with a flag. The ruleset was followed.
