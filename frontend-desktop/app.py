import sys
import os
import json
import uuid
from datetime import datetime
import requests
import pandas as pd
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QFileDialog,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QCheckBox,
    QFrame,
    QHeaderView,
    QStackedWidget,
    QSizePolicy,
    QScrollArea,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

API_BASE = os.getenv("CHEMVIZ_API_URL", "http://localhost:8000/api")
BASE_DIR = os.path.dirname(__file__)
CACHE_PATH = os.path.join(BASE_DIR, "cache.json")

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
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    rename_map = {normalized_map[key]: CANONICAL_COLUMNS[key] for key in CANONICAL_COLUMNS}
    return df.rename(columns=rename_map)


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["Flowrate", "Pressure", "Temperature"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _series_stats(series: pd.Series) -> dict:
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


def calculate_insights(df: pd.DataFrame) -> dict:
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


def _read_cache() -> dict:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _write_cache(payload: dict) -> None:
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except Exception:
        pass


LIGHT_STYLE = """
QWidget { background-color: #f3f5f9; color: #0f172a; font-family: "Segoe UI"; }
QFrame#Card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; }
QFrame#HeroCard {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fff7ed, stop:1 #f1f5f9);
  border: 1px solid #f0c799;
  border-radius: 18px;
}
QFrame#UploadCard { background-color: #ffffff; border: 1px dashed #ffd1a3; border-radius: 18px; }
QFrame#StatCard { background-color: #fff7ed; border: 1px solid #fed7aa; border-radius: 12px; }
QLabel#HeaderTitle { font-size: 22px; font-weight: 700; }
QLabel#HeaderSubtitle { font-size: 12px; color: #64748b; }
QLabel#SectionTitle { font-size: 14px; font-weight: 700; }
QLabel#CardTitle { font-size: 12px; font-weight: 700; }
QLabel#UploadHint { color: #6b7280; }
QLabel#MutedText { color: #64748b; font-size: 10px; }
QLabel#StatLabel { color: #6b7280; font-size: 10px; }
QLabel#StatValue { font-size: 14px; font-weight: 700; }
QLabel#FileChip { background-color: #fff7ed; border: 1px solid #fed7aa; border-radius: 999px; padding: 4px 10px; color: #9a3412; }
QLabel#Badge { background-color: #eef2ff; color: #1e3a8a; border: 1px solid #c7d2fe; border-radius: 999px; padding: 3px 10px; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel#StatusPill { background-color: #ecfeff; color: #0e7490; border: 1px solid #a5f3fc; border-radius: 999px; padding: 3px 10px; font-size: 10px; font-weight: 700; }
QPushButton { background-color: #ff7a00; color: white; border-radius: 10px; padding: 8px 12px; font-weight: 600; }
QPushButton#SecondaryButton { background-color: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; }
QPushButton#OutlineButton { background-color: #ffffff; color: #ff7a00; border: 1px solid #ff7a00; }
QTableWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
QListWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
"""

DARK_STYLE = """
QWidget { background-color: #0b1226; color: #e2e8f0; font-family: "Segoe UI"; }
QFrame#Card { background-color: #0f172a; border: 1px solid #1f2a44; border-radius: 14px; }
QFrame#HeroCard {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b1226, stop:1 #111827);
  border: 1px solid #1f2a44;
  border-radius: 18px;
}
QFrame#UploadCard { background-color: #0f172a; border: 1px dashed #334155; border-radius: 18px; }
QFrame#StatCard { background-color: #111827; border: 1px solid #1f2a44; border-radius: 12px; }
QLabel#HeaderTitle { font-size: 22px; font-weight: 700; }
QLabel#HeaderSubtitle { font-size: 12px; color: #94a3b8; }
QLabel#SectionTitle { font-size: 14px; font-weight: 700; }
QLabel#CardTitle { font-size: 12px; font-weight: 700; }
QLabel#UploadHint { color: #94a3b8; }
QLabel#MutedText { color: #94a3b8; font-size: 10px; }
QLabel#StatLabel { color: #94a3b8; font-size: 10px; }
QLabel#StatValue { font-size: 14px; font-weight: 700; }
QLabel#FileChip { background-color: #1f2937; border: 1px solid #334155; border-radius: 999px; padding: 4px 10px; color: #e2e8f0; }
QLabel#Badge { background-color: #1e293b; color: #c7d2fe; border: 1px solid #334155; border-radius: 999px; padding: 3px 10px; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel#StatusPill { background-color: #0f172a; color: #7dd3fc; border: 1px solid #1f2a44; border-radius: 999px; padding: 3px 10px; font-size: 10px; font-weight: 700; }
QPushButton { background-color: #ff9f43; color: #0b1226; border-radius: 10px; padding: 8px 12px; font-weight: 600; }
QPushButton#SecondaryButton { background-color: #111827; color: #e2e8f0; border: 1px solid #334155; }
QPushButton#OutlineButton { background-color: #0b1226; color: #ff9f43; border: 1px solid #ff9f43; }
QTableWidget { background-color: #0f172a; border: 1px solid #1f2a44; border-radius: 8px; gridline-color: #1f2a44; }
QTableWidget::item { background-color: #0f172a; color: #e2e8f0; }
QTableWidget::item:alternate { background-color: #111827; color: #e2e8f0; }
QTableWidget::item:selected { background-color: #1e293b; color: #f8fafc; }
QHeaderView::section { background-color: #111827; color: #e2e8f0; border: 1px solid #1f2a44; padding: 4px 6px; }
QTableCornerButton::section { background-color: #111827; border: 1px solid #1f2a44; }
QListWidget { background-color: #0f172a; border: 1px solid #1f2a44; border-radius: 8px; }
"""


class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None, figsize=(12, 9.5), compact: bool = False):
        fig = Figure(figsize=figsize, dpi=100)
        self.ax_live = fig.add_subplot(221)
        self.ax_type = fig.add_subplot(222)
        self.ax_scatter = fig.add_subplot(223)
        self.ax_hist = fig.add_subplot(224)
        self.compact = compact
        self.dark_mode = False
        super().__init__(fig)
        self.setParent(parent)

    def set_theme(self, dark: bool):
        self.dark_mode = dark

    def update_charts(self, dataset):
        self.ax_live.clear()
        self.ax_type.clear()
        self.ax_scatter.clear()
        self.ax_hist.clear()

        summary = dataset.get("summary") or dataset
        title_size = 10 if self.compact else 12
        tick_size = 7 if self.compact else 9
        type_dist = summary.get("type_distribution", {})
        if type_dist:
            labels = list(type_dist.keys())
            counts = list(type_dist.values())
            self.ax_type.bar(range(len(labels)), counts, color="#FF7A00")
            self.ax_type.set_xticks(range(len(labels)))
            self.ax_type.set_xticklabels(labels, rotation=25, ha="right", fontsize=tick_size)
            self.ax_type.set_title("Equipment Mix", fontsize=title_size)

        rows = dataset.get("rows") or []
        if rows:
            def as_number(value):
                try:
                    return float(value)
                except Exception:
                    return float("nan")

            scatter_points = [
                (as_number(row.get("Pressure")), as_number(row.get("Flowrate")))
                for row in rows
            ]
            scatter_points = [(x, y) for x, y in scatter_points if not np.isnan(x) and not np.isnan(y)]
            if scatter_points:
                xs, ys = zip(*scatter_points)
                self.ax_scatter.scatter(xs, ys, color="#2EC4B6", alpha=0.7)
            self.ax_scatter.set_xlabel("Pressure", fontsize=tick_size)
            self.ax_scatter.set_ylabel("Flowrate", fontsize=tick_size)
            self.ax_scatter.set_title("Pressure vs Flowrate", fontsize=title_size)

            temp_rows = rows[:20]
            temp_labels = [row.get("Equipment Name") or "Unit" for row in temp_rows]
            temp_values = [as_number(row.get("Temperature")) for row in temp_rows]
            x_vals = list(range(len(temp_values)))
            self.ax_live.plot(x_vals, temp_values, color="#4c6fff")
            self.ax_live.set_title("Temperature Profile", fontsize=title_size)
            if temp_labels:
                step = max(1, len(temp_labels) // 6)
                ticks = list(range(0, len(temp_labels), step))
                self.ax_live.set_xticks(ticks)
                self.ax_live.set_xticklabels([temp_labels[i] for i in ticks], rotation=40, ha="right", fontsize=tick_size)

            flow_values = [
                as_number(row.get("Flowrate"))
                for row in rows
                if not np.isnan(as_number(row.get("Flowrate")))
            ]
            if flow_values:
                min_v = min(flow_values)
                max_v = max(flow_values)
                span = max_v - min_v or 1
                bin_count = 6
                bin_size = span / bin_count
                bins = [0] * bin_count
                for val in flow_values:
                    idx = min(bin_count - 1, int((val - min_v) / bin_size))
                    bins[idx] += 1
                labels_hist = []
                for i in range(bin_count):
                    start = min_v + i * bin_size
                    end = start + bin_size
                    labels_hist.append(f"{start:.1f}-{end:.1f}")
                self.ax_hist.bar(labels_hist, bins, color="#4C6FFF", alpha=0.8)
                self.ax_hist.set_xticks(range(len(labels_hist)))
                self.ax_hist.set_xticklabels(labels_hist, rotation=20, ha="right", fontsize=tick_size)
                self.ax_hist.set_title("Flowrate Distribution", fontsize=title_size)
        self._apply_theme_to_axes()
        self.figure.tight_layout(pad=2.0)
        self.draw()

    def _apply_theme_to_axes(self):
        if self.dark_mode:
            fig_bg = "#0b1226"
            ax_bg = "#111827"
            grid = "#1f2a44"
            text = "#e2e8f0"
        else:
            fig_bg = "#ffffff"
            ax_bg = "#ffffff"
            grid = "#e5e7eb"
            text = "#111827"
        self.figure.patch.set_facecolor(fig_bg)
        for ax in [self.ax_live, self.ax_type, self.ax_scatter, self.ax_hist]:
            ax.set_facecolor(ax_bg)
            ax.tick_params(colors=text, labelcolor=text)
            ax.title.set_color(text)
            ax.xaxis.label.set_color(text)
            ax.yaxis.label.set_color(text)
            ax.grid(True, color=grid, alpha=0.35)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chemical Equipment Visualizer")
        self.resize(1280, 820)
        self.setMinimumSize(980, 780)

        self.choose_button = QPushButton("Choose File")
        self.choose_button.setObjectName("SecondaryButton")
        self.choose_button.clicked.connect(self.choose_file)
        self.upload_button = QPushButton("Upload")
        self.upload_button.clicked.connect(self.upload_csv)
        self.selected_file_label = QLabel("No file chosen")
        self.selected_file_label.setObjectName("FileChip")
        self.selected_file_path = ""

        self.back_button = QPushButton("<- Back to uploads")
        self.back_button.setObjectName("OutlineButton")
        self.back_button.clicked.connect(self.show_uploads)

        self.theme_toggle_home = QCheckBox("Dark Mode")
        self.theme_toggle_home.stateChanged.connect(self.toggle_theme)
        self.theme_toggle_detail = QCheckBox("Dark Mode")
        self.theme_toggle_detail.stateChanged.connect(self.toggle_theme)

        self.dataset_list = QListWidget()
        self.dataset_list.setSelectionMode(QListWidget.SingleSelection)
        self.dataset_list.itemClicked.connect(self.on_dataset_selected)
        self.dataset_list.itemActivated.connect(self.on_dataset_selected)

        self.recent_name_label = QLabel("Most Recent Dataset: None")
        self.recent_name_label.setObjectName("SectionTitle")
        self.recent_name_label.setWordWrap(True)
        self.recent_uploaded_label = QLabel("Uploaded: -")
        self.recent_uploaded_label.setObjectName("MutedText")
        self.recent_stats_label = QLabel("Records: - | Avg Flow: - | Avg Pressure: - | Avg Temp: -")
        self.recent_stats_label.setObjectName("MutedText")
        self.recent_stats_label.setWordWrap(True)

        self.detail_name_label = QLabel("Dataset: -")
        self.detail_name_label.setObjectName("SectionTitle")
        self.detail_name_label.setWordWrap(True)
        self.detail_uploaded_label = QLabel("Uploaded: -")
        self.detail_uploaded_label.setObjectName("MutedText")

        self.brief_label = QLabel("Upload a dataset to generate the operational brief.")
        self.brief_label.setWordWrap(True)

        self.pi_values = {
            "Health Score": QLabel("-"),
            "Stability Index": QLabel("-"),
            "Efficiency Index": QLabel("-"),
            "Utilization Band": QLabel("-"),
            "Anomaly Rate": QLabel("-"),
            "Missing Ratio": QLabel("-"),
        }
        for value in self.pi_values.values():
            value.setObjectName("StatValue")

        self.alerts_layout = QVBoxLayout()

        self.stat_cards = {}
        for key in ["Total Records", "Avg Flowrate", "Avg Pressure", "Avg Temperature", "Equipment Types"]:
            value_label = QLabel("-")
            value_label.setObjectName("StatValue")
            self.stat_cards[key] = value_label

        self.download_pdf_button = QPushButton("Download PDF")
        self.download_pdf_button.setObjectName("OutlineButton")
        self.download_pdf_button.clicked.connect(self.download_pdf)
        self.export_charts_button = QPushButton("Export Charts PNG")
        self.export_charts_button.setObjectName("OutlineButton")
        self.export_charts_button.clicked.connect(self.export_charts_png)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.preview_canvas = ChartCanvas(figsize=(9, 6), compact=True)
        self.preview_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_canvas.setMinimumHeight(420)

        self.chart_canvas = ChartCanvas(figsize=(12, 9.5))
        self.chart_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_canvas.setMinimumHeight(640)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_uploads_page())
        self.stack.addWidget(self.build_detail_page())

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(self.stack)
        self.setCentralWidget(root)

        self.active_dataset = None
        self.preview_dataset = None
        self.apply_theme(False)
        self.refresh_datasets()

    def build_card(self, title, body_layout):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        layout.addWidget(title_label)
        layout.addLayout(body_layout)
        return card

    def build_uploads_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(14)

        header = QFrame()
        header.setObjectName("HeroCard")
        header.setMinimumHeight(130)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 18, 20, 18)

        title_box = QVBoxLayout()
        title = QLabel("Chemical Equipment Parameter Visualizer")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Upload datasets, inspect operational health, and export reports from a single console.")
        subtitle.setObjectName("HeaderSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)

        badge_col = QVBoxLayout()
        badge_row = QHBoxLayout()
        badge = QLabel("CONTROL ROOM")
        badge.setObjectName("Badge")
        status = QLabel("DESKTOP OPS")
        status.setObjectName("StatusPill")
        badge_row.addWidget(badge)
        badge_row.addWidget(status)
        badge_col.addLayout(badge_row)
        badge_col.addSpacing(6)
        badge_col.addWidget(self.theme_toggle_home, alignment=Qt.AlignRight)
        header_layout.addLayout(badge_col)
        outer.addWidget(header)

        content_row = QHBoxLayout()
        content_row.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        upload_card = QFrame()
        upload_card.setObjectName("UploadCard")
        upload_layout = QVBoxLayout(upload_card)
        upload_layout.setContentsMargins(16, 14, 16, 14)
        upload_title = QLabel("Upload Dataset")
        upload_title.setObjectName("SectionTitle")
        upload_hint = QLabel("CSV with Equipment Name, Type, Flowrate, Pressure, Temperature.")
        upload_hint.setObjectName("UploadHint")
        upload_layout.addWidget(upload_title)
        upload_layout.addWidget(upload_hint)

        file_row = QHBoxLayout()
        file_row.addWidget(self.choose_button)
        file_row.addWidget(self.selected_file_label, 1)
        file_row.addStretch(1)
        file_row.addWidget(self.upload_button)
        upload_layout.addLayout(file_row)
        left_col.addWidget(upload_card)

        recent_card = QFrame()
        recent_card.setObjectName("Card")
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(14, 12, 14, 12)
        recent_title = QLabel("Recent Datasets")
        recent_title.setObjectName("SectionTitle")
        recent_layout.addWidget(recent_title)
        recent_layout.addWidget(self.dataset_list, 1)
        left_col.addWidget(recent_card, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        recent_summary = QFrame()
        recent_summary.setObjectName("Card")
        summary_layout = QVBoxLayout(recent_summary)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.addWidget(self.recent_name_label)
        summary_layout.addWidget(self.recent_uploaded_label)
        summary_layout.addWidget(self.recent_stats_label)
        right_col.addWidget(recent_summary)

        snapshot_card = QFrame()
        snapshot_card.setObjectName("Card")
        snapshot_layout = QVBoxLayout(snapshot_card)
        snapshot_layout.setContentsMargins(16, 14, 16, 14)
        snapshot_title = QLabel("Snapshot Visuals")
        snapshot_title.setObjectName("SectionTitle")
        snapshot_layout.addWidget(snapshot_title)
        snapshot_layout.addWidget(self.preview_canvas)
        right_col.addWidget(snapshot_card, 1)

        content_row.addLayout(left_col, 1)
        content_row.addLayout(right_col, 2)
        outer.addLayout(content_row, 1)
        return page

    def build_detail_page(self):
        page = QWidget()
        outer_layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)

        header_card = QFrame()
        header_card.setObjectName("Card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_top = QHBoxLayout()
        header_top.addWidget(self.back_button)
        header_top.addStretch(1)
        header_top.addWidget(self.download_pdf_button)
        header_top.addWidget(self.export_charts_button)
        header_top.addWidget(self.theme_toggle_detail)
        header_layout.addLayout(header_top)
        header_layout.addWidget(self.detail_name_label)
        header_layout.addWidget(self.detail_uploaded_label)
        layout.addWidget(header_card)

        brief_card = QFrame()
        brief_card.setObjectName("Card")
        brief_layout = QVBoxLayout(brief_card)
        brief_layout.setContentsMargins(14, 12, 14, 12)
        brief_title = QLabel("Operational Brief")
        brief_title.setObjectName("SectionTitle")
        brief_layout.addWidget(brief_title)
        brief_layout.addWidget(self.brief_label)

        pi_card = QFrame()
        pi_card.setObjectName("Card")
        pi_layout = QVBoxLayout(pi_card)
        pi_layout.setContentsMargins(14, 12, 14, 12)
        pi_title = QLabel("Process Intelligence")
        pi_title.setObjectName("SectionTitle")
        pi_layout.addWidget(pi_title)

        grid = QGridLayout()
        items = [
            "Health Score",
            "Stability Index",
            "Efficiency Index",
            "Utilization Band",
            "Anomaly Rate",
            "Missing Ratio",
        ]
        for idx, name in enumerate(items):
            row = idx // 3
            col = idx % 3
            label = QLabel(name)
            label.setObjectName("StatLabel")
            value = self.pi_values[name]
            container = QVBoxLayout()
            container.addWidget(label)
            container.addWidget(value)
            cell = QWidget()
            cell.setLayout(container)
            grid.addWidget(cell, row, col)
        pi_layout.addLayout(grid)

        alerts_title = QLabel("Alerts")
        alerts_title.setObjectName("SectionTitle")
        pi_layout.addWidget(alerts_title)
        pi_layout.addLayout(self.alerts_layout)

        brief_row = QHBoxLayout()
        brief_row.setSpacing(12)
        brief_row.addWidget(brief_card, 2)
        brief_row.addWidget(pi_card, 2)
        layout.addLayout(brief_row)

        stats_grid = QGridLayout()
        stat_items = [
            "Total Records",
            "Avg Flowrate",
            "Avg Pressure",
            "Avg Temperature",
            "Equipment Types",
        ]
        for idx, name in enumerate(stat_items):
            card = QFrame()
            card.setObjectName("StatCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            label = QLabel(name)
            label.setObjectName("StatLabel")
            card_layout.addWidget(label)
            card_layout.addWidget(self.stat_cards[name])
            stats_grid.addWidget(card, idx // 3, idx % 3)
        layout.addLayout(stats_grid)

        table_card = QFrame()
        table_card.setObjectName("Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 10, 12, 10)
        table_title = QLabel("Equipment Records")
        table_title.setObjectName("SectionTitle")
        table_layout.addWidget(table_title)
        table_layout.addWidget(self.table)

        charts_card = QFrame()
        charts_card.setObjectName("Card")
        charts_layout = QVBoxLayout(charts_card)
        charts_layout.setContentsMargins(12, 10, 12, 10)
        charts_title = QLabel("Process Visuals")
        charts_title.setObjectName("SectionTitle")
        charts_layout.addWidget(charts_title)
        charts_layout.addWidget(self.chart_canvas)

        layout.addWidget(table_card)
        layout.addWidget(charts_card)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return page

    def apply_theme(self, dark: bool):
        self.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)
        self.preview_canvas.set_theme(dark)
        self.chart_canvas.set_theme(dark)
        self.preview_canvas.update_charts(self.preview_dataset or {"summary": {"type_distribution": {}}, "rows": []})
        self.chart_canvas.update_charts(self.active_dataset or {"summary": {"type_distribution": {}}, "rows": []})

    def toggle_theme(self, state):
        if getattr(self, "_theme_sync", False):
            return
        self._theme_sync = True
        dark = state == Qt.Checked
        self.apply_theme(dark)
        self.theme_toggle_home.setChecked(dark)
        self.theme_toggle_detail.setChecked(dark)
        self._theme_sync = False

    def choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return
        self.selected_file_path = file_path
        self.selected_file_label.setText(os.path.basename(file_path))

    def refresh_datasets(self):
        try:
            response = requests.get(f"{API_BASE}/datasets/")
            datasets = response.json()
        except Exception:
            datasets = _read_cache().get("datasets", [])

        self.dataset_list.clear()
        for dataset in datasets:
            self.dataset_list.addItem(f"{dataset['id']} | {dataset['name']}")

        if datasets:
            self.load_preview_dataset(datasets[0]["id"])
        else:
            self.clear_preview()

    def load_preview_dataset(self, dataset_id: str):
        try:
            response = requests.get(f"{API_BASE}/datasets/{dataset_id}/?include_rows=1")
            data = response.json()
            self.preview_dataset = data
            self.update_recent_summary(data)
            self.preview_canvas.update_charts(data)
            cache = _read_cache()
            cache["last"] = data
            _write_cache(cache)
        except Exception:
            cached = _read_cache().get("last")
            if cached:
                self.preview_dataset = cached
                self.update_recent_summary(cached)
                self.preview_canvas.update_charts(cached)
            else:
                self.clear_preview()

    def clear_preview(self):
        self.recent_name_label.setText("Most Recent Dataset: None")
        self.recent_uploaded_label.setText("Uploaded: -")
        self.recent_stats_label.setText("Records: - | Avg Flow: - | Avg Pressure: - | Avg Temp: -")
        self.preview_dataset = None
        self.preview_canvas.update_charts({"summary": {"type_distribution": {}}, "rows": []})

    def upload_csv(self):
        if not self.selected_file_path:
            self.show_error("Please choose a CSV file first.")
            return
        file_path = self.selected_file_path
        try:
            with open(file_path, "rb") as handle:
                response = requests.post(f"{API_BASE}/upload/", files={"file": handle})
                if response.status_code >= 400:
                    raise RuntimeError(response.text)
                data = response.json()
            self.active_dataset = data
            self.refresh_datasets()
            self.update_summary(data)
            self.update_table(data)
            self.chart_canvas.update_charts(data)
            self.show_detail()
            cache = _read_cache()
            cache["last"] = data
            _write_cache(cache)
        except Exception:
            local_data = self.analyze_local_csv(file_path)
            self.active_dataset = local_data
            self.update_recent_summary(local_data)
            self.preview_canvas.update_charts(local_data)
            self.update_summary(local_data)
            self.update_table(local_data)
            self.chart_canvas.update_charts(local_data)
            self.show_detail()
            cache = _read_cache()
            cache["last"] = local_data
            _write_cache(cache)

    def on_dataset_selected(self, item):
        if item is None:
            item = self.dataset_list.currentItem()
        if item is None:
            return
        dataset_id = item.text().split("|")[0].strip()
        try:
            response = requests.get(f"{API_BASE}/datasets/{dataset_id}/?include_rows=1")
            data = response.json()
            self.active_dataset = data
            self.update_summary(data)
            self.update_table(data)
            self.chart_canvas.update_charts(data)
            self.show_detail()
            cache = _read_cache()
            cache["last"] = data
            _write_cache(cache)
        except Exception:
            cached = _read_cache().get("last")
            if cached:
                self.active_dataset = cached
                self.update_summary(cached)
                self.update_table(cached)
                self.chart_canvas.update_charts(cached)
                self.show_detail()
            else:
                self.show_error("Unable to load dataset details.")

    def show_uploads(self):
        self.stack.setCurrentIndex(0)

    def show_detail(self):
        self.stack.setCurrentIndex(1)

    def update_recent_summary(self, dataset):
        summary = dataset.get("summary") or dataset
        name = dataset.get("name") or "Unknown"
        uploaded = (
            dataset.get("uploaded_at")
            or dataset.get("created_at")
            or dataset.get("uploaded")
            or "-"
        )
        row_count = summary.get("row_count", 0)
        avg_flow = summary.get("avg_flowrate", 0.0)
        avg_pressure = summary.get("avg_pressure", 0.0)
        avg_temp = summary.get("avg_temperature", 0.0)
        types = len(summary.get("type_distribution", {}))

        self.recent_name_label.setText(f"Most Recent Dataset: {name}")
        self.recent_uploaded_label.setText(f"Uploaded {uploaded}")
        self.recent_stats_label.setText(
            f"Records: {row_count} | Avg Flow: {avg_flow:.2f} | "
            f"Avg Pressure: {avg_pressure:.2f} | Avg Temp: {avg_temp:.2f} | Types: {types}"
        )

    def update_summary(self, dataset):
        summary = dataset.get("summary") or dataset
        insights = summary.get("insights", {})
        type_dist = summary.get("type_distribution", {})

        name = dataset.get("name") or "Dataset"
        uploaded = (
            dataset.get("uploaded_at")
            or dataset.get("created_at")
            or dataset.get("uploaded")
            or "-"
        )
        self.detail_name_label.setText(name)
        self.detail_uploaded_label.setText(f"Uploaded {uploaded}")

        top_type = "-"
        top_count = 0
        if type_dist:
            top_type = max(type_dist, key=type_dist.get)
            top_count = type_dist.get(top_type, 0)

        brief = (
            f"The plant is running with a health score of {insights.get('health_score', 0)} "
            f"and a {insights.get('utilization_band', '-')} utilization band. "
            f"Average flowrate is {summary.get('avg_flowrate', 0):.2f}, "
            f"with pressure at {summary.get('avg_pressure', 0):.2f} "
            f"and temperature at {summary.get('avg_temperature', 0):.2f}.\n\n"
            f"Most common equipment: {top_type} ({top_count} units).\n\n"
            f"Stability index is {insights.get('stability_index', 0)} "
            f"and efficiency index is {insights.get('efficiency_index', 0)}."
        )
        self.brief_label.setText(brief)

        self.pi_values["Health Score"].setText(str(insights.get("health_score", "-")))
        self.pi_values["Stability Index"].setText(str(insights.get("stability_index", "-")))
        self.pi_values["Efficiency Index"].setText(str(insights.get("efficiency_index", "-")))
        self.pi_values["Utilization Band"].setText(str(insights.get("utilization_band", "-")))
        self.pi_values["Anomaly Rate"].setText(f"{insights.get('anomaly_rate', 0)}%")
        self.pi_values["Missing Ratio"].setText(f"{insights.get('missing_ratio', 0)}%")

        self._set_alerts(insights.get("alerts", []))

        self.stat_cards["Total Records"].setText(str(summary.get("row_count", 0)))
        self.stat_cards["Avg Flowrate"].setText(f"{summary.get('avg_flowrate', 0):.2f}")
        self.stat_cards["Avg Pressure"].setText(f"{summary.get('avg_pressure', 0):.2f}")
        self.stat_cards["Avg Temperature"].setText(f"{summary.get('avg_temperature', 0):.2f}")
        self.stat_cards["Equipment Types"].setText(str(len(type_dist)))

    def _set_alerts(self, alerts):
        while self.alerts_layout.count():
            item = self.alerts_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not alerts:
            alerts = ["No critical alerts. System within normal bands."]
        for message in alerts:
            label = QLabel(message)
            label.setWordWrap(True)
            self.alerts_layout.addWidget(label)

    def update_table(self, dataset):
        rows = dataset.get("rows") or []
        if not rows:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        columns = dataset.get("columns") or list(rows[0].keys())
        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(columns)
        for row_idx, row in enumerate(rows):
            for col_idx, col in enumerate(columns):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row.get(col, ""))))
        self.table.resizeColumnsToContents()

    def analyze_local_csv(self, file_path):
        df = pd.read_csv(file_path)
        df = _normalize_dataframe(df)
        df = _coerce_numeric(df)
        columns = list(df.columns)
        rows = df.fillna("").to_dict(orient="records")

        summary = {
            "row_count": int(len(df)),
            "avg_flowrate": float(df["Flowrate"].mean(skipna=True)),
            "avg_pressure": float(df["Pressure"].mean(skipna=True)),
            "avg_temperature": float(df["Temperature"].mean(skipna=True)),
            "type_distribution": df["Type"].fillna("Unknown").value_counts().to_dict(),
            "columns": columns,
            "stats": {
                "flowrate": _series_stats(df["Flowrate"]),
                "pressure": _series_stats(df["Pressure"]),
                "temperature": _series_stats(df["Temperature"]),
            },
            "insights": calculate_insights(df),
        }
        local_id = f"local:{uuid.uuid4().hex[:8]}"
        uploaded = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "id": local_id,
            "name": os.path.basename(file_path),
            "uploaded_at": uploaded,
            "columns": columns,
            "rows": rows,
            "summary": summary,
        }

    def download_pdf(self):
        if not self.active_dataset:
            self.show_error("No dataset selected.")
            return
        dataset_id = self.active_dataset.get("id")
        if not dataset_id or str(dataset_id).startswith("local:"):
            self.show_error("PDF download requires an online dataset.")
            return
        default_name = f"{self.active_dataset.get('name', 'dataset')}_report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return
        try:
            response = requests.get(f"{API_BASE}/datasets/{dataset_id}/report/")
            if response.status_code >= 400:
                raise RuntimeError(response.text)
            with open(file_path, "wb") as handle:
                handle.write(response.content)
        except Exception as exc:
            self.show_error(f"Download failed: {exc}")

    def export_charts_png(self):
        if not self.active_dataset:
            self.show_error("No dataset selected.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Select folder to save chart")
        if not folder:
            return
        base = os.path.splitext(self.active_dataset.get("name", "charts"))[0]
        file_path = os.path.join(folder, f"{base}_charts.png")
        try:
            self.chart_canvas.figure.savefig(file_path, dpi=150)
        except Exception as exc:
            self.show_error(f"Export failed: {exc}")

    def show_error(self, message):
        QMessageBox.warning(self, "Error", message)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
