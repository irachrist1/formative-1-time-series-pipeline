"""Build the self-contained HTML report and final PDF submission."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs/figures"
TABLES = ROOT / "outputs/tables"
REPORTS = ROOT / "reports"
PDF_DIR = ROOT / "output/pdf"
REPORTS.mkdir(exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

findings = json.loads((TABLES / "analytical_findings.json").read_text())
metrics = json.loads((TABLES / "model_metrics.json").read_text())
query_results = json.loads((TABLES / "database_query_results_actual.json").read_text())
prediction = json.loads((TABLES / "prediction_api_sql_result.json").read_text())
team = json.loads((REPORTS / "team_details.json").read_text())
experiments = pd.read_csv(TABLES / "model_experiments.csv")


def image_data(name: str) -> str:
    encoded = base64.b64encode((FIG / name).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def code_block(text: str) -> str:
    return f"<pre><code>{html.escape(text.strip())}</code></pre>"


def build_html() -> Path:
    member_rows = "".join(
        f"<tr><td>{html.escape(m['name'])}</td><td>{html.escape(m['student_id'])}</td><td>{html.escape(m['contribution'])}</td></tr>"
        for m in team["members"]
    )
    experiment_rows = "".join(
        f"<tr><td>{r.experiment}</td><td>{int(r.n_estimators)}</td><td>{'None' if pd.isna(r.max_depth) else int(r.max_depth)}</td><td>{int(r.min_samples_leaf)}</td><td>{r.validation_mae:.2f}</td><td>{r.validation_rmse:.2f}</td><td>{r.validation_r2:.4f}</td></tr>"
        for r in experiments.itertuples()
    )
    endpoints = [
        ("POST", "/sql/records", "Create a SQL record"), ("GET", "/sql/records/{id}", "Read one SQL record"),
        ("PUT", "/sql/records/{id}", "Update a SQL record"), ("DELETE", "/sql/records/{id}", "Delete a SQL record"),
        ("GET", "/sql/records/latest", "Latest SQL record"), ("GET", "/sql/records?start=&end=", "SQL date range"),
        ("POST", "/mongo/records", "Create a MongoDB document"), ("GET", "/mongo/records/{id}", "Read one MongoDB document"),
        ("PUT", "/mongo/records/{id}", "Update a MongoDB document"), ("DELETE", "/mongo/records/{id}", "Delete a MongoDB document"),
        ("GET", "/mongo/records/latest", "Latest MongoDB document"), ("GET", "/mongo/records?start=&end=", "MongoDB date range"),
    ]
    endpoint_rows = "".join(f"<tr><td><span class='method'>{m}</span></td><td><code>{html.escape(p)}</code></td><td>{d}</td></tr>" for m, p, d in endpoints)

    sql_query = """SELECT tr.date_time, tr.traffic_volume, wc.weather_main
