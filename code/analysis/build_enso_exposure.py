"""Build official NOAA monthly ENSO data and fixed-calendar crop exposures."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


import os
ROOT = Path(os.environ.get('ENSO_DATA_ROOT', Path(__file__).resolve().parents[2]))
RELATIVE = ROOT / "data/raw/enso/noaa_relative_nino34/Rnino34.ascii.txt"
RONI = ROOT / "data/raw/enso/noaa_roni/RONI.ascii.txt"
CALENDAR = ROOT / "data/intermediate/crop_calendars/crop_calendar_country_crop.parquet"
MONTHLY_OUT = ROOT / "data/intermediate/enso_exposure/enso_monthly.parquet"
EXPOSURE_OUT = ROOT / "data/intermediate/enso_exposure/enso_exposure_country_crop_year.parquet"
QC_OUT = ROOT / "outputs/diagnostics/enso_exposure_qc.csv"
EXAMPLES_OUT = ROOT / "outputs/diagnostics/enso_alignment_examples.csv"
SEASON_CENTER_MONTH = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def strength(value: float) -> str:
    if pd.isna(value) or abs(value) < 0.5:
        return "neutral"
    magnitude = abs(value)
    if magnitude < 1.0:
        return "weak"
    if magnitude < 1.5:
        return "moderate"
    if magnitude < 2.0:
        return "strong"
    return "very_strong"


def identify_events(monthly: pd.DataFrame) -> pd.DataFrame:
    raw_phase = np.where(
        monthly["roni"].isna(),
        "Missing",
        np.where(monthly["roni"] >= 0.5, "El Nino", np.where(monthly["roni"] <= -0.5, "La Nina", "Neutral")),
    )
    monthly["enso_phase"] = np.where(monthly["roni"].notna(), "Neutral", pd.NA)
    monthly["enso_event_id"] = ""
    monthly["enso_strength"] = np.where(monthly["roni"].notna(), "neutral", pd.NA)
    start = 0
    while start < len(monthly):
        phase = raw_phase[start]
        end = start + 1
        while end < len(monthly) and raw_phase[end] == phase:
            end += 1
        if phase != "Neutral" and end - start >= 5:
            block = monthly.iloc[start:end]
            first = block.iloc[0]
            last = block.iloc[-1]
            prefix = "EN" if phase == "El Nino" else "LN"
            event_id = f"{prefix}_{int(first.year)}{int(first.month):02d}_{int(last.year)}{int(last.month):02d}"
            peak = float(block["roni"].abs().max())
            monthly.loc[monthly.index[start:end], "enso_phase"] = phase
            monthly.loc[monthly.index[start:end], "enso_event_id"] = event_id
            monthly.loc[monthly.index[start:end], "enso_strength"] = strength(peak)
        start = end
    return monthly


def build_monthly() -> pd.DataFrame:
    relative = pd.read_csv(RELATIVE, sep=r"\s+").rename(columns={"YR": "year", "MTH": "month", "ANOM": "relative_nino34"})
    roni = pd.read_csv(RONI, sep=r"\s+").rename(columns={"YR": "year", "ANOM": "roni"})
    roni["month"] = roni["SEAS"].map(SEASON_CENTER_MONTH)
    roni = roni[["year", "month", "roni"]]
    monthly = relative.merge(roni, on=["year", "month"], how="left", validate="one_to_one")
    monthly["date"] = pd.to_datetime(dict(year=monthly.year, month=monthly.month, day=1))
    monthly = identify_events(monthly.sort_values("date").reset_index(drop=True))
    monthly["source_version"] = "NOAA CPC ERSSTv6 Relative Nino3.4 + official RONI; snapshot 2026-09-18"
    return monthly[["year", "month", "date", "relative_nino34", "roni", "enso_phase", "enso_strength", "enso_event_id", "source_version"]]


def dates_for_season(plant: int, harvest: int, harvest_year: int) -> list[pd.Timestamp]:
    if plant <= harvest:
        return [pd.Timestamp(harvest_year, month, 1) for month in range(plant, harvest + 1)]
    return [pd.Timestamp(harvest_year - 1, month, 1) for month in range(plant, 13)] + [pd.Timestamp(harvest_year, month, 1) for month in range(1, harvest + 1)]


def signed_peak(values: pd.Series) -> float:
    values = values.dropna()
    if values.empty:
        return np.nan
    return float(values.loc[values.abs().idxmax()])


def split_means(values: np.ndarray) -> tuple[float, float, float]:
    parts = np.array_split(values, 3)
    return tuple(float(np.nanmean(part)) if len(part) else np.nan for part in parts)


def build_exposure(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calendar = pd.read_parquet(CALENDAR)
    lookup = monthly.set_index("date")
    season_rows: list[dict[str, object]] = []
    for row in calendar.itertuples(index=False):
        for harvest_year in range(1981, 2025):
            dates = dates_for_season(int(row.plant_month), int(row.harvest_month), harvest_year)
            values = lookup.reindex(dates)
            nino = values["relative_nino34"]
            roni = values["roni"]
            early, middle, late = split_means(nino.to_numpy(dtype=float))
            event_counts = Counter(value for value in values["enso_event_id"].fillna("") if value)
            event_id = event_counts.most_common(1)[0][0] if event_counts else ""
            season_rows.append({
                "iso3": row.iso3,
                "crop": row.crop,
                "season_id": row.season_id,
                "harvest_year": harvest_year,
                "plant_month": int(row.plant_month),
                "harvest_month": int(row.harvest_month),
                "cross_year": int(row.cross_year),
                "season_area_weight": float(row.season_area_weight),
                "months_used": "|".join(date.strftime("%Y-%m") for date in dates),
                "monthly_nino34": "|".join("NA" if pd.isna(value) else f"{value:.2f}" for value in nino),
                "enso_season": float(nino.mean()) if nino.notna().all() else np.nan,
                "season_max": float(nino.max()) if nino.notna().all() else np.nan,
                "season_min": float(nino.min()) if nino.notna().all() else np.nan,
                "season_absmax": float(nino.abs().max()) if nino.notna().all() else np.nan,
                "roni_mean": float(roni.mean()) if roni.notna().all() else np.nan,
                "roni_peak": signed_peak(roni) if roni.notna().all() else np.nan,
                "enso_early": early,
                "enso_mid": middle,
                "enso_late": late,
                "season_event_id": event_id,
                "missing_months": int(nino.isna().sum()),
                "cross_year_previous_year_used": int(not row.cross_year or dates[0].year == harvest_year - 1),
            })
    seasons = pd.DataFrame(season_rows)

    exposures: list[dict[str, object]] = []
    for (iso3, crop, harvest_year), group in seasons.groupby(["iso3", "crop", "harvest_year"], sort=True):
        weights = group["season_area_weight"].to_numpy(dtype=float)
        weights = weights / weights.sum()
        event_weight: defaultdict[str, float] = defaultdict(float)
        for event_id, weight in zip(group["season_event_id"], weights):
            if event_id:
                event_weight[str(event_id)] += float(weight)
        event_id = max(event_weight, key=event_weight.get) if event_weight else ""

        def weighted(column: str) -> float:
            values = group[column].to_numpy(dtype=float)
            return float(np.dot(weights, values)) if np.isfinite(values).all() else np.nan

        roni_mean = weighted("roni_mean")
        roni_peak_value = weighted("roni_peak")
        phase = "El Nino" if roni_mean >= 0.5 else "La Nina" if roni_mean <= -0.5 else "Neutral"
        exposures.append({
            "iso3": iso3,
            "crop": crop,
            "harvest_year": int(harvest_year),
            "enso_gs_mean": weighted("enso_season"),
            "enso_gs_max": weighted("season_max"),
            "enso_gs_min": weighted("season_min"),
            "enso_gs_absmax": weighted("season_absmax"),
            "roni_mean_gs": roni_mean,
            "roni_peak": roni_peak_value,
            "enso_early": weighted("enso_early"),
            "enso_mid": weighted("enso_mid"),
            "enso_late": weighted("enso_late"),
            "enso_phase": phase,
            "enso_strength": strength(roni_peak_value),
            "enso_event_id": event_id,
        })
    exposure = pd.DataFrame(exposures).sort_values(["iso3", "crop", "harvest_year"])

    qc: list[dict[str, object]] = []
    expected_dates = pd.date_range(monthly["date"].min(), monthly["date"].max(), freq="MS")
    missing_calendar_months = len(expected_dates.difference(monthly["date"]))
    qc.append({"check": "monthly_time_continuity", "scope": "all", "value": missing_calendar_months, "status": "PASS" if missing_calendar_months == 0 else "FAIL", "notes": "Missing calendar months between first and last NOAA Relative Nino3.4 observations."})
    duplicate_months = int(monthly.duplicated(["year", "month"]).sum())
    qc.append({"check": "monthly_duplicate_months", "scope": "all", "value": duplicate_months, "status": "PASS" if duplicate_months == 0 else "FAIL", "notes": "Duplicate year-month rows in monthly ENSO table."})
    missing_relative = int(monthly["relative_nino34"].isna().sum())
    qc.append({"check": "monthly_missing_relative_nino34", "scope": "all", "value": missing_relative, "status": "PASS" if missing_relative == 0 else "FAIL", "notes": "Missing NOAA Relative Nino3.4 values."})
    missing_roni_dates = monthly.loc[monthly["roni"].isna(), "date"]
    roni_boundary_only = set(missing_roni_dates) <= {monthly["date"].min(), monthly["date"].max()}
    qc.append({"check": "monthly_missing_roni_boundary", "scope": "all", "value": len(missing_roni_dates), "status": "PASS" if roni_boundary_only else "FAIL", "notes": "Official RONI has no interior gaps; 1949-12 precedes RONI coverage and 2026-08 has no centered RONI season in the snapshot. Values were not substituted."})
    duplicate_count = int(exposure.duplicated(["iso3", "crop", "harvest_year"]).sum())
    qc.append({"check": "unique_key", "scope": "all", "value": duplicate_count, "status": "PASS" if duplicate_count == 0 else "FAIL", "notes": "Duplicate iso3-crop-harvest_year rows."})
    missing = int(exposure["enso_gs_mean"].isna().sum())
    qc.append({"check": "missing_exposure", "scope": "all", "value": missing, "status": "PASS" if missing == 0 else "FAIL", "notes": "Rows missing Relative Nino3.4 growing-season exposure."})
    cross = seasons[seasons["cross_year"] == 1]
    cross_errors = int((cross["cross_year_previous_year_used"] != 1).sum())
    qc.append({"check": "cross_year_alignment", "scope": "all", "value": cross_errors, "status": "PASS" if cross_errors == 0 else "FAIL", "notes": f"Checked {len(cross)} season-years."})
    weight_error = float(calendar.groupby(["iso3", "crop"])["season_area_weight"].sum().sub(1).abs().max())
    qc.append({"check": "season_weight_sum_max_error", "scope": "all", "value": weight_error, "status": "PASS" if weight_error < 1e-8 else "FAIL", "notes": "Fixed MIRCA baseline season weights."})
    for year in (1983, 1998, 2016, 2024):
        value = float(exposure.loc[exposure.harvest_year == year, "enso_gs_mean"].quantile(0.90))
        qc.append({"check": "strong_el_nino_sanity_p90", "scope": str(year), "value": value, "status": "PASS" if value > 0.5 else "WARN", "notes": "90th percentile verifies that calendars overlapping the named strong event have clearly positive exposure; not all harvest calendars overlap the event."})
    for year in (1989, 1999, 2011, 2022):
        value = float(exposure.loc[exposure.harvest_year == year, "enso_gs_mean"].quantile(0.10))
        qc.append({"check": "la_nina_sanity_p10", "scope": str(year), "value": value, "status": "PASS" if value < -0.5 else "WARN", "notes": "10th percentile verifies that calendars overlapping the named La Nina event have clearly negative exposure."})
    variation = float(exposure.groupby("harvest_year")["enso_gs_mean"].std().median())
    qc.append({"check": "calendar_induced_cross_sectional_variation", "scope": "all", "value": variation, "status": "PASS" if variation > 0 else "FAIL", "notes": "Median within-year SD across country-crop calendars."})

    examples_spec = [("BRA", "SOY"), ("BRA", "MAIZE"), ("CHN", "RICE"), ("CHN", "WHEAT"), ("USA", "MAIZE"), ("IND", "RICE")]
    examples: list[pd.DataFrame] = []
    for iso3, crop in examples_spec:
        selected = seasons[(seasons.iso3 == iso3) & (seasons.crop == crop) & (seasons.harvest_year == 2016)].copy()
        selected["case"] = f"{iso3} {crop}"
        selected["season_exposure"] = selected["enso_season"]
        examples.append(selected[["case", "iso3", "crop", "season_id", "season_area_weight", "plant_month", "harvest_month", "harvest_year", "months_used", "monthly_nino34", "season_exposure"]])
    return exposure, pd.DataFrame(qc), pd.concat(examples, ignore_index=True)


def main() -> None:
    monthly = build_monthly()
    exposure, qc, examples = build_exposure(monthly)
    for path in (MONTHLY_OUT, EXPOSURE_OUT, QC_OUT, EXAMPLES_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_parquet(MONTHLY_OUT, index=False)
    exposure.to_parquet(EXPOSURE_OUT, index=False)
    qc.to_csv(QC_OUT, index=False, encoding="utf-8-sig")
    examples.to_csv(EXAMPLES_OUT, index=False, encoding="utf-8-sig")
    dates = monthly["date"]
    expected = pd.date_range(dates.min(), dates.max(), freq="MS")
    print(f"monthly_rows={len(monthly)} continuous={dates.equals(pd.Series(expected))} duplicates={monthly.duplicated(['year','month']).sum()}")
    print(f"exposure_rows={len(exposure)} qc_failures={(qc.status == 'FAIL').sum()} examples={len(examples)}")


if __name__ == "__main__":
    main()
