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

## Timing rules (not yet reconciled)
A rough check compared the day numbers in the ruleset's hard-block and warning sentences with each file's rules. Matching, no number missing: maize, rice, yam, groundnut, tomato, pepper, onion, hibiscus.
Ruleset numbers that do not appear in the file, to be checked by hand (some are weeks or months restated as days):

| Crop | Ruleset numbers not in the file |
|---|---|
| cassava | 90, 180, 730 |
| ofsp | 45, 85, 130 |
| ginger | 5 |
| cowpea | 70, 100 |
| sesame | 120 |
| cocoa | 10, 180, 540 |
| oil palm | 8, 18 |
| cashew | 8 |
| rubber | 5, 6, 20, 72, 1800, 2160 |
| coffee | 5, 12 |
| cotton | 21 (the file has only two day numbers, 100 and 110) |
| vitamin A maize | 10 |

### Decision needed: cassava harvest
The file blocks harvest before 240 days and says "deliberately no hard maximum". The ruleset (section 5, also used for vitamin A cassava) blocks harvest before 180 days and after 730 days, and flags it outside 270-450. These disagree. The ruleset is the CEO's document, so it should win unless the earlier choice was deliberate for a reason the CEO accepts.
