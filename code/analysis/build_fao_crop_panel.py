"""Build the locked four-crop FAOSTAT panel and non-destructive QC outputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


import os
ROOT = Path(os.environ.get('ENSO_DATA_ROOT', Path(__file__).resolve().parents[2]))
SOURCE = ROOT / "data/raw/agriculture/faostat_production/extracted/Production_Crops_Livestock_E_All_Data_(Normalized).csv"
COUNTRY = ROOT / "data/metadata/country_crosswalk.csv"
OUTPUT = ROOT / "data/intermediate/agriculture_panel/fao_crop_panel.parquet"
CONSISTENCY = ROOT / "outputs/diagnostics/faostat_production_consistency.csv"
SUMMARY = ROOT / "outputs/diagnostics/faostat_panel_qc_summary.md"
ITEMS = {56: "MAIZE", 15: "WHEAT", 27: "RICE", 236: "SOY"}
ELEMENTS = {"Yield", "Area harvested", "Production"}


def load_source() -> tuple[pd.DataFrame, int]:
    columns = ["Area Code", "Area", "Item Code", "Item", "Element", "Year", "Unit", "Value", "Flag", "Note"]
    parts: list[pd.DataFrame] = []
    for chunk in pd.read_csv(SOURCE, usecols=columns, chunksize=300_000, low_memory=False):
        chunk = chunk[
            chunk["Item Code"].isin(ITEMS)
            & chunk["Element"].isin(ELEMENTS)
            & chunk["Year"].between(1961, 2024)
        ].copy()
        parts.append(chunk)
    frame = pd.concat(parts, ignore_index=True)
    duplicate_rows = int(frame.duplicated(["Area Code", "Item Code", "Year", "Element"], keep=False).sum())
    return frame, duplicate_rows


def element_frame(source: pd.DataFrame, element: str, prefix: str) -> pd.DataFrame:
    selected = source[source["Element"] == element].copy()
    selected = selected.drop_duplicates(["Area Code", "Item Code", "Year", "Element"], keep="first")
    return selected[["Area Code", "Item Code", "Year", "Value", "Unit", "Flag"]].rename(columns={
        "Value": f"{prefix}_fao_raw",
        "Unit": f"{prefix}_unit_raw",
        "Flag": f"fao_{prefix}_flag",
    })


def build_panel() -> tuple[pd.DataFrame, int, int]:
    source, duplicate_rows = load_source()
    keys = source[["Area Code", "Area", "Item Code", "Item", "Year"]].drop_duplicates()
    for element, prefix in (("Yield", "yield"), ("Area harvested", "area"), ("Production", "production")):
        keys = keys.merge(element_frame(source, element, prefix), on=["Area Code", "Item Code", "Year"], how="left", validate="one_to_one")

    crosswalk = pd.read_csv(COUNTRY)
    fao_map = crosswalk[
        (crosswalk["source"] == "FAOSTAT")
        & crosswalk["status"].isin(["matched", "historical_entity"])
    ][["fao_area_code", "iso3", "country_standard", "status"]].drop_duplicates("fao_area_code")
    fao_map["fao_area_code"] = pd.to_numeric(fao_map["fao_area_code"], errors="coerce").astype("Int64")
    keys["Area Code"] = keys["Area Code"].astype("Int64")
    panel = keys.merge(fao_map, left_on="Area Code", right_on="fao_area_code", how="left", validate="many_to_one")
    excluded_unmapped = int(panel["iso3"].isna().sum())
    panel = panel[panel["iso3"].notna()].copy()
    panel["crop"] = panel["Item Code"].map(ITEMS)
    panel["harvest_year"] = panel["Year"].astype(int)
    panel["country"] = panel["country_standard"]

    panel["yield_t_ha"] = np.where(
        panel["yield_unit_raw"] == "kg/ha", panel["yield_fao_raw"] / 1000.0,
        np.where(panel["yield_unit_raw"] == "t/ha", panel["yield_fao_raw"], np.nan),
    )
    panel["area_ha"] = np.where(panel["area_unit_raw"] == "ha", panel["area_fao_raw"], np.nan)
    panel["production_t"] = np.where(panel["production_unit_raw"] == "t", panel["production_fao_raw"], np.nan)
    panel = panel.rename(columns={"area_fao_raw": "area_harvested_fao_raw"})
    panel["production_calc"] = panel["yield_t_ha"] * panel["area_ha"]
    panel["production_gap"] = panel["production_t"] - panel["production_calc"]
    panel["production_gap_pct"] = np.where(
        panel["production_t"].abs() > 0,
        panel["production_gap"] / panel["production_t"] * 100.0,
        np.nan,
    )
    panel["flag_production_inconsistent"] = np.where(
        panel["production_gap_pct"].notna(),
        (panel["production_gap_pct"].abs() > 5.0).astype(int),
        pd.NA,
    )
    upper = panel.groupby("crop")["yield_t_ha"].transform(lambda series: series.quantile(0.999))
    panel["flag_yield_extreme"] = ((panel["yield_t_ha"] > upper) & panel["yield_t_ha"].notna()).astype(int)
    panel["flag_country_historical_entity"] = (panel["status"] == "historical_entity").astype(int)

    columns = [
        "iso3", "country", "crop", "harvest_year",
        "yield_fao_raw", "yield_unit_raw", "area_harvested_fao_raw", "area_unit_raw",
        "production_fao_raw", "production_unit_raw", "yield_t_ha", "area_ha", "production_t",
        "fao_yield_flag", "fao_area_flag", "fao_production_flag",
        "production_calc", "production_gap", "production_gap_pct", "flag_production_inconsistent",
        "flag_yield_extreme", "flag_country_historical_entity",
    ]
    panel = panel[columns].sort_values(["iso3", "crop", "harvest_year"]).reset_index(drop=True)
    return panel, duplicate_rows, excluded_unmapped


def write_summary(panel: pd.DataFrame, duplicate_source_rows: int, excluded_unmapped: int) -> None:
    key_duplicates = int(panel.duplicated(["iso3", "crop", "harvest_year"]).sum())
    nonpositive = {
        "yield": int((panel["yield_t_ha"] <= 0).sum()),
        "area": int((panel["area_ha"] <= 0).sum()),
        "production": int((panel["production_t"] <= 0).sum()),
    }
    missing = panel[["yield_t_ha", "area_ha", "production_t"]].isna().sum().to_dict()
    inconsistent = int((panel["flag_production_inconsistent"] == 1).sum())
    extreme = int(panel["flag_yield_extreme"].sum())
    coverage = panel.groupby("crop")["iso3"].nunique().to_dict()
    annual = panel.groupby("harvest_year").size()
    flags = {
        column: panel[column].fillna("MISSING").value_counts().to_dict()
        for column in ("fao_yield_flag", "fao_area_flag", "fao_production_flag")
    }
    gaps = []
    for (iso3, crop), group in panel.groupby(["iso3", "crop"]):
        years = sorted(group.loc[group[["yield_t_ha", "area_ha", "production_t"]].notna().any(axis=1), "harvest_year"].unique())
        if years:
            missing_years = len(set(range(min(years), max(years) + 1)) - set(years))
            if missing_years:
                gaps.append((iso3, crop, missing_years))
    lines = [
        "# FAOSTAT Panel QC Summary",
        "",
        f"- Rows: {len(panel):,}",
        f"- Countries/entities: {panel['iso3'].nunique()}",
        f"- Period: {panel.harvest_year.min()}-{panel.harvest_year.max()}",
        f"- Key duplicates (`iso3 × crop × harvest_year`): {key_duplicates}",
        f"- Duplicate source metric rows before pivot: {duplicate_source_rows}",
        f"- Excluded aggregate/unmapped source rows: {excluded_unmapped:,}",
        f"- Missing standardized values: {missing}",
        f"- Non-positive values (retained): {nonpositive}",
        f"- Production consistency flags (`abs(gap_pct) > 5%`, retained): {inconsistent:,}",
        f"- Crop-specific upper 0.1% yield flags (retained): {extreme:,}",
        f"- Country/entity coverage by crop: {coverage}",
        f"- Annual row count range: {int(annual.min())}-{int(annual.max())}",
        f"- Country-crop series with internal time gaps: {len(gaps)}",
        f"- FAOSTAT flag distributions: {flags}",
        "",
        "No estimated, imputed, unofficial, non-positive, extreme, or inconsistent record was deleted.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    panel, duplicate_source_rows, excluded_unmapped = build_panel()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CONSISTENCY.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUTPUT, index=False)
    consistency_columns = [
        "iso3", "country", "crop", "harvest_year", "yield_t_ha", "area_ha", "production_t",
        "production_calc", "production_gap", "production_gap_pct", "flag_production_inconsistent",
    ]
    panel[consistency_columns].to_csv(CONSISTENCY, index=False, encoding="utf-8-sig")
    write_summary(panel, duplicate_source_rows, excluded_unmapped)
    duplicate_keys = int(panel.duplicated(["iso3", "crop", "harvest_year"]).sum())
    print(f"panel_rows={len(panel)} countries={panel.iso3.nunique()} duplicate_keys={duplicate_keys} inconsistent={(panel.flag_production_inconsistent == 1).sum()}")


if __name__ == "__main__":
    main()