FROM traffic_records tr
JOIN weather_conditions wc ON wc.id = tr.weather_condition_id
ORDER BY tr.date_time DESC
LIMIT 1;"""
    mongo_query = """db.traffic_records.aggregate([
  {$group: {
    _id: "$weather.weather_main",
    average_traffic: {$avg: "$traffic_volume"},
    hourly_records: {$sum: 1}
  }},
  {$sort: {average_traffic: -1}}
]);"""
    prediction_commands = "python scripts/predict_from_api.py --database sql\npython scripts/predict_from_api.py --database mongo"
    reproduction_commands = "python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\npython scripts/run_analysis.py\npython scripts/seed_databases.py\nuvicorn src.api.main:app --reload\npytest -q"

    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Metro Traffic Time Series Pipeline</title>
<style>
:root{{--cream:#f7f4ef;--ink:#1a1a1a;--muted:#77776e;--border:#e0dbd2;--blue:#2e4780;--light:#eaf1fe;--card:#fff}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:var(--cream);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
nav{{position:fixed;z-index:10;top:16px;left:50%;transform:translateX(-50%);max-width:calc(100vw - 32px);display:flex;gap:6px;padding:7px;background:rgba(255,255,255,.94);border:1px solid var(--border);border-radius:999px;overflow:auto;box-shadow:0 8px 30px rgba(0,0,0,.08)}} nav a{{white-space:nowrap;color:var(--muted);text-decoration:none;padding:7px 11px;border-radius:999px;font-size:13px}} nav a.active,nav a:hover{{background:var(--light);color:var(--blue)}}
main{{width:min(1040px,calc(100% - 32px));margin:auto;padding:100px 0 70px}} section{{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:48px;margin-bottom:24px}} .hero{{min-height:75vh;display:flex;flex-direction:column;justify-content:center;background:var(--blue);color:white}} h1,h2,h3{{font-family:Georgia,serif;font-weight:400;letter-spacing:-.02em;line-height:1.12}} h1{{font-size:clamp(44px,7vw,78px);max-width:850px;margin:0 0 24px}} h2{{font-size:38px;margin:0 0 22px}} h3{{font-size:25px;margin:38px 0 12px}} .eyebrow{{text-transform:uppercase;letter-spacing:.15em;font-size:12px;color:#cedffe}} .hero p{{max-width:720px;font-size:19px;color:#eaf1fe}} .meta{{display:flex;gap:12px;flex-wrap:wrap;margin-top:30px}} .chip{{padding:7px 12px;border:1px solid rgba(255,255,255,.35);border-radius:999px;font-size:13px}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}} .stat{{padding:20px;border:1px solid var(--border);border-radius:14px;background:#fcfcfd}} .stat strong{{display:block;font:30px Georgia,serif;color:var(--blue)}} .note{{padding:18px 20px;border-left:4px solid var(--blue);background:var(--light);border-radius:0 12px 12px 0}} img.chart{{width:100%;height:auto;margin:18px 0 8px;border-radius:10px}} table{{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}} th,td{{padding:11px 10px;text-align:left;border-bottom:1px solid var(--border);vertical-align:top}} th{{color:var(--blue);font-weight:650}} pre{{background:#171b26;color:#edf1fa;border-radius:12px;padding:18px;overflow:auto;font:13px/1.55 "SFMono-Regular",Consolas,monospace}} code{{font-family:"SFMono-Regular",Consolas,monospace}} .method{{font-weight:700;color:var(--blue)}} .two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} .card{{border:1px solid var(--border);padding:20px;border-radius:14px}} footer{{color:var(--muted);text-align:center;padding:20px}}
@media(max-width:760px){{section{{padding:26px}}.summary,.two{{grid-template-columns:1fr}}}}
@media print{{nav{{display:none}}body{{background:white}}main{{width:100%;padding:0}}section{{border:0;border-radius:0;page-break-before:always;margin:0;padding:16mm}}.hero{{page-break-before:auto;min-height:250mm}}img.chart{{break-inside:avoid}}}}
</style></head><body>
<nav aria-label="Report chapters"><a href="#title">Title</a><a href="#summary">Summary</a><a href="#task1">Task 1</a><a href="#model">Model</a><a href="#task2">Task 2</a><a href="#task3">Task 3</a><a href="#task4">Task 4</a><a href="#team">Team</a></nav>
<main>
<section id="title" class="hero"><div class="eyebrow">{html.escape(team['course'])}</div><h1>Metro Interstate Traffic Volume Forecasting Pipeline</h1><p>{html.escape(team['assignment'])}. A complete pipeline from time series cleaning and forecasting to MySQL, MongoDB, CRUD APIs and a live prediction client.</p><div class="meta"><span class="chip">48,204 raw observations</span><span class="chip">October 2012 to September 2018</span><span class="chip">Hourly forecasting</span></div></section>
<section id="summary"><h2>The pipeline predicts hourly traffic and serves it through two databases</h2><div class="summary"><div class="stat"><strong>{metrics['test_mae']:.1f}</strong>test MAE</div><div class="stat"><strong>{metrics['test_rmse']:.1f}</strong>test RMSE</div><div class="stat"><strong>{metrics['test_r2']:.3f}</strong>test R squared</div><div class="stat"><strong>1,000</strong>records seeded in each database</div></div><p>The selected random forest reproduced the strong daily and weekly traffic cycle on an untouched final test period. Lagged traffic was the most useful source of information. The same cleaned data was implemented in a normalized MySQL schema and a nested MongoDB collection. FastAPI provides complete create, read, update and delete operations plus latest record and date range queries for both systems.</p><div class="note"><strong>Scope:</strong> Results apply to westbound I 94 at Minnesota Department of Transportation station ATR 301. They should not be directly generalized to Rwanda or to another road without retraining.</div></section>
<section id="task1"><h2>Task 1: Preprocessing and exploratory analysis</h2><h3>Problem definition and dataset choice</h3><p>The target is <code>traffic_volume</code>, the number of westbound vehicles recorded in an hour. Forecasting this measure can support traffic management and road planning. The Kaggle dataset was selected because it combines a clear timestamp, a useful regression target, weather measurements, holidays and more than six years of observations.</p><div class="summary"><div class="stat"><strong>48,204</strong>raw rows</div><div class="stat"><strong>40,575</strong>unique observed hours</div><div class="stat"><strong>7,629</strong>repeated timestamps</div><div class="stat"><strong>11,976</strong>absent hours</div></div><h3>Missing values and repeated timestamps</h3><p>The raw holiday value <code>None</code> means no holiday, so it was converted to <code>No Holiday</code>. Seventeen fully duplicated rows were removed. Repeated timestamps occur when one hour has several weather descriptions. They were aggregated into one hourly record by averaging numeric measures and combining weather text. The complete hourly index exposed 11,976 absent hours. Only internal gaps of three hours or less were interpolated. Longer gaps stayed missing and were excluded when a lag depended on them. This method preserves usable short sequences without creating long artificial traffic histories.</p><img class="chart" src="{image_data('traffic_distribution.png')}" alt="Traffic distribution"><p>The distribution spans zero to 7,280 vehicles per hour and reflects a mixture of quiet overnight periods and busy commuting periods. The mean is 3,260 and the median is 3,380 vehicles per hour.</p><h3>Question 1: Is there a long term trend?</h3><img class="chart" src="{image_data('q1_monthly_trend.png')}" alt="Monthly traffic trend"><p>The first twelve months averaged {findings['q1']['first_12_month_mean']:,.0f} vehicles per hour and the last twelve averaged {findings['q1']['last_12_month_mean']:,.0f}. The increase is only {findings['q1']['percent_change']:.1f} percent, therefore the series is better described as seasonal and variable than steadily increasing.</p><h3>Question 2: When is traffic busiest?</h3><img class="chart" src="{image_data('q2_hour_weekday_heatmap.png')}" alt="Hour weekday heatmap"><p>The strongest mean occurs on {findings['q2']['peak_weekday']} at {findings['q2']['peak_hour']:02d}:00, about {findings['q2']['peak_mean']:,.0f} vehicles per hour. Weekday commuter hours are much busier than overnight and weekend periods.</p><h3>Question 3: Does weather relate to traffic?</h3><img class="chart" src="{image_data('q3_weather_comparison.png')}" alt="Weather comparison"><p>Among categories with at least 100 observations, {findings['q3']['highest_weather']} has the highest mean at {findings['q3']['highest_mean']:,.0f}, while {findings['q3']['lowest_weather']} has the lowest at {findings['q3']['lowest_mean']:,.0f}. This is an association rather than a causal effect because weather categories also occur at different seasons and times.</p><h3>Question 4: Do lagged traffic values help?</h3><img class="chart" src="{image_data('q4_lag_correlations.png')}" alt="Lag correlations"><p>The previous hour correlation is {findings['q4']['Previous hour']:.3f}, yesterday at the same hour is {findings['q4']['Same hour yesterday']:.3f}, and last week at the same hour is {findings['q4']['Same hour last week']:.3f}. The weekly lag is strongest, which confirms a repeating weekly schedule.</p><h3>Question 5: What do moving averages show?</h3><img class="chart" src="{image_data('q5_moving_averages.png')}" alt="Moving averages"><p>During August 2018, hourly traffic had a standard deviation of {findings['q5']['hourly_std']:,.0f}. The 24 hour moving average reduced this to {findings['q5']['ma24_std']:,.0f}, and the 168 hour average reduced it to {findings['q5']['ma168_std']:,.0f}. The weekly moving average reveals the baseline, while the daily average reacts faster.</p><h3>Question 6: How does traffic differ by temperature?</h3><img class="chart" src="{image_data('q6_temperature_bands.png')}" alt="Temperature bands"><p>Moderate and warm temperature bands contain higher average traffic than very cold periods. The band above 30 degrees Celsius has few observations, so its high mean is not strong evidence by itself. Calendar and lag variables remain more reliable predictors.</p></section>
<section id="model"><h2>The tuned random forest generalizes to the final months</h2><p>Calendar, weather, 1 hour, 24 hour and 168 hour lags, plus 24 hour and 168 hour past only moving averages were used. Rows were ordered by time and split 70 percent for training, 15 percent for validation, and 15 percent for testing. A random split was avoided because future records must not influence earlier training.</p><table><thead><tr><th>Experiment</th><th>Trees</th><th>Depth</th><th>Min leaf</th><th>Validation MAE</th><th>Validation RMSE</th><th>Validation R squared</th></tr></thead><tbody>{experiment_rows}</tbody></table><p>RF 2 was selected because it produced the lowest validation RMSE. It was refitted using training plus validation data, then evaluated once on {metrics['test_rows']:,} unseen test rows from January to September 2018. Test MAE was {metrics['test_mae']:.2f}, RMSE was {metrics['test_rmse']:.2f}, and R squared was {metrics['test_r2']:.4f}.</p><img class="chart" src="{image_data('model_test_predictions.png')}" alt="Actual and predicted traffic"><p>The forecast follows the repeating daily peaks and overnight lows closely. Errors remain around sudden deviations and unusual days, which is expected because a random forest returns patterns learned from history.</p><img class="chart" src="{image_data('model_feature_importance.png')}" alt="Feature importance"><p>Lag and calendar features dominate the model. This agrees with the earlier analytical findings and shows that traffic history is more informative than weather alone.</p></section>
<section id="task2"><h2>Task 2: MySQL and MongoDB designs support time ordered access</h2><h3>Relational schema</h3><p>The MySQL design uses four tables. Locations and weather conditions avoid repeating descriptive text, traffic records store the hourly measures, and model predictions preserve forecast history. Unique and time indexes protect one observation per station and make latest and date range queries efficient.</p><img class="chart" src="{image_data('sql_erd.png')}" alt="SQL ERD"><h3>MongoDB collection</h3><p>MongoDB stores one document per hour. Weather text is embedded because it is read with the traffic measurement. A unique ascending index on <code>date_time</code> protects chronological uniqueness. A compound <code>location_id</code> and descending <code>date_time</code> index supports station history and latest record retrieval.</p><div class="two"><div>{code_block(sql_query)}</div><div>{code_block(mongo_query)}</div></div><h3>Executed query evidence</h3><table><thead><tr><th>Database</th><th>Query</th><th>Result from 1,000 seeded rows</th></tr></thead><tbody><tr><td>MySQL</td><td>Latest record</td><td>30 September 2018 23:00, volume 954, Clouds</td></tr><tr><td>MySQL</td><td>1 to 7 September range</td><td>{query_results['sql']['date_range']['row_count']} hourly rows</td></tr><tr><td>MySQL</td><td>Average by weather</td><td>Clouds ranked first at {query_results['sql']['average_by_weather'][0]['average_traffic']:,.2f}</td></tr><tr><td>MongoDB</td><td>Latest record</td><td>30 September 2018 23:00, volume 954, Clouds</td></tr><tr><td>MongoDB</td><td>1 to 7 September range</td><td>{query_results['mongodb']['date_range']['row_count']} hourly documents</td></tr><tr><td>MongoDB</td><td>Average by weather</td><td>Clouds ranked first at {query_results['mongodb']['average_by_weather'][0]['average_traffic']:,.2f}</td></tr></tbody></table></section>
<section id="task3"><h2>Task 3: Both databases expose complete CRUD and time series routes</h2><p>FastAPI provides matching behavior for SQL and MongoDB. Pydantic validates temperature, precipitation, cloud percentage and nonnegative traffic values. Duplicate timestamps return HTTP 409, missing IDs return HTTP 404, and invalid MongoDB IDs return HTTP 422.</p><table><thead><tr><th>Method</th><th>Endpoint</th><th>Purpose</th></tr></thead><tbody>{endpoint_rows}</tbody></table><p>Automated integration tests create, read, update and delete a record in each database. They also verify latest record and date range behavior. The complete suite passes, and FastAPI generates interactive documentation at <code>/docs</code>.</p></section>
<section id="task4"><h2>Task 4: The prediction client runs from API response to forecast</h2><p>The script first requests the latest record, then requests the preceding fourteen days from either the SQL or MongoDB endpoint. It parses timestamps, recreates the same calendar, lag and moving average features used during training, loads the saved RF 2 artifact, and predicts the latest record.</p><div class="summary"><div class="stat"><strong>{prediction['history_records_used']}</strong>API records used</div><div class="stat"><strong>{prediction['actual_traffic_volume']}</strong>actual volume</div><div class="stat"><strong>{prediction['predicted_traffic_volume']:.0f}</strong>predicted volume</div><div class="stat"><strong>{prediction['absolute_error']:.0f}</strong>absolute error</div></div>{code_block(prediction_commands)}<p>Both routes produced {prediction['predicted_traffic_volume']:.2f} vehicles per hour for 30 September 2018 at 23:00. This confirms the required integration works with either database implementation.</p></section>
<section id="team"><h2>Team participation and repository</h2><table><thead><tr><th>Member</th><th>Student ID</th><th>Major component</th></tr></thead><tbody>{member_rows}</tbody></table><p><strong>GitHub repository:</strong> {html.escape(team['github_url'])}</p><p>Each member should make at least four meaningful commits under their own GitHub account. Suggested commit groups are data setup, analytical questions, model experiments, database design, API routes, prediction integration, tests and final documentation.</p><h3>Reproduction commands</h3>{code_block(reproduction_commands)}<h3>Conclusion</h3><p>The project meets the four technical tasks in one reproducible repository. The strongest analytical result is the repeated weekly traffic pattern, which explains why lag features improve forecasting. The databases and API retain the same time ordered structure, and the final script demonstrates that a stored model can consume live API records and return a forecast.</p><h3>Dataset reference</h3><p>Metro Interstate Traffic Volume, Kaggle. Original traffic measurements from the Minnesota Department of Transportation and distributed through the UCI Machine Learning Repository. Kaggle URL: https://www.kaggle.com/datasets/anshtanwar/metro-interstate-traffic-volume</p></section>
</main><footer>Formative 1, Metro Interstate Traffic Volume Forecasting Pipeline</footer>
<script>const links=[...document.querySelectorAll('nav a')];const obs=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting){{links.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id))}}}}),{{rootMargin:'-30% 0px -60% 0px'}});document.querySelectorAll('section').forEach(s=>obs.observe(s));</script>
</body></html>"""
    output = REPORTS / "final_report.html"
    output.write_text(body, encoding="utf-8")
    return output


