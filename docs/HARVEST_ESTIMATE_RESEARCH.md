# Harvest estimate: where the numbers come from

Researched 25 Oct 2026. Seven crops have an estimate: maize, rice, cassava, soybean, cocoa, groundnut, sorghum.
Every other crop answers "no current research recorded yet" and gets no figure.

## What each number is
- **Typical** is Nigeria's national average yield for 2024 from FAOSTAT (FAO, Production: Crops and livestock products), read through Our World in Data. The 1961 to 2024 series was downloaded and the 2020 to 2024 low and high are stored beside it.
- **Normal range** is the standard range the crop's yield checks already use: the CEO's ruleset (maize 0.8 to 5.0, rice 1.0 to 6.0, cassava 5 to 30, cocoa 0.1 to 1.5, groundnut 0.5 to 2.5, sorghum 0.5 to 2.5). The CEO's ruleset has no soybean section, so soybean uses 0.7 to 3.0, taken from IITA figures. The estimate and the yield validation therefore never disagree about what is normal.
  **High end cap (CEO decision):** the high end is the ruleset's best case capped at 1.5 times the typical yield, so the range stays close to what farms really get. The ruleset figure is kept as `ruleset_high`. It was twice the typical yield from 25 to 28 Oct 2026; on 28 Oct the CEO said 1.5 times is right, and that cassava should come out at about 8 to 10 t/ha (it is now 8.76). Cassava went from 30 (the ruleset's best case) to 8.76 t/ha.
- **Harvest window** is the expected window in the crop's own timing rules. Rice is counted from transplanting, the others from planting. Cocoa is perennial and has no window.

## What was opened and checked
| Source | Result |
|---|---|
| FAOSTAT via Our World in Data, one page per crop | Opened and downloaded. Used. |
| IITA news item on soybean (4 April 2020) | Opened. Says current average yields of the developed varieties are 0.8 to 1.2 t/ha. Used for soybean. |
| Africa Climate Reports, 3 Nov 2025 | Opened. Says Nigeria's cassava average is "about 10 t/ha" but cites no source. **Not used.** |
| PwC maize report, AfDB country compact | Access refused (403). Not used. |
| IITA guide to rice in northern Nigeria | The link was dead (404). Not used. |
| Frontiers 2025 cocoa paper | The PDF could not be read. Not used. |
| Search-result snippets (cocoa 350 to 400 kg/ha, rice 2.0 to 3.0, improved maize hybrids 3.5 and more) | Not opened. Not used. |

## What the research changed
The earlier "expected yield" figures were higher than current national figures for three crops: cassava (10 to 15 against 5.84), cocoa (0.3 to 1.2 against 0.27) and rice (2.5 to 4.0 against 2.00). They were replaced. The old figures are kept in each file's notes as the record of what was replaced.

## Limits
- National averages hide how much farms differ. A single farm can be well outside the typical figure, which is why the normal range is shown with it.
- FAO's figures for Nigeria are compiled from national reports and FAO estimates, and they move little from year to year (rice stayed between 1.86 and 2.08 over ten years).
- No published farm-by-farm spread for Nigeria was found. The place to get one is the World Bank's Nigeria General Household Survey Panel (2023 to 2024 wave), which has plot area and harvest quantities. That needs a registered download and would let the normal range be measured instead of taken from the ruleset.
- Rice is paddy, and PIS prices milled rice: no naira value is given for rice until a milling factor is sourced. Cassava has no price series.
- Tomato was left out: the national figure swings from 3.4 to 7.6 t/ha across ten years, which is too unstable. Yam, cowpea and the other crops had no current figure.

## To refresh (once a year, after FAOSTAT publishes a new year)
Download `https://ourworldindata.org/grapher/<crop>-yields.csv?v=1&csvType=full&useColumnShortNames=true`, keep the Nigeria rows, update `typical`, `national_recent_low`, `national_recent_high` and `as_of` in each crop's `harvest_estimate`, and bump the file's version.

## Soil research (26 Oct 2026)

The estimate compares a farm's recorded soil with what the crop prefers. Only a soil the crop file says the crop does badly on (`texture_avoid`) changes a number: the high end is held at the typical yield. An avoid entry needs a source that was opened.

