# Methods overview

## Agricultural anomalies and phase comparisons

Historical yield, area and reported-production anomalies use `100 * (V_t / G_t - 1)`, with `G_t` the centred five-year geometric mean of positive valid values from `t-2` to `t+2`. Anomalies are percentages; differences between anomalies are percentage points (pp). The study retains reporting entities and flags. Majority-neutral is an agricultural exposure category and can include some ENSO contact; it is not an identified no-ENSO counterfactual.

Seasonal weights allocate each positive-area season's area share equally over its active months, then combine seasons by harvest year. Phase assignment requires a uniquely largest share of at least 50%. Event-level maps additionally require one event to have at least 50% and exceed any other event, with no opposite-phase exposure. Event means use complete qualified sets of harvest years. See [Table 16](../results/supplementary_tables/Table_16/) for event and system support.

## Event variation and agricultural environments

Complete-event omission checks whether phase-contrast direction persists. A contrary event is at least 2 pp on the opposite side of the majority-neutral mean. Historical severe low yield means a yield anomaly ≤−10%. Environmental groups use climate, crop-season and irrigation conditions independently of yield outcomes. Strong-minus-ordinary event contrasts and early/late model-share changes use separately qualified cohorts, including the distinct wheat comparisons in Figure 3.

## Weather models

The historical model removes system intercepts and trends and fits residual yield variation with a forest using precipitation, temperature, VPD, soil moisture, radiation and agricultural context. TreeSHAP allocates fitted output among predictors. Signed five-weather contributions sum the five weather terms (pp); full fitted outputs also contain expected value, system/trend and non-weather contributions. Relative shares allocate the sum of mean absolute weather contributions (%). Changing shares within the same fitted model describes changes in how that model represents historical records, not independent physiological effects. The final model covers 459 systems and 16,990 agricultural years.

## Production outcomes

Independent historical Y/A/Q anomaly references do not form an additive percentage identity. The common production accounting instead uses `Q - Y0*A0 = (Y-Y0)*A0 + Y*(A-A0) + (Q-Y*A)`: fixed-area yield contribution, area including its interaction with yield, and reporting difference. Coverage of actual world production and fixed reference production shares are separate denominators. Fixed shares use 2012–2020 means and are normalized only within a stated eligible group.

## Conditional 2027 risk

Severe low yield here means ≤−10% relative to a separate pre-issue trend reference, not historical MA5. A two-parameter trend uses the last ten calendar years available under the agricultural lag, with at least eight valid values. Historical residual distributions are mixed with the dated traditional Niño3.4 phase probabilities. Phase histories shrink toward all-history weights using six equivalent observations; sensitivity settings are not chosen by scores. When only El Niño probability is specified, residual neutral/La Niña allocation produces bounds, not a chosen midpoint or a confidence interval. Weighted system bounds need not be jointly attainable under one season-consistent allocation. A probability change over reference production is not a prediction of future production tonnage.