INK = colors.HexColor("#1F2430")
BLUE = colors.HexColor("#2E4780")
LIGHT_BLUE = colors.HexColor("#EAF1FE")
MUTED = colors.HexColor("#6F768A")
GRID = colors.HexColor("#D7DBE7")


def build_pdf() -> Path:
    output = PDF_DIR / "metro_traffic_pipeline_report.pdf"
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm, title="Metro Interstate Traffic Volume Forecasting Pipeline",
        author=team["group_name"],
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=32, textColor=BLUE, alignment=TA_LEFT, spaceAfter=18))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=BLUE, spaceBefore=8, spaceAfter=10))
    styles.add(ParagraphStyle(name="Subsection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=INK, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="Body2", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.3, leading=14, textColor=INK, spaceAfter=8))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.6, leading=10.5, textColor=MUTED, spaceAfter=5))
    styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, backColor=LIGHT_BLUE, borderColor=BLUE, borderWidth=0.8, borderPadding=9, spaceBefore=8, spaceAfter=10))
    styles.add(ParagraphStyle(name="CodeCustom", fontName="Courier", fontSize=6.3, leading=8.2, textColor=INK, borderPadding=8, spaceBefore=5, spaceAfter=9))

    story = []
    P = lambda text, style="Body2": story.append(Paragraph(text, styles[style]))
    H1 = lambda text: P(text, "Section")
    H2 = lambda text: P(text, "Subsection")
    def pic(name, width=6.9 * inch):
        img = Image(str(FIG / name))
        ratio = img.imageHeight / img.imageWidth
        img.drawWidth = width
        img.drawHeight = width * ratio
        story.append(img)
        story.append(Spacer(1, 5))
    def table(data, widths=None, font=7.5):
        t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), BLUE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), font), ("LEADING", (0, 0), (-1, -1), font + 3),
            ("GRID", (0, 0), (-1, -1), 0.35, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FCFCFD")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t); story.append(Spacer(1, 8))
    def pdf_code(text):
        lines = [html.escape(line).replace(" ", "&nbsp;") for line in text.strip().splitlines()]
        story.append(Paragraph("<br/>".join(lines), styles["CodeCustom"]))

    story += [Spacer(1, 32 * mm)]
    P("FORMATIVE 1", "Small")
    P("Metro Interstate Traffic Volume Forecasting Pipeline", "CoverTitle")
    P("A complete time series pipeline covering preprocessing, exploratory analysis, forecasting, MySQL, MongoDB, CRUD APIs and integrated prediction.", "Body2")
    story += [Spacer(1, 16 * mm)]
    table([["Dataset", "Time range", "Target"], ["Metro Interstate Traffic Volume", "2 Oct 2012 to 30 Sep 2018", "Hourly traffic volume"]], [65 * mm, 60 * mm, 45 * mm], 8)
    story += [Spacer(1, 30 * mm)]
    P(f"Course: {team['course']}<br/>Group: {team['group_name']}<br/>GitHub: {team['github_url']}", "Body2")
    story.append(PageBreak())

    H1("Technical summary")
    P(f"The project predicts hourly westbound traffic on Interstate 94 using weather, calendar, lag and moving average features. The selected RF 2 random forest achieved a test MAE of <b>{metrics['test_mae']:.2f}</b>, RMSE of <b>{metrics['test_rmse']:.2f}</b> and R squared of <b>{metrics['test_r2']:.4f}</b> on the final chronological test period.")
    P("The strongest evidence is the repeated weekly traffic pattern. Traffic one week earlier has a correlation of 0.944 with current traffic. A normalized four table MySQL schema and a nested MongoDB collection store the same hourly records. FastAPI exposes complete CRUD operations plus latest and date range queries for both databases.")
    P("The end to end client fetched 337 records from the running API, recreated the training features, loaded the saved model and predicted 1,110.93 vehicles for the latest record. The actual volume was 954, giving an absolute error of 156.93 vehicles.", "Callout")
    H2("Project scope")
    P("The findings describe one westbound I 94 monitoring station between Minneapolis and St. Paul, Minnesota. The model should be retrained before use on another road or country because traffic schedules and road conditions differ.")
    H2("Repository outputs")
    table([["Component", "Evidence"], ["Task 1", "Executed notebook, seven analytical figures, cleaned CSV and model experiment table"], ["Task 2", "MySQL schema, ERD, MongoDB design, sample documents, queries and results"], ["Task 3", "FastAPI application and integration tests for SQL and MongoDB"], ["Task 4", "API prediction client and saved forecast result"]], [35 * mm, 135 * mm])
    story.append(PageBreak())

    H1("Task 1: Dataset understanding and preprocessing")
    H2("Problem definition and justification")
    P("The forecasting target is <b>traffic_volume</b>, the number of westbound vehicles recorded during an hour. Forecasts can help traffic managers understand expected congestion and plan road operations. This dataset is suitable because it has a clear timestamp, a continuous target, weather measurements, holiday labels and more than six years of observations.")
    table([["Item", "Observed value"], ["Raw shape", "48,204 rows and 9 columns"], ["Time range", "2 October 2012 09:00 to 30 September 2018 23:00"], ["Intended frequency", "Hourly"], ["Unique observed hours", "40,575"], ["Repeated timestamp rows", "7,629"], ["Fully duplicated rows", "17"], ["Absent hours after regular indexing", "11,976"]], [55 * mm, 115 * mm])
    H2("Missing data decisions")
    P("The holiday label <font name='Courier'>None</font> means a normal day, not an unknown value, so it was renamed <font name='Courier'>No Holiday</font>. Fully duplicated rows were removed. Repeated timestamps represent multiple weather descriptions during the same hour, so numeric values were averaged and categorical weather descriptions were combined.")
    P("The data was reindexed to an hourly timeline. Internal gaps of at most three hours were interpolated using time order. Longer gaps remained missing and model rows that depended on those gaps were removed. This approach uses nearby information for small interruptions without fabricating long traffic sequences.")
    pic("traffic_distribution.png", 6.6 * inch)
    P("Hourly volume ranges from zero to 7,280 vehicles. The mean is 3,260, the median is 3,380, and the standard deviation is 1,987. The broad shape reflects overnight lows and commuting peaks.")
    story.append(PageBreak())

    H1("Six analytical questions")
    H2("1. Does traffic have a long term increasing or decreasing trend?")
    pic("q1_monthly_trend.png", 6.65 * inch)
    P(f"The first twelve months averaged {findings['q1']['first_12_month_mean']:,.0f} vehicles per hour and the last twelve averaged {findings['q1']['last_12_month_mean']:,.0f}. The difference is {findings['q1']['percent_change']:.1f} percent. There is no strong monotonic trend; seasonal movement and data coverage create larger month to month changes.")
    H2("2. Which weekday and hour combination has the highest traffic?")
    pic("q2_hour_weekday_heatmap.png", 6.65 * inch)
    P(f"The highest mean occurs on {findings['q2']['peak_weekday']} at {findings['q2']['peak_hour']:02d}:00, with about {findings['q2']['peak_mean']:,.0f} vehicles per hour. Weekday commuter hours are consistently busier than overnight and weekend periods, supporting hour and weekday model features.")
    story.append(PageBreak())
    H2("3. Does traffic volume differ across weather conditions?")
    pic("q3_weather_comparison.png", 6.55 * inch)
    P(f"Among weather categories with at least 100 records, {findings['q3']['highest_weather']} has the highest mean at {findings['q3']['highest_mean']:,.0f}, while {findings['q3']['lowest_weather']} has the lowest at {findings['q3']['lowest_mean']:,.0f}. This result is descriptive because weather categories are also related to season and time of day.")
    H2("4. Is current traffic related to traffic 1, 24 and 168 hours earlier?")
    pic("q4_lag_correlations.png", 6.2 * inch)
    P(f"The 1 hour lag correlation is {findings['q4']['Previous hour']:.3f}, the 24 hour lag is {findings['q4']['Same hour yesterday']:.3f}, and the 168 hour lag is {findings['q4']['Same hour last week']:.3f}. The weekly lag is the strongest, showing that travel schedules repeat across weeks.")
    story.append(PageBreak())
    H2("5. What do 24 hour and 168 hour moving averages reveal?")
    pic("q5_moving_averages.png", 6.65 * inch)
    P(f"During August 2018 the hourly standard deviation was {findings['q5']['hourly_std']:,.0f}. The 24 hour moving average standard deviation was {findings['q5']['ma24_std']:,.0f}, while the 168 hour average was only {findings['q5']['ma168_std']:,.0f}. The weekly moving average gives a stable baseline and the daily average reacts faster. Both use only earlier traffic values.")
    H2("6. How does traffic differ by temperature range?")
    pic("q6_temperature_bands.png", 6.4 * inch)
    P("Traffic is not a simple linear function of temperature. Warm bands show higher averages, but the band above 30 degrees Celsius contains only 396 observations. Time of day and season can explain part of this difference, so temperature should be used with calendar and lag variables.")
    story.append(PageBreak())

    H1("Model experiments and validation")
    P("Features include temperature, rain, snow, clouds, hour, weekday, month, weekend and holiday flags, traffic lags at 1, 24 and 168 hours, and past only moving averages over 24 and 168 hours. The chronological split used 70 percent for training, 15 percent for validation and 15 percent for testing.")
    exp_data = [["Experiment", "Trees", "Depth", "Min leaf", "Val MAE", "Val RMSE", "Val R2"]]
    for r in experiments.itertuples():
        exp_data.append([r.experiment, int(r.n_estimators), "None" if pd.isna(r.max_depth) else int(r.max_depth), int(r.min_samples_leaf), f"{r.validation_mae:.2f}", f"{r.validation_rmse:.2f}", f"{r.validation_r2:.4f}"])
    table(exp_data, [25 * mm, 18 * mm, 18 * mm, 20 * mm, 25 * mm, 27 * mm, 24 * mm])
    P(f"RF 2 was selected using the lowest validation RMSE. After refitting on training plus validation data, it achieved test MAE {metrics['test_mae']:.2f}, RMSE {metrics['test_rmse']:.2f} and R squared {metrics['test_r2']:.4f} across {metrics['test_rows']:,} test rows.", "Callout")
    pic("model_test_predictions.png", 6.65 * inch)
    P("Predictions closely follow daily peaks and overnight lows during the last fourteen days. Remaining errors occur around abrupt deviations and unusual days.")
    pic("model_feature_importance.png", 6.1 * inch)
    P("Lag and calendar variables are the most important. This is consistent with the EDA and shows that repeated schedules are more predictive than weather alone.")
    story.append(PageBreak())

    H1("Task 2: Database design and implementation")
    H2("MySQL relational design")
    P("The normalized schema has four tables. Locations and weather conditions store reusable descriptions, traffic records store time varying measurements, and model predictions retain forecast history. Unique and time indexes support integrity and efficient chronological retrieval.")
    pic("sql_erd.png", 6.7 * inch)
    H2("MongoDB collection design")
    P("Each MongoDB document represents one hourly observation. Weather fields are embedded because they are normally read together. The collection uses a unique date_time index and a compound location_id plus descending date_time index. This supports latest record and range access without joins.")
    table([["Design", "MySQL", "MongoDB"], ["Main unit", "traffic_records row", "traffic_records document"], ["Weather", "Foreign key to weather_conditions", "Embedded weather object"], ["Location", "Foreign key to locations", "location_id field"], ["Time index", "date_time and location/date_time", "date_time and location/date_time"], ["Prediction history", "model_predictions table", "Can be a separate collection"]], [32 * mm, 70 * mm, 70 * mm])
    story.append(PageBreak())

    H1("Database queries and executed results")
    H2("MySQL query examples")
    pdf_code("""-- Latest record
SELECT tr.date_time, tr.traffic_volume, wc.weather_main
FROM traffic_records tr
JOIN weather_conditions wc ON wc.id = tr.weather_condition_id
ORDER BY tr.date_time DESC LIMIT 1;

-- Records by date range
SELECT date_time, traffic_volume FROM traffic_records
WHERE date_time BETWEEN '2018-09-01' AND '2018-09-07 23:59:59';

-- Average by weather
SELECT wc.weather_main, AVG(tr.traffic_volume), COUNT(*)
FROM traffic_records tr JOIN weather_conditions wc ON wc.id=tr.weather_condition_id
GROUP BY wc.weather_main ORDER BY AVG(tr.traffic_volume) DESC;""")
    H2("MongoDB query examples")
    pdf_code("""// Latest record
db.traffic_records.find({}).sort({date_time: -1}).limit(1)

// Records by date range
db.traffic_records.find({date_time: {$gte: ISODate('2018-09-01'),
  $lte: ISODate('2018-09-07T23:59:59Z')}}).sort({date_time: 1})

// Average by weather
db.traffic_records.aggregate([
  {$group: {_id: '$weather.weather_main',
    average_traffic: {$avg: '$traffic_volume'}, records: {$sum: 1}}},
  {$sort: {average_traffic: -1}}
])""")
    results_data = [["Database", "Query", "Executed result"], ["MySQL", "Latest", "30 Sep 2018 23:00, 954 vehicles, Clouds"], ["MySQL", "Date range", f"{query_results['sql']['date_range']['row_count']} rows from 1 to 7 September"], ["MySQL", "Weather average", f"Clouds first: {query_results['sql']['average_by_weather'][0]['average_traffic']:,.2f}"], ["MongoDB", "Latest", "30 Sep 2018 23:00, 954 vehicles, Clouds"], ["MongoDB", "Date range", f"{query_results['mongodb']['date_range']['row_count']} documents from 1 to 7 September"], ["MongoDB", "Weather average", f"Clouds first: {query_results['mongodb']['average_by_weather'][0]['average_traffic']:,.2f}"]]
    table(results_data, [30 * mm, 35 * mm, 105 * mm])
    P("Both services were installed locally and loaded with the same 1,000 recent hourly records. Matching results confirm that the two implementations represent the same data.")
    story.append(PageBreak())

    H1("Task 3: CRUD and time series endpoints")
    P("FastAPI provides matching operations for both storage systems. Input validation rejects unrealistic temperature, negative precipitation, invalid cloud percentages and negative traffic. Duplicate timestamps return HTTP 409 and missing records return HTTP 404.")
    endpoint_data = [["Method", "SQL endpoint", "MongoDB endpoint", "Purpose"], ["POST", "/sql/records", "/mongo/records", "Create"], ["GET", "/sql/records/{id}", "/mongo/records/{id}", "Read one"], ["PUT", "/sql/records/{id}", "/mongo/records/{id}", "Update"], ["DELETE", "/sql/records/{id}", "/mongo/records/{id}", "Delete"], ["GET", "/sql/records/latest", "/mongo/records/latest", "Latest"], ["GET", "/sql/records?start=&end=", "/mongo/records?start=&end=", "Date range"]]
    table(endpoint_data, [18 * mm, 55 * mm, 57 * mm, 32 * mm], 7)
    P("The automated integration test performs create, read, date range, latest, update and delete operations for SQL and MongoDB. The suite passes. Interactive OpenAPI documentation is available at <font name='Courier'>http://127.0.0.1:8000/docs</font> when the server runs.", "Callout")
    H2("Example create request")
    pdf_code("""POST /sql/records
{
  "date_time": "2018-10-01T00:00:00",
  "temp": 282.5,
  "rain_1h": 0.0,
  "snow_1h": 0.0,
  "clouds_all": 75,
  "weather_main": "Clouds",
  "weather_description": "broken clouds",
  "traffic_volume": 1000,
  "location_id": 1
}""")
    story.append(PageBreak())

    H1('<font color="#FFFFFF">XXXXXX</font>Task 4: Integrated prediction script')
    P("The prediction script requests the latest record and the previous fourteen days from either database route. It parses the timestamps, applies the same shifted lag and moving average logic used during training, loads the saved RF 2 artifact, and predicts the latest traffic volume.")
    table([["Field", "Observed result"], ["Database route", prediction["database"]], ["API history records", prediction["history_records_used"]], ["Record timestamp", prediction["date_time"].replace("T", " ")], ["Actual traffic", prediction["actual_traffic_volume"]], ["Predicted traffic", f"{prediction['predicted_traffic_volume']:.2f}"], ["Absolute error", f"{prediction['absolute_error']:.2f}"], ["Model", prediction["model"]]], [60 * mm, 110 * mm])
    pdf_code("""# Start the API
uvicorn src.api.main:app --reload

# Predict through either database
python scripts/predict_from_api.py --database sql
python scripts/predict_from_api.py --database mongo""")
    P("Both database routes returned the same feature history and produced the same forecast. This verifies the required path from an API record through preprocessing and model loading to a final prediction.")
    H2("Limitations and robustness")
    P("The random forest estimates expected traffic from historical patterns but does not establish causal weather effects. Missing periods reduce the usable training set. A single chronological holdout is appropriate for the assignment, while a production system should add rolling origin cross validation, a seasonal naive baseline, drift monitoring and retraining on newer local data.")
    story.append(PageBreak())

    H1("Team participation and reproducibility")
    member_data = [["Member", "Student ID", "Major contribution"]] + [[m["name"], m["student_id"], Paragraph(m["contribution"], styles["Small"])] for m in team["members"]]
    table(member_data, [42 * mm, 30 * mm, 98 * mm], 7)
    P(f"<b>GitHub repository:</b> {team['github_url']}")
    P("Each member should have at least four clear commits under their own GitHub account. Commit messages should identify meaningful work such as preprocessing, model experiments, database schema, API routes, tests or report evidence.", "Callout")
    H2("Reproduction")
    pdf_code("""python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_analysis.py
python scripts/seed_databases.py
uvicorn src.api.main:app --reload
pytest -q""")
    H2("Conclusion")
    P("The project implements the full requested pipeline in one structured repository. It includes documented preprocessing, six analytical questions, lag and moving average features, three tuned experiments, two database systems, complete CRUD endpoints, time series queries and an end to end API prediction.")
    H2("Dataset reference")
    P("Metro Interstate Traffic Volume, Kaggle. Original measurements from the Minnesota Department of Transportation and distributed through the UCI Machine Learning Repository.<br/>https://www.kaggle.com/datasets/anshtanwar/metro-interstate-traffic-volume", "Small")

    def page(canvas, document):
        canvas.saveState()
        if document.page > 1:
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(MUTED)
            canvas.drawString(18 * mm, 10 * mm, "Metro Interstate Traffic Volume Forecasting Pipeline")
            canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page, onLaterPages=page)
    return output


if __name__ == "__main__":
    print(build_html())
    print(build_pdf())
