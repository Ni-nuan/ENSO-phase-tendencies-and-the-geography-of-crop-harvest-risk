"""Build fixed-baseline country-crop-season calendars from MIRCA2000."""

from __future__ import annotations

import gzip
import io
import zipfile
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd


import os
ROOT = Path(os.environ.get('ENSO_DATA_ROOT', Path(__file__).resolve().parents[2]))
MIRCA_ZIP = ROOT / "data/raw/crop_calendar/mirca2000/growing_periods_listed.zip"
SPAM_CSV = ROOT / "data/raw/crop_distribution/spam2020/extracted/harvested_area_csv/spam2020V2r2_global_harvested_area/spam2020V2r2_global_H_TA.csv"
SACKS_DIR = ROOT / "data/raw/crop_calendar/sacks"
CROSSWALK = ROOT / "data/metadata/country_crosswalk.csv"
OUT = ROOT / "data/intermediate/crop_calendars/crop_calendar_country_crop.parquet"
SUMMARY_OUT = ROOT / "data/intermediate/crop_calendars/crop_calendar_country_crop_summary.parquet"
QC_OUT = ROOT / "outputs/diagnostics/crop_calendar_qc.csv"

CROPS = {1: "WHEAT", 2: "MAIZE", 3: "RICE", 8: "SOY"}
SPAM_COLS = {"WHEAT": "whea", "MAIZE": "maiz", "RICE": "rice", "SOY": "soyb"}
SACKS_FILES = {
    "MAIZE": [("main", "Maize.crop.calendar.nc.gz"), ("second", "Maize.2.crop.calendar.nc.gz")],
    "WHEAT": [("spring", "Wheat.crop.calendar.nc.gz"), ("winter", "Wheat.Winter.crop.calendar.nc.gz")],
    "RICE": [("main", "Rice.crop.calendar.nc.gz"), ("second", "Rice.2.crop.calendar.nc.gz")],
    "SOY": [("main", "Soybeans.crop.calendar.nc.gz")],
}


