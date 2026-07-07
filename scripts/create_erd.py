"""Render the relational database ERD as a report-ready image."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/figures/sql_erd.png"

fig, ax = plt.subplots(figsize=(12, 7), facecolor="#FCFCFD")
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis("off")

tables = {
    "locations": (0.5, 4.05, 3.0, 2.25, ["PK  id", "UK  station_code", "road_name", "direction", "city", "state"]),
    "weather_conditions": (0.5, 0.65, 3.0, 2.0, ["PK  id", "weather_main", "weather_description", "UK  main + description"]),
    "traffic_records": (4.5, 2.0, 3.35, 3.65, ["PK  id", "FK  location_id", "FK  weather_condition_id", "date_time", "holiday", "temp / rain / snow", "clouds_all", "traffic_volume", "UK  location + timestamp"]),
    "model_predictions": (8.8, 2.7, 2.8, 2.35, ["PK  id", "FK  traffic_record_id", "predicted_volume", "model_version", "created_at"]),
}

for name, (x, y, w, h, fields) in tables.items():
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", facecolor="white", edgecolor="#D7DBE7", linewidth=1.2)
    ax.add_patch(box)
    ax.add_patch(FancyBboxPatch((x, y + h - 0.46), w, 0.46, boxstyle="round,pad=0.02,rounding_size=0.08", facecolor="#2E4780", edgecolor="#2E4780"))
    ax.text(x + 0.15, y + h - 0.23, name.upper(), va="center", ha="left", fontsize=10, color="white", fontweight="bold")
    line_y = y + h - 0.75
    for field in fields:
        ax.text(x + 0.16, line_y, field, va="center", ha="left", fontsize=8.5, color="#1F2430", family="monospace")
        line_y -= 0.33

def relation(start, end, label):
    arrow = FancyArrowPatch(start, end, arrowstyle="|-|", mutation_scale=10, linewidth=1.3, linestyle="--", color="#7A828F", connectionstyle="arc3,rad=0")
    ax.add_patch(arrow)
    ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.16, label, fontsize=8, color="#6F768A", ha="center", bbox={"facecolor": "#FCFCFD", "edgecolor": "none", "pad": 1})

relation((3.5, 5.05), (4.5, 4.8), "1 to many")
relation((3.5, 1.65), (4.5, 2.75), "1 to many")
relation((7.85, 3.8), (8.8, 3.8), "1 to many")

fig.text(0.065, 0.95, "Relational database design", fontsize=17, fontweight="semibold", color="#1F2430")
fig.text(0.065, 0.915, "Normalized MySQL schema for hourly traffic, weather, location and forecasts", fontsize=10, color="#6F768A")
fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="#FCFCFD")
plt.close(fig)
print(OUT)

