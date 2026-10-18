"""Economy: growth, inflation, currency, credit, trade and money."""
import plotly.graph_objects as go
from dash import html
from data import last_year, proc, table
from ui import card, cards, graph, grid, note


def layout():
    e, y = proc("economy_annual").set_index("year"), last_year()
    q, m = proc("economy_quarterly"), proc("economy_monthly")
    f1 = go.Figure()
    f1.add_bar(x=e.index, y=e.gdp_growth_pct, name="Real GDP growth", marker_color=["#c0392b" if v < 0 else "#1f77b4" for v in e.gdp_growth_pct])
    f1.add_scatter(x=e.index, y=e.inflation_pct, name="Inflation", mode="lines+markers", line=dict(color="#ff7f0e"))
    f1.update_yaxes(title="%")
    f1.update_layout(title="GDP growth and inflation")
    f2 = go.Figure(go.Scatter(x=e.index, y=e.tnd_per_usd, mode="lines+markers", marker=dict(size=4)))
    f2.update_yaxes(title="TND per USD")
    f2.update_layout(title="Dinar exchange rate")
    f3 = go.Figure()
    f3.add_scatter(x=e.index, y=e.private_credit_pct_gdp, name="Private credit / GDP", mode="lines+markers")
    f3.add_scatter(x=e.index, y=e.exports_pct_gdp, name="Exports / GDP", mode="lines")
    f3.add_scatter(x=e.index, y=e.imports_pct_gdp, name="Imports / GDP", mode="lines")
    f3.update_yaxes(title="% of GDP")
    f3.update_layout(title="Credit and trade")
    f4 = go.Figure(go.Bar(x=q.period, y=q.gdp_real_yoy_pct, marker_color=["#c0392b" if v < 0 else "#1f77b4" for v in q.gdp_real_yoy_pct]))
    f4.update_yaxes(title="% vs same quarter last year")
    f4.update_layout(title="Quarterly real GDP growth")
    f5 = go.Figure(go.Scatter(x=m.month, y=m.inflation_yoy_pct, mode="lines"))
    f5.update_yaxes(title="% year on year")
    f5.update_layout(title="Monthly inflation")
    f6 = go.Figure(go.Scatter(x=e.index, y=e.broad_money_growth_pct, mode="lines+markers", marker=dict(size=4)))
    f6.update_yaxes(title="%")
    f6.update_layout(title="Broad money growth")
    return html.Div([cards(card(f"GDP growth {y}", f"{e.gdp_growth_pct[y]:.1f}%"), card(f"Inflation {y}", f"{e.inflation_pct[y]:.1f}%"),
                           card("TND per USD", f"{e.tnd_per_usd[y]:.2f}"), card("Private credit", f"{e.private_credit_pct_gdp[y]:.0f}% GDP"),
                           card("Current account", f"{e.current_account_usd_bn[y]:.1f} bn USD")),
                     grid(graph(f1), graph(f2), graph(f3), graph(f4), graph(f5), graph(f6)),
                     note("Sources: World Bank, FRED, BCT and INS (step 1, cleaned and chain-linked where the base year changed).")])
