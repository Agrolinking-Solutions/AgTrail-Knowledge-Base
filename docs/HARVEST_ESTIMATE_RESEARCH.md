# Harvest estimate: where the numbers come from

Researched 25 Oct 2026. Seven crops have an estimate: maize, rice, cassava, soybean, cocoa, groundnut, sorghum.
Every other crop answers "no current research recorded yet" and gets no figure.

## What each number is
- **Typical** is Nigeria's national average yield for 2024 from FAOSTAT (FAO, Production: Crops and livestock products), read through Our World in Data. The 1961 to 2024 series was downloaded and the 2020 to 2024 low and high are stored beside it.
- **Normal range** is the standard range the crop's yield checks already use: the CEO's ruleset (maize 0.8 to 5.0, rice 1.0 to 6.0, cassava 5 to 30, cocoa 0.1 to 1.5, groundnut 0.5 to 2.5, sorghum 0.5 to 2.5). The CEO's ruleset has no soybean section, so soybean uses 0.7 to 3.0, taken from IITA figures. The estimate and the yield validation therefore never disagree about what is normal.
  **High end cap (CEO decision, 25 Oct 2026):** the high end is the ruleset's best case capped at twice the typical yield, so the range stays close to what farms really get. The ruleset figure is kept as `ruleset_high`. Cassava, for example, went from 30 to 11.68 t/ha.
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
