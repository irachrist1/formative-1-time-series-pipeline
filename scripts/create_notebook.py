"""Create the reader-facing Task 1 notebook using nbformat."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
findings = json.loads((ROOT / "outputs/tables/analytical_findings.json").read_text())
metrics = json.loads((ROOT / "outputs/tables/model_metrics.json").read_text())

nb = nbf.v4.new_notebook()
cells = []
cells.append(nbf.v4.new_markdown_cell("""# Task 1: Time-series preprocessing, analysis and forecasting

## tl;dr

The dataset contains hourly traffic and weather observations for westbound I-94 from October 2012 to September 2018. Repeated timestamps were aggregated because one hour can contain more than one weather description. Short gaps up to three hours were interpolated, while longer gaps were kept missing so that we do not create too much artificial history.

Traffic has a strong hour-of-day and weekday pattern. Lagged traffic values are highly useful, and moving averages make the underlying daily and weekly levels easier to see. The selected random forest achieved a test RMSE of **{rmse:.2f} vehicles/hour**, MAE of **{mae:.2f}**, and R-squared of **{r2:.4f}** on the final chronological test period.""".format(rmse=metrics["test_rmse"], mae=metrics["test_mae"], r2=metrics["test_r2"])))

cells.append(nbf.v4.new_markdown_cell("""## Context & Methods

The forecasting target is `traffic_volume`, the number of westbound vehicles recorded in an hour. We use a chronological 70/15/15 split rather than a random split because a random split would allow future patterns to leak into training.

### Key assumptions

- Repeated timestamps describe the same traffic hour under multiple weather labels, so numeric weather values and traffic are averaged and categorical weather is combined.
- The text value `None` in the holiday column means a normal day. It is changed to `No Holiday`; it is not treated as an unknown missing value.
- Only internal gaps of three hours or less are interpolated. Longer gaps remain missing and model rows that depend on them are dropped.
- Lag and moving-average features are shifted by one hour. Therefore the current target is never included in its own predictors."""))

cells.append(nbf.v4.new_code_cell("""from pathlib import Path
import json
import sys
import pandas as pd
from IPython.display import Image, display

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

# Rebuild all data, figures, tables and the model from the raw CSV.
from scripts.run_analysis import main
main()"""))

cells.append(nbf.v4.new_markdown_cell("""## Data

The raw file has nine columns: timestamp, holiday, four numeric weather measures, two weather descriptions, and the traffic target. The intended granularity is hourly, but the raw timeline contains repeated timestamps and missing hours. The next cells show the saved quality summary and descriptive statistics."""))
cells.append(nbf.v4.new_code_cell("""quality = pd.read_csv(ROOT / "outputs/tables/data_quality_summary.csv", index_col=0)
quality"""))
cells.append(nbf.v4.new_code_cell("""statistics = pd.read_csv(ROOT / "outputs/tables/descriptive_statistics.csv", index_col=0)
statistics.loc[["temp", "rain_1h", "snow_1h", "clouds_all", "traffic_volume"], ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]"""))
cells.append(nbf.v4.new_markdown_cell("""## Results

### Question 1: Does traffic show an increasing or decreasing long-term trend?

Monthly traffic changes across the six years, but it does not follow one smooth straight trend. The average in the last twelve months was **{last:,.0f} vehicles/hour**, compared with **{first:,.0f}** in the first twelve months, a change of **{change:.1f}%**. Seasonal changes and gaps mean this should be interpreted as descriptive, not a causal change.""".format(first=findings["q1"]["first_12_month_mean"], last=findings["q1"]["last_12_month_mean"], change=findings["q1"]["percent_change"])))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/q1_monthly_trend.png'))"))

cells.append(nbf.v4.new_markdown_cell("""### Question 2: Which weekday and hour combinations have the highest traffic?

