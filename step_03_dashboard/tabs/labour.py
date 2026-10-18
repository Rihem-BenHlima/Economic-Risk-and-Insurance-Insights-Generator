"""Labour: unemployment and employment."""
import plotly.graph_objects as go
from dash import html
from data import proc
from ui import card, cards, graph, grid, note


def layout():
    a, q = proc("labour_annual").set_index("year"), proc("labour_quarterly")
    y = int(a.index.max())
    f1 = go.Figure(go.Scatter(x=a.index, y=a.unemployment_rate, mode="lines+markers", line=dict(color="#c0392b"), marker=dict(size=4)))
    f1.update_yaxes(title="%")
    f1.update_layout(title="Unemployment rate")
    est = a.employed_source.str.contains("estimated", na=False)
    f2 = go.Figure(go.Bar(x=a.index, y=a.employed_thousand, marker_color=["#9db7d5" if v else "#1f77b4" for v in est]))
    f2.update_yaxes(title="thousand people")
    f2.update_layout(title="Employed people (light bars are estimates)")
    f3 = go.Figure()
    for c, n in (("unemployment_rate_total", "Total"), ("unemployment_rate_male", "Men"), ("unemployment_rate_female", "Women"),
                 ("higher_ed_graduates_unemployment_rate_total", "Higher-education graduates")):
        f3.add_scatter(x=q.period, y=q[c], name=n, mode="lines+markers")
    f3.update_yaxes(title="%")
    f3.update_layout(title="Unemployment by group, recent quarters")
    f4 = go.Figure(go.Scatter(x=a.index, y=100 * a.employment_rate_proxy, mode="lines+markers", marker=dict(size=4)))
    f4.update_yaxes(title="% of the labour force")
    f4.update_layout(title="Employed / labour force")
    return html.Div([cards(card(f"Unemployment {y}", f"{a.unemployment_rate[y]:.1f}%"), card("Employed", f"{a.employed_thousand[y] / 1000:.2f} M people")),
                     grid(graph(f1), graph(f2), graph(f3), graph(f4)),
                     note("Sources: INS and World Bank (step 1). Employment before 2011 and in the last year is estimated from the unemployment rate and the labour force.")])
