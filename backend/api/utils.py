import io
import time
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from rest_framework import serializers


CANONICAL_COLUMNS = {
    "equipmentname": "Equipment Name",
    "type": "Type",
    "flowrate": "Flowrate",
    "pressure": "Pressure",
    "temperature": "Temperature",
}


def _normalize_column(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized_map = {_normalize_column(col): col for col in df.columns}
    missing = [key for key in CANONICAL_COLUMNS if key not in normalized_map]
    if missing:
        raise serializers.ValidationError(
            f"Missing required columns: {', '.join(missing)}"
        )
    rename_map = {normalized_map[key]: CANONICAL_COLUMNS[key] for key in CANONICAL_COLUMNS}
    return df.rename(columns=rename_map)


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["Flowrate", "Pressure", "Temperature"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _series_stats(series: pd.Series) -> Dict:
    series = series.dropna()
    if series.empty:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": float(series.mean()),
        "std": float(series.std(ddof=0)),
        "min": float(series.min()),
        "max": float(series.max()),
    }


def _iqr_outliers(series: pd.Series) -> int:
    series = series.dropna()
    if series.empty:
        return 0
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((series < lower) | (series > upper)).sum())


def calculate_insights(df: pd.DataFrame) -> Dict:
    flow = df["Flowrate"]
    pressure = df["Pressure"]
    temperature = df["Temperature"]

    anomalies = {
        "flowrate": _iqr_outliers(flow),
        "pressure": _iqr_outliers(pressure),
        "temperature": _iqr_outliers(temperature),
    }
    total_anomalies = int(sum(anomalies.values()))

    missing_ratio = float(df[["Flowrate", "Pressure", "Temperature"]].isna().mean().mean())
    anomaly_rate = total_anomalies / max(len(df), 1)

    stability = 0.0
    for series in [flow, pressure, temperature]:
        series = series.dropna()
        if series.empty or series.mean() == 0:
            continue
        stability += max(0.0, 1.0 - (series.std(ddof=0) / series.mean()))
    stability_index = round((stability / 3.0) * 100, 1)

    health_score = 100.0
    health_score -= min(35.0, anomaly_rate * 100.0 * 0.7)
    health_score -= min(20.0, missing_ratio * 100.0 * 0.4)
    health_score -= max(0.0, 50.0 - stability_index) * 0.1
    health_score = max(40.0, round(health_score, 1))

    alerts = []
    if temperature.mean(skipna=True) > 320:
        alerts.append("High average temperature detected")
    if pressure.mean(skipna=True) > 6:
        alerts.append("High average pressure detected")
    if flow.mean(skipna=True) < 150:
        alerts.append("Throughput below target range")
    if missing_ratio > 0.05:
        alerts.append("Missing sensor values present")
    if total_anomalies > 0:
        alerts.append(f"{total_anomalies} potential anomalies flagged")
    if not alerts:
        alerts.append("No critical alerts. System within normal bands.")

    utilization_ratio = 0.0
    flow_max = flow.max(skipna=True)
    if flow_max and flow_max > 0:
        utilization_ratio = float(flow.mean(skipna=True) / flow_max)
    if utilization_ratio >= 0.85:
        utilization_band = "High"
    elif utilization_ratio >= 0.6:
        utilization_band = "Moderate"
    else:
        utilization_band = "Low"

    efficiency_index = round(80 + (utilization_ratio * 20), 1)

    return {
        "health_score": health_score,
        "stability_index": stability_index,
        "efficiency_index": efficiency_index,
        "utilization_band": utilization_band,
        "anomalies": anomalies,
        "anomaly_rate": round(anomaly_rate * 100, 2),
        "missing_ratio": round(missing_ratio * 100, 2),
        "alerts": alerts,
    }


def generate_live_signals(stats: Dict, points: int = 24, bucket_seconds: int = 10) -> Dict:
    now_bucket = int(time.time() // bucket_seconds)
    seed = now_bucket + int(stats.get("seed", 0))
    rng = np.random.default_rng(seed=seed)

    signals = {}
    for key in ["flowrate", "pressure", "temperature"]:
        metric = stats.get(key, {})
        mean = float(metric.get("mean", 0.0))
        std = float(metric.get("std", 0.0))
        scale = max(std * 0.15, abs(mean) * 0.02, 0.1)
        series = []
        for _ in range(points):
            value = mean + rng.normal(0.0, scale)
            series.append(round(float(value), 2))
        signals[key] = series

    labels = [f"-{(points - 1 - idx) * bucket_seconds}s" for idx in range(points)]
    return {"labels": labels, "signals": signals, "bucket_seconds": bucket_seconds}


def analyze_csv(file_obj) -> Tuple[pd.DataFrame, Dict]:
    try:
        content = file_obj.read()
    except Exception as exc:
        raise serializers.ValidationError("Unable to read uploaded file.") from exc

    if not content:
        raise serializers.ValidationError("Uploaded file is empty.")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise serializers.ValidationError("CSV parsing failed. Check file format.") from exc

    if df.empty:
        raise serializers.ValidationError("CSV contains no rows.")

    df = _normalize_dataframe(df)
    df = _coerce_numeric(df)

    type_distribution = df["Type"].fillna("Unknown").value_counts().to_dict()

    stats = {
        "flowrate": _series_stats(df["Flowrate"]),
        "pressure": _series_stats(df["Pressure"]),
        "temperature": _series_stats(df["Temperature"]),
    }
    insights = calculate_insights(df)

    summary = {
        "row_count": int(len(df)),
        "avg_flowrate": float(df["Flowrate"].mean(skipna=True)),
        "avg_pressure": float(df["Pressure"].mean(skipna=True)),
        "avg_temperature": float(df["Temperature"].mean(skipna=True)),
        "type_distribution": type_distribution,
        "columns": list(df.columns),
        "stats": stats,
        "insights": insights,
    }

    return df, summary


def preview_rows(df: pd.DataFrame, limit: int = 200):
    return df.head(limit).fillna("").to_dict(orient="records")