The heatmap shows a strong commuting cycle. The highest mean occurs on **{day} at {hour:02d}:00**, with about **{mean:,.0f} vehicles/hour**. Weekday morning and afternoon periods are clearly busier, while overnight hours and weekends are lower. This pattern supports using hour, weekday and weekend features in the model.""".format(day=findings["q2"]["peak_weekday"], hour=findings["q2"]["peak_hour"], mean=findings["q2"]["peak_mean"])))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/q2_hour_weekday_heatmap.png'))"))

cells.append(nbf.v4.new_markdown_cell("""### Question 3: Does traffic volume differ across weather conditions?

Among weather categories with at least 100 observations, **{high}** has the highest mean traffic at about **{high_mean:,.0f} vehicles/hour**, while **{low}** has the lowest at about **{low_mean:,.0f}**. Weather is associated with traffic, but this comparison is also affected by time of day and season, so it does not prove weather caused the difference.""".format(high=findings["q3"]["highest_weather"], high_mean=findings["q3"]["highest_mean"], low=findings["q3"]["lowest_weather"], low_mean=findings["q3"]["lowest_mean"])))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/q3_weather_comparison.png'))"))

lag_text = ", ".join(f"{name}: {value:.3f}" for name, value in findings["q4"].items())
cells.append(nbf.v4.new_markdown_cell(f"""### Question 4: Is current traffic related to traffic 1, 24 and 168 hours earlier?

Yes. The correlations are **{lag_text}**. The same-hour previous-day and previous-week lags capture repeated travel schedules, while the one-hour lag captures short-term continuity. These strong relationships justify lagged features in the forecasting model. Correlation still does not mean every individual hour behaves the same."""))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/q4_lag_correlations.png'))"))

cells.append(nbf.v4.new_markdown_cell("""### Question 5: What do 24-hour and 168-hour moving averages reveal?

The raw hourly series is volatile, with a standard deviation of **{hourly:,.0f} vehicles/hour** during August 2018. The 24-hour moving average reduces this to **{ma24:,.0f}**, and the 168-hour moving average reduces it further to **{ma168:,.0f}**. The weekly average therefore shows the baseline level clearly, while the daily average reacts faster. Both averages use only earlier observations to prevent leakage.""".format(hourly=findings["q5"]["hourly_std"], ma24=findings["q5"]["ma24_std"], ma168=findings["q5"]["ma168_std"])))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/q5_moving_averages.png'))"))

cells.append(nbf.v4.new_markdown_cell("""### Question 6: How does traffic differ across temperature ranges?

Traffic volume is not a simple linear function of temperature. Moderate temperature bands contain many normal commuting days and generally have higher mean traffic than extreme cold or heat bands. Temperature may be useful, but calendar and lag variables are more direct predictors of repeated travel behaviour."""))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/q6_temperature_bands.png'))"))

cells.append(nbf.v4.new_markdown_cell("""## Model experiments

Three random forest configurations were tuned using the middle chronological validation period. RMSE is the main selection metric because it penalizes large forecast errors, while MAE gives an easier average-error interpretation. The best configuration is refitted on the combined training and validation periods, then evaluated once on the untouched final test period."""))
cells.append(nbf.v4.new_code_cell("""experiments = pd.read_csv(ROOT / "outputs/tables/model_experiments.csv")
experiments.round(4)"""))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/model_test_predictions.png'))"))
cells.append(nbf.v4.new_code_cell("display(Image(filename=ROOT / 'outputs/figures/model_feature_importance.png'))"))

cells.append(nbf.v4.new_markdown_cell("""## Takeaways

- Traffic forecasting is mainly driven by repeated hourly and weekly behaviour.
- Lagged values and past-only moving averages are important and also satisfy the time-series feature requirement.
- Weather adds context, although descriptive weather comparisons are confounded by season and time of day.
- The selected model generalizes well to the final chronological period, but its performance applies to this I-94 station and should not be assumed for other roads.
- A future improvement would compare this random forest with a seasonal naive baseline and a gradient boosting model over several rolling validation windows."""))

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.9"},
}
output = ROOT / "notebooks/01_time_series_analysis.ipynb"
nbf.write(nb, output)
print(output)