**Added**
- Groundnut avoids clay loam, sandy clay and clay. Source: ARC Grain Crops Institute (South Africa), "Groundnut production: a concise guide" by AJ Cilliers, as published in Farmer's Weekly, 16 Dec 2017. The topsoil should have under 20% clay so the pegs can penetrate, and a high clay content may break the pegs at harvest. One source from outside Nigeria.
- Cocoa prefers clay loam and sandy clay loam in addition to loam and sandy loam. Source: Yara, "Soils, liming and salinity in cocoa production": sandy clay loam to clay loam soils are the most productive.
- Soybean avoids sand (from the existing soybean note).

**Looked at and not used**
- Maize: the IITA land preparation procedure treats sandy soil as workable; Nigerian suitability studies name fertility and climate, not texture, as the main limits. No avoid.
- Cassava: a search summary said an IITA farming guide calls sandy and clayey soils "not the most suitable", but the IITA document link (Starting_a_cassava_farm.pdf) returned 404 and a second CGIAR page did not resolve, so it was not confirmed. No avoid.
- Rice: a Nigerian flood-plain suitability paper (FUDMA Journal of Agriculture and Agricultural Technology, June 2022) was opened. It rates the studied soils suitable and says nothing against sandy soil. No avoid.
- Sorghum: sources disagree (one pot study found sandy loam best and sandy clay least suitable; guides say sorghum tolerates heavy clay). Not opened in full. No avoid.

**To get further:** the better route is AgTrail's own harvest results grouped by soil, which would measure the effect instead of reading it from foreign guides.

## Yam, tomato and pepper (27 Oct 2026)

Three more crops have an estimate: **yam 8.15 t/ha** (fresh tubers), **tomato 4.53** (fresh fruit) and **pepper 7.37** (green fruit, added up over the whole harvest period).

**Source:** FAOSTAT, Production: Crops and livestock products, bulk download for Africa (`Production_Crops_Livestock_E_Africa.zip`), Nigeria, element Yield, opened and read on 27 Oct 2026. Our World in Data has no page for these crops, and FAOSTAT's data service needs a login, so the public bulk file was used. The file reports yield in kg per hectare.

**How weak the evidence is:** FAO flags the 2024 yield for all three as its own estimate (flag E), not a figure reported by Nigeria. Yam's 2019 figure was official (7.81 t/ha). Tomato moved between 3.4 and 7.6 t/ha in ten years. Pepper is almost flat (7.37 to 7.62 over ten years), which looks modelled. Confidence is 0.5 for yam and 0.4 for tomato and pepper, and each caveat says so.

**Normal range:** the low end and best case come from the CEO's yield checks (yam 5 to 25, tomato 2 to 15, pepper 1 to 10), with the best case capped at twice the typical yield as for the other crops (yam 16.3, tomato 9.06, pepper 10.0).

**Harvest dates:** yam has a window (180 to 270 days after planting, from its timing rules). Tomato, onion and pepper rules give only the earliest sensible harvest (50, 75 and 60 days after transplanting) and no latest date, so no window is invented: the estimate says so (`timing_note`).

**Not added, because the sources disagree:**
- **Dry onion:** FAO's national average is 2.7 t/ha (an estimate), below the CEO's lowest normal yield of 5 t/ha.
- **Sweet potato (and OFSP):** FAO's national average is 2.7 t/ha, below the CEO's lowest normal yield of 4 t/ha for OFSP. A national sweet potato average is also not specific to orange-fleshed varieties.
These stay "no current research recorded yet" until someone reconciles the two, for example with the World Bank farm survey.

## Cap changed to 1.5 times (28 Oct 2026)
CEO decision on the cap I had set at twice the typical yield: 1.5 times is right. New high ends (t/ha): maize 3.04, rice 3.0, cassava 8.76, soybean 1.53, cocoa 0.41, groundnut 1.88, sorghum 1.6, yam 12.23, tomato 6.79, pepper 10.0 (the ruleset's own best case is lower than 1.5 times, so it stays).