def grid_indices(lon: pd.Series, lat: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    col = np.floor((lon.to_numpy() + 180.0) * 2.0 + 1e-6).astype(int) + 1
    row = np.floor((90.0 - lat.to_numpy()) * 2.0 + 1e-6).astype(int) + 1
    return np.clip(row, 1, 360), np.clip(col, 1, 720)


def build_spam_cell_map() -> tuple[pd.DataFrame, pd.DataFrame]:
    crosswalk = pd.read_csv(CROSSWALK)
    spam_iso = (
        crosswalk[crosswalk["source"] == "SPAM2020"]
        .drop_duplicates("source_name")
        .set_index("source_name")["iso3"]
        .to_dict()
    )
    crop_parts: list[pd.DataFrame] = []
    any_parts: list[pd.DataFrame] = []
    columns = ["x", "y", "FIPS0", "ADM0_NAME", *SPAM_COLS.values()]
    for chunk in pd.read_csv(SPAM_CSV, usecols=columns, chunksize=150_000, low_memory=False):
        row, col = grid_indices(chunk["x"], chunk["y"])
        chunk["row"] = row
        chunk["column"] = col
        chunk["iso3"] = chunk["ADM0_NAME"].map(spam_iso)
        chunk = chunk[chunk["iso3"].notna()].copy()
        chunk["any_area"] = chunk[list(SPAM_COLS.values())].sum(axis=1)
        any_parts.append(chunk.groupby(["row", "column", "iso3"], as_index=False)["any_area"].sum())
        for crop, column in SPAM_COLS.items():
            part = chunk.loc[chunk[column] > 0, ["row", "column", "iso3", column]].copy()
            part["crop"] = crop
            part = part.rename(columns={column: "spam_area"})
            crop_parts.append(part.groupby(["row", "column", "iso3", "crop"], as_index=False)["spam_area"].sum())

    crop_area = pd.concat(crop_parts, ignore_index=True).groupby(["row", "column", "iso3", "crop"], as_index=False)["spam_area"].sum()
    crop_dom = crop_area.sort_values("spam_area", ascending=False).drop_duplicates(["row", "column", "crop"])
    any_area = pd.concat(any_parts, ignore_index=True).groupby(["row", "column", "iso3"], as_index=False)["any_area"].sum()
    any_dom = any_area.sort_values("any_area", ascending=False).drop_duplicates(["row", "column"])
    return crop_dom, any_dom


def read_mirca() -> pd.DataFrame:
    member = "growing_periods_listed/CELL_SPECIFIC_CROPPING_CALENDARS_30MN.TXT.gz"
    with zipfile.ZipFile(MIRCA_ZIP) as archive, archive.open(member) as compressed:
        with gzip.GzipFile(fileobj=compressed) as stream:
            frame = pd.read_csv(stream, sep="\t")
    frame["base_crop"] = ((frame["crop"] - 1) % 26) + 1
    frame = frame[frame["base_crop"].isin(CROPS)].copy()
    frame["crop_standard"] = frame["base_crop"].map(CROPS)
    frame["water_system"] = np.where(frame["crop"] <= 26, "irrigated", "rainfed")
    return frame


def day_to_month(values: np.ndarray) -> np.ndarray:
    boundaries = np.cumsum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    return np.searchsorted(boundaries, values, side="left") + 1


def sacks_reference(crop_dom: pd.DataFrame) -> pd.DataFrame:
    references: list[pd.DataFrame] = []
    for crop, variants in SACKS_FILES.items():
        weights = crop_dom[crop_dom["crop"] == crop][["row", "column", "iso3", "spam_area"]]
        for variant, filename in variants:
            raw = gzip.open(SACKS_DIR / filename, "rb").read()
            with netCDF4.Dataset("inmemory.nc", memory=raw) as dataset:
                plant = np.ma.filled(dataset.variables["plant"][:], np.nan)
                harvest = np.ma.filled(dataset.variables["harvest"][:], np.nan)
            valid = np.isfinite(plant) & np.isfinite(harvest) & (plant > 0) & (harvest > 0)
            rr, cc = np.where(valid)
            values = pd.DataFrame({
                "row": rr + 1,
                "column": cc + 1,
                "plant_month": day_to_month(plant[valid]),
                "harvest_month": day_to_month(harvest[valid]),
            }).merge(weights, on=["row", "column"], how="inner")
            if values.empty:
                continue
            grouped = values.groupby(["iso3", "plant_month", "harvest_month"], as_index=False)["spam_area"].sum()
            dominant = grouped.sort_values("spam_area", ascending=False).drop_duplicates("iso3")
            dominant["crop_standard"] = crop
            dominant["sacks_variant"] = variant
            references.append(dominant)
    return pd.concat(references, ignore_index=True)


def month_distance(a: int, b: int) -> int:
    difference = abs(int(a) - int(b))
    return min(difference, 12 - difference)


def month_sequence(start: int, end: int) -> list[int]:
    if start <= end:
        return list(range(start, end + 1))
    return list(range(start, 13)) + list(range(1, end + 1))


def build_calendar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    crop_dom, any_dom = build_spam_cell_map()
    mirca = read_mirca()
    crop_map = crop_dom[["row", "column", "crop", "iso3"]].rename(columns={"crop": "crop_standard", "iso3": "iso3_crop"})
    general_map = any_dom[["row", "column", "iso3"]].rename(columns={"iso3": "iso3_any"})
    mirca = mirca.merge(crop_map, on=["row", "column", "crop_standard"], how="left")
    mirca = mirca.merge(general_map, on=["row", "column"], how="left")
    mirca["iso3"] = mirca["iso3_crop"].fillna(mirca["iso3_any"])
    total_area = float(mirca["area"].sum())
    assigned_area = float(mirca.loc[mirca["iso3"].notna(), "area"].sum())
    mirca = mirca[mirca["iso3"].notna() & (mirca["area"] > 0)].copy()

    pair_area = mirca.groupby(["iso3", "crop_standard", "subcrop", "start", "end"], as_index=False)["area"].sum()
    dominant = pair_area.sort_values("area", ascending=False).drop_duplicates(["iso3", "crop_standard", "subcrop"])
    dominant = dominant.rename(columns={"area": "dominant_pair_area", "start": "plant_month", "end": "harvest_month"})
    season_area = mirca.groupby(["iso3", "crop_standard", "subcrop"], as_index=False)["area"].sum().rename(columns={"area": "season_area"})
    water = mirca.groupby(["iso3", "crop_standard", "subcrop", "water_system"], as_index=False)["area"].sum()
    water = water.pivot_table(index=["iso3", "crop_standard", "subcrop"], columns="water_system", values="area", fill_value=0).reset_index()
    for column in ("irrigated", "rainfed"):
        if column not in water:
            water[column] = 0.0
    result = dominant.merge(season_area, on=["iso3", "crop_standard", "subcrop"]).merge(water, on=["iso3", "crop_standard", "subcrop"])
    crop_total = result.groupby(["iso3", "crop_standard"])["season_area"].transform("sum")
    result["season_area_weight"] = result["season_area"] / crop_total
    result["irrigated_share"] = result["irrigated"] / result["season_area"]
    result["rainfed_share"] = result["rainfed"] / result["season_area"]
    result["calendar_uncertainty"] = 1.0 - result["dominant_pair_area"] / result["season_area"]
    result["season_id"] = result["subcrop"].astype(int).map(lambda value: f"S{value:02d}")
    result["cross_year"] = (result["plant_month"] > result["harvest_month"]).astype(int)
    result["growing_months"] = result.apply(lambda row: "|".join(map(str, month_sequence(int(row.plant_month), int(row.harvest_month)))), axis=1)
    result["calendar_source"] = "MIRCA2000 v1.1 30-arcmin; SPAM2020 v2.2 country overlay"

    sacks = sacks_reference(crop_dom)
    sacks_lookup = {(iso3, crop): group for (iso3, crop), group in sacks.groupby(["iso3", "crop_standard"])}
    flags: list[str] = []
    sacks_plants: list[object] = []
    sacks_harvests: list[object] = []
    sacks_variants: list[str] = []
    differences: list[object] = []
    for row in result.itertuples(index=False):
        options = sacks_lookup.get((row.iso3, row.crop_standard))
        if options is None or options.empty:
            flags.append("sacks_unavailable")
            sacks_plants.append("")
            sacks_harvests.append("")
            sacks_variants.append("")
            differences.append("")
            continue
        scored = options.copy()
        scored["distance"] = scored.apply(lambda item: month_distance(row.plant_month, item.plant_month) + month_distance(row.harvest_month, item.harvest_month), axis=1)
        best = scored.sort_values(["distance", "spam_area"], ascending=[True, False]).iloc[0]
        sacks_plants.append(int(best.plant_month))
        sacks_harvests.append(int(best.harvest_month))
        sacks_variants.append(str(best.sacks_variant))
        differences.append(int(best.distance))
        if month_distance(row.plant_month, best.plant_month) > 2 or month_distance(row.harvest_month, best.harvest_month) > 2:
            flags.append("mirca_sacks_disagreement")
        elif row.calendar_uncertainty > 0.35:
            flags.append("mirca_spatial_heterogeneity")
        else:
            flags.append("ok")
    result["calendar_quality_flag"] = flags
    result["sacks_plant_month"] = sacks_plants
    result["sacks_harvest_month"] = sacks_harvests
    result["sacks_variant"] = sacks_variants
    result["mirca_sacks_month_distance"] = differences

    weight_sum = result.groupby(["iso3", "crop_standard"])["season_area_weight"].transform("sum")
    result["weight_sum"] = weight_sum
    result["plant_month_valid"] = result["plant_month"].between(1, 12)
    result["harvest_month_valid"] = result["harvest_month"].between(1, 12)
    result["season_length_months"] = result.apply(lambda row: len(month_sequence(int(row.plant_month), int(row.harvest_month))), axis=1)
    result["season_length_reasonable"] = result["season_length_months"].between(2, 12)
    result["weights_valid"] = (weight_sum - 1.0).abs() < 1e-8
    result["multi_season_reasonable"] = result.groupby(["iso3", "crop_standard"])["season_id"].transform("nunique").between(1, 9)
    result["spatial_assignment_coverage_global"] = assigned_area / total_area

    qc_columns = [
        "iso3", "crop_standard", "season_id", "plant_month", "harvest_month", "cross_year",
        "season_length_months", "season_area_weight", "weight_sum", "plant_month_valid",
        "harvest_month_valid", "season_length_reasonable", "weights_valid", "multi_season_reasonable",
        "sacks_plant_month", "sacks_harvest_month", "sacks_variant", "mirca_sacks_month_distance",
        "calendar_uncertainty", "calendar_quality_flag", "spatial_assignment_coverage_global",
    ]
    qc = result[qc_columns].copy()

    output_columns = [
        "iso3", "crop_standard", "season_id", "plant_month", "harvest_month", "cross_year",
        "growing_months", "season_area_weight", "irrigated_share", "rainfed_share",
        "calendar_source", "calendar_quality_flag",
    ]
    calendar = result[output_columns].rename(columns={"crop_standard": "crop"}).sort_values(["iso3", "crop", "season_id"])

    summary_rows: list[dict[str, object]] = []
    for (iso3, crop), group in result.groupby(["iso3", "crop_standard"]):
        dominant_row = group.sort_values("season_area_weight", ascending=False).iloc[0]
        summary_rows.append({
            "iso3": iso3,
            "crop": crop,
            "num_seasons": int(group["season_id"].nunique()),
            "dominant_plant_month": int(dominant_row.plant_month),
            "dominant_harvest_month": int(dominant_row.harvest_month),
            "cross_year_any": int(group["cross_year"].max()),
            "irrigated_share": float(np.average(group["irrigated_share"], weights=group["season_area_weight"])),
            "rainfed_share": float(np.average(group["rainfed_share"], weights=group["season_area_weight"])),
            "calendar_uncertainty": float(np.average(group["calendar_uncertainty"], weights=group["season_area_weight"])),
        })
    summary = pd.DataFrame(summary_rows).sort_values(["iso3", "crop"])
    return calendar, summary, qc


def main() -> None:
    calendar, summary, qc = build_calendar()
    for path in (OUT, SUMMARY_OUT, QC_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
    calendar.to_parquet(OUT, index=False)
    summary.to_parquet(SUMMARY_OUT, index=False)
    qc.to_csv(QC_OUT, index=False, encoding="utf-8-sig")
    failures = (~qc[["plant_month_valid", "harvest_month_valid", "season_length_reasonable", "weights_valid", "multi_season_reasonable"]].all(axis=1)).sum()
    print(f"calendar_rows={len(calendar)} country_crop={len(summary)} hard_qc_failures={failures}")
    print(qc["calendar_quality_flag"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
