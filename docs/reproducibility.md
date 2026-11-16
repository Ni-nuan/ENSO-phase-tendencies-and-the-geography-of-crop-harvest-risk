# Reproducibility scope

## Stored results and main figures

All six main figure builders read the included source tables (and the public-domain basemap). Run `python code/visualization/render_main_figures.py` from the repository root after installing `requirements.txt`. They write only to ignored `build/` subfolders. Figure 4's accepted ellipse/median/IQR display is regenerated; unused alternative designs are not run. Numerical results are not refitted. Previews in `figures/` remain the original accepted images; font availability and library versions can change rendered typography.

## Raw-data preparation

The three preprocessing modules read official agricultural, calendar and ENSO products from a data workspace. `ENSO_DATA_ROOT` selects this workspace; the default is the repository root. Obtain the files declared near the top of each module, retain the exact product versions and populate the country crosswalk. Raw gridded data and large agricultural bulk downloads are not bundled. Some preprocessing writes diagnostic files under that external workspace; do not point it at a read-only archive. These modules are source implementations, not a promise that raw downloads alone reconstruct all final qualifications.

## Analysis functions and computational work

Original functions are provided for historical distribution summaries, retrospective event comparisons, the trend/distribution/phase-shrinkage calculations and the system/trend plus forest fit. Their scientific function bodies are retained; callers must supply qualified, matched inputs. These functions are not a newly constructed full analysis pipeline. Forest fitting and global weather aggregation can be expensive and were not rerun to assemble this release.

The full extraction of gridded products, final physical-event qualification, model/TreeSHAP job orchestration, every sensitivity refit and supplementary plotting workflow are not independently reconstructed here. The release supplies complete result tables so readers can inspect their numerical evidence without obtaining all raw products. Supplementary previews are rasterized from the accepted one-page PDFs, not regenerated analytical plots.

The dated 2027 risk results remain tied to information available by 8 November 2026. Calling a live provider URL or substituting later statistics would define a different application. Historical replay, event deletion and reliability diagnostics remain supplementary evidence and do not certify local forecast skill.
