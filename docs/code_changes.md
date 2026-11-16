# Code preparation

Public plotting entrypoints retain the original plotting calculations and stored inputs. Changes replace local project locations with repository-relative input and ignored output folders, remove private layout-audit dependencies and select the accepted Figure 4 display rather than its discarded alternatives. Full numerical inputs are preserved; no weather model or risk scenario is refitted by these changes.

The preprocessing modules use an environment-selected data workspace. Analysis function modules retain original function bodies while omitting execution orchestration, local audit writes and document assembly. These excerpts are method implementations, not a replacement end-to-end pipeline. Code syntax and stored-result rendering are checked for this release; raw-data preprocessing and forest fitting are not rerun.
