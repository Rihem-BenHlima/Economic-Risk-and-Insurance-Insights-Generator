"""Overview: the key figures of the latest year and the final forecast (the ensemble) of the five series."""
import plotly.graph_objects as go
from dash import html
from data import TARGETS, last_year, result, table
from ui import card, cards, graph, grid, note, pct


def layout():
    t, y = table(), last_year()
    prem, claims = t.premiums_total, t.claims_paid_total
    g_prem = 100 * (prem[y] / prem[y - 1] - 1)
    F = result("forecasts")
    F = F[F.model == "ensemble"]
    tot = F[F.series == "premiums_total"].set_index("year")
    kpis = cards(
        card(f"Premiums {y}", f"{prem[y]:,.0f} M.TND", f"{pct(g_prem)} vs {y - 1}", good=g_prem > 0),
        card(f"Paid claims {y}", f"{claims[y]:,.0f} M.TND", f"{pct(100 * (claims[y] / claims[y - 1] - 1))} vs {y - 1}"),
        card("Claims / premiums", f"{100 * claims[y] / prem[y]:.0f}%", "all branches"),
        card(f"Premiums {y + 3} (forecast)", f"{tot.forecast[y + 3]:,.0f} M.TND", f"80% band {tot.lower_80[y + 3]:,.0f} to {tot.upper_80[y + 3]:,.0f}"),
        card("Real GDP growth", f"{t.gdp_growth_pct[y]:.1f}%", f"inflation {t.inflation_pct[y]:.1f}%"),
        card("Unemployment", f"{t.unemployment_rate[y]:.1f}%", f"{y}"))
    fig = go.Figure()
    fig.add_scatter(x=t.index, y=prem, name="Total premiums", mode="lines+markers", marker=dict(size=4))
    fig.add_scatter(x=t.index, y=claims, name="Paid claims", mode="lines+markers", marker=dict(size=4))
    for s, col in (("premiums_total", "#1f77b4"), ("claims_paid_total", "#ff7f0e")):
        f = F[F.series == s]
        x = [y] + list(f.year)
        fig.add_scatter(x=x, y=[t[s][y]] + list(f.forecast), name=f"{TARGETS[s]} forecast", mode="lines+markers", line=dict(dash="dash", color=col))
        fig.add_scatter(x=list(f.year) + list(f.year)[::-1], y=list(f.upper_80) + list(f.lower_80)[::-1], mode="lines", fill="toself", fillcolor="rgba(150,150,150,0.2)",
                        line=dict(width=0), hoverinfo="skip", showlegend=False)
    fig.update_yaxes(title="M.TND")
    rows = []
    for s, label in TARGETS.items():
        f = F[F.series == s].set_index("year")
        rows.append(html.Tr([html.Td(label)] + [html.Td(f"{f.forecast[y + k]:,.0f}") for k in (1, 2, 3)] + [html.Td(pct(100 * (f.forecast[y + 3] / t[s][y]) ** (1 / 3) - 100) + " / yr")]))
    tbl = html.Table([html.Thead(html.Tr([html.Th("Series (M.TND)")] + [html.Th(str(y + k)) for k in (1, 2, 3)] + [html.Th(f"Growth {y}-{y + 3}")])), html.Tbody(rows)], className="table")
    return html.Div([kpis, grid(graph(fig, 380, f"Premiums and claims, history and forecast to {y + 3}"), html.Div([html.H4("Final forecast (ensemble)"), tbl,
                     note("The ensemble averages five models (ARIMA, Prophet, gradient boosting, Random Forest, LSTM), weighting each by its past accuracy. "
                          "Its backtest error is about 3.8% (MAPE). The shaded band is the 80% interval.")], className="panel"))])
