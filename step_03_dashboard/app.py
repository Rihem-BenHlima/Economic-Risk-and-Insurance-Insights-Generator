"""Tunisia Economic Risk & Insurance Insights: the dashboard.

Run:  python step_03_dashboard/app.py      then open the address it prints
Tabs: Overview, Insurance, Economy, Labour, Agriculture, Climate and risk, Forecasts.
Reads only CSV files: data/processed (step 1) and step_02_forecasting/results (step 2).
"""
import os
import sys
from pathlib import Path
from dash import Dash, Input, Output, dcc, html
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tabs import agriculture, climate, economy, forecasts, insurance, labour, overview
from ui import BG, INK, LINE, MUTED

TABS = [("overview", "Overview", overview), ("insurance", "Insurance", insurance), ("economy", "Economy", economy), ("labour", "Labour", labour),
        ("agriculture", "Agriculture", agriculture), ("climate", "Climate and risk", climate), ("forecasts", "Forecasts", forecasts)]

app = Dash(__name__, suppress_callback_exceptions=True, title="Tunisia Insurance Insights")
app.index_string = app.index_string.replace("</head>", f"""<style>
body {{ margin: 0; background: {BG}; color: {INK}; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
.header {{ background: {INK}; color: white; padding: 16px 28px; }} .header h1 {{ margin: 0; font-size: 22px; }} .header p {{ margin: 4px 0 0; color: #b8c4d6; font-size: 13px; }}
.main {{ max-width: 1280px; margin: 0 auto; padding: 18px 20px 40px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 14px; }}
.card {{ background: white; border: 1px solid {LINE}; border-radius: 10px; padding: 12px 14px; }}
.card-label {{ font-size: 12px; color: {MUTED}; }} .card-value {{ font-size: 22px; font-weight: 600; margin-top: 2px; }} .card-sub {{ font-size: 12px; margin-top: 2px; min-height: 15px; }}
.grid {{ display: grid; gap: 14px; }} .panel {{ background: white; border: 1px solid {LINE}; border-radius: 10px; padding: 8px 10px; margin-bottom: 14px; }}
.note {{ color: {MUTED}; font-size: 12.5px; line-height: 1.5; }} .label {{ font-size: 12px; color: {MUTED}; }}
.controls {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }}
.table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }} .table th, .table td {{ text-align: left; padding: 7px 8px; border-bottom: 1px solid {LINE}; }} .table th {{ color: {MUTED}; font-weight: 600; }}
.tab {{ padding: 10px 16px !important; border: none !important; background: transparent !important; color: {MUTED} !important; }}
.tab--selected {{ color: {INK} !important; font-weight: 600; border-bottom: 3px solid #1f77b4 !important; }}
@media (max-width: 900px) {{ .grid, .controls {{ grid-template-columns: 1fr !important; }} }}
</style></head>""")

app.layout = html.Div([
    html.Div([html.H1("Tunisia: economic risk and insurance insights"), html.P("Insurance, economy, labour, agriculture and climate, with forecasts of premiums and claims to 2027")], className="header"),
    html.Div([dcc.Tabs(id="tabs", value=os.environ.get("DASH_TAB", "overview"), children=[dcc.Tab(label=label, value=key, className="tab", selected_className="tab--selected") for key, label, _ in TABS]),
              html.Div(id="content", style={"marginTop": "14px"})], className="main")])


@app.callback(Output("content", "children"), Input("tabs", "value"))
def render(tab):
    return {key: mod for key, _, mod in TABS}[tab].layout()


agriculture.register(app)
forecasts.register(app)

if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("DASH_PORT", 8050)))
