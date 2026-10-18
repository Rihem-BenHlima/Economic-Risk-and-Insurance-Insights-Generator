"""Forecasts: pick a series and a model; see its history, its backtest, its forecast with the 80% band, and how every model scored on that series."""
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from data import MODEL_NAMES, TARGETS, last_year, result, table
from ui import graph, note, style


def layout():
    return html.Div([
        html.Div([html.Div([html.Label("Series", className="label"), dcc.Dropdown([{"label": v, "value": k} for k, v in TARGETS.items()], "premiums_total", id="fc-series", clearable=False, className="dropdown")]),
                  html.Div([html.Label("Model", className="label"), dcc.Dropdown([{"label": v, "value": k} for k, v in MODEL_NAMES.items()], "ensemble", id="fc-model", clearable=False, className="dropdown")])],
                 className="controls"),
        html.Div(dcc.Graph(id="fc-chart", config={"displayModeBar": False}), className="panel"),
        html.Div([html.Div(dcc.Graph(id="fc-compare", config={"displayModeBar": False}), className="panel"), html.Div(id="fc-table", className="panel")], className="grid", style={"gridTemplateColumns": "1fr 1fr"}),
        note("The backtest refits every model on past years only and forecasts 1 to 3 years ahead, from 2012 onwards. Error = MAPE, the average size of the miss as a percentage "
             "of the true value; lower is better. The final forecast is the ensemble, which averages the five models.")])


def register(app):
    @app.callback(Output("fc-chart", "figure"), Output("fc-compare", "figure"), Output("fc-table", "children"), Input("fc-series", "value"), Input("fc-model", "value"))
    def update(series, model):
        t, y = table(), last_year()
        F, B, M = result("forecasts"), result("backtest"), result("metrics")
        f = F[(F.series == series) & (F.model == model)]
        b = B[(B.series == series) & (B.model == model) & (B.step == 1)]
        fig = go.Figure()
        fig.add_scatter(x=t.index, y=t[series], name="Actual", mode="lines+markers", marker=dict(size=4), line=dict(color="#1b2a41"))
        fig.add_scatter(x=b.year, y=b.forecast, name="1-year-ahead backtest", mode="markers", marker=dict(color="#1f77b4", size=7))
        fig.add_scatter(x=list(f.year) + list(f.year)[::-1], y=list(f.upper_80) + list(f.lower_80)[::-1], mode="lines", fill="toself", fillcolor="rgba(214,39,40,0.15)", line=dict(width=0),
                        hoverinfo="skip", name="80% band")
        fig.add_scatter(x=[y] + list(f.year), y=[t[series][y]] + list(f.forecast), name="Forecast", mode="lines+markers", line=dict(color="#d62728", dash="dash"))
        for _, r in f.iterrows():
            fig.add_annotation(x=r.year, y=r.forecast, text=f"{r.forecast:,.0f}", showarrow=False, yshift=14, font=dict(size=11))
        fig.update_yaxes(title="M.TND")
        chart = style(fig, 420, f"{TARGETS[series]}: {MODEL_NAMES[model]}")
        s = M[(M.series == series) & (M.step == "ALL")].set_index("model")
        order = s["MAPE_%"].sort_values()
        bars = go.Figure(go.Bar(x=order.values, y=[MODEL_NAMES[m] for m in order.index], orientation="h", marker_color=["#d62728" if m == model else "#9db7d5" for m in order.index],
                                text=[f"{v:.2f}%" for v in order.values], textposition="outside"))
        bars.update_yaxes(autorange="reversed")
        bars.update_xaxes(title="average error, MAPE %")
        rows = [html.Tr([html.Th("Model"), html.Th("MAPE %"), html.Th("R²"), html.Th("MASE")])]
        for m in order.index:
            rows.append(html.Tr([html.Td(MODEL_NAMES[m]), html.Td(f"{s.loc[m, 'MAPE_%']:.2f}"), html.Td(f"{s.loc[m, 'R2']:.3f}"), html.Td(f"{s.loc[m, 'MASE']:.2f}")]))
        tbl = html.Div([html.H4("Scores on this series"), html.Table(rows, className="table"),
                        note("MASE below 1 means the model beats repeating last year's value. R² close to 1 means the forecasts follow the actual values closely.")])
        return chart, style(bars, 320, "Which model forecasts this series best"), tbl
