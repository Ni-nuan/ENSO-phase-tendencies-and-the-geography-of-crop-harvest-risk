# Analysis and visualization code

The visualization builders reproduce the main panels from stored numerical results. The analysis modules provide the original implementations or function bodies for inspecting methods; they do not form a complete raw-data-to-paper pipeline.

| Module | Purpose and required inputs |
|---|---|
| [build_fao_crop_panel.py](analysis/build_fao_crop_panel.py) | National FAOSTAT panel from official bulk records and country crosswalk |
| [build_crop_calendar.py](analysis/build_crop_calendar.py) | MIRCA2000/SPAM seasonal weights; requires original spatial products |
| [build_enso_exposure.py](analysis/build_enso_exposure.py) | NOAA RONI and calendar-aligned exposure; requires prepared calendar |
| [yield_distributions.py](analysis/yield_distributions.py) | Distribution metrics over caller-selected valid phase/neutral series |
| [event_history_metrics.py](analysis/event_history_metrics.py) | Direction/magnitude summaries over matched event records |
| [weather_model_functions.py](analysis/weather_model_functions.py) | System/trend adjustment and the original limited-complexity forest fit |
| [conditional_risk_functions.py](analysis/conditional_risk_functions.py) | Trend reference, weighted risk summaries and historical phase shrinkage |

Use [render_main_figures.py](visualization/render_main_figures.py) for the stored-result route. The [figure index](../docs/figure_and_table_index.md) identifies inputs and builders. See [reproducibility](../docs/reproducibility.md) for missing orchestration and raw-data requirements. No downloads or fits occur when importing the extracted analysis functions.
