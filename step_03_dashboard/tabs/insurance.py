"""Insurance: market size, branch mix, claims ratio, growth, penetration and the companies."""
import plotly.express as px
import plotly.graph_objects as go
from data import last_year, proc, table
from dash import html
from ui import cards, card, graph, grid, note


def layout():
    t, y = table(), last_year()
    a = proc("insurance_annual").set_index("year")
    parts = {"Life": "premiums_life", "Motor": "premiums_auto", "Health": "premiums_health", "Transport": "premiums_transport", "Fire & misc.": "premiums_fire_and_misc_combined"}
    d = a[list(parts.values())].rename(columns={v: k for k, v in parts.items()})
    d["Other"] = a.premiums_total - d.sum(axis=1)
    f1 = px.area(d, labels={"value": "M.TND", "year": "", "variable": ""})
    f1.update_layout(title="Premiums by branch")
    share = d.div(a.premiums_total, axis=0) * 100
    f2 = px.area(share, labels={"value": "%", "year": "", "variable": ""})
    f2.update_layout(title="Branch shares (%)")
    f2.update_yaxes(range=[0, 100])
    f3 = go.Figure()
    for label, p, c in (("All branches", "premiums_total", "claims_paid_total"), ("Motor", "premiums_auto", "claims_paid_auto"), ("Health", "premiums_health", "claims_paid_health"),
                        ("Life", "premiums_life", "claims_paid_life")):
        f3.add_scatter(x=a.index, y=100 * a[c] / a[p], name=label, mode="lines+markers", marker=dict(size=4))
    f3.update_yaxes(title="% of premiums")
    f3.update_layout(title="Claims paid / premiums")
    g = (100 * a[["premiums_total", "premiums_life", "premiums_auto", "premiums_health", "claims_paid_total"]].pct_change()).dropna()
    f4 = go.Figure()
    for c, n in (("premiums_total", "Total premiums"), ("premiums_life", "Life"), ("premiums_auto", "Motor"), ("premiums_health", "Health"), ("claims_paid_total", "Claims")):
        f4.add_scatter(x=g.index, y=g[c], name=n, mode="lines+markers", marker=dict(size=4))
    f4.add_hline(y=0, line_width=1, line_color="#999")
    f4.update_yaxes(title="% per year")
    f4.update_layout(title="Annual growth")
    f5 = go.Figure(go.Scatter(x=t.index, y=t.penetration_pct_gdp, mode="lines+markers", marker=dict(size=4)))
    f5.update_yaxes(title="% of GDP")
    f5.update_layout(title="Penetration: premiums as % of GDP")
    c = proc("insurance_companies")
    top = c[(c.branch_code == "ALL_BRANCHES") & (c.measure == "premiums_total_direct_plus_acceptances") & (c.year == c.year.max())].sort_values("value_mtnd").tail(10)
    f6 = px.bar(top, x="value_mtnd", y="company", orientation="h", labels={"value_mtnd": "M.TND", "company": ""})
    f6.update_layout(title=f"Ten largest companies, premiums {int(c.year.max())}")
    return html.Div([cards(card(f"Premiums {y}", f"{t.premiums_total[y]:,.0f} M.TND"), card("Motor share", f"{t.auto_share_pct[y]:.0f}%"), card("Life share", f"{t.life_share_pct[y]:.0f}%"),
                           card("Health share", f"{t.health_share_pct[y]:.0f}%"), card("Penetration", f"{t.penetration_pct_gdp[y]:.2f}% GDP"), card("Loss ratio", f"{t.loss_ratio_pct[y]:.0f}%")),
                     grid(graph(f1), graph(f2), graph(f3), graph(f4), graph(f5), graph(f6)),
                     note("Source: CGA and FTUSA annual reports (step 1, cleaned). Company data covers 2016 onwards.")])
