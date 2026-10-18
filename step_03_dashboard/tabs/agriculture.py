"""Agriculture: production indices, weight in the economy and crop-by-crop detail (the crop is chosen in a drop-down)."""
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from data import proc
from ui import card, cards, graph, grid, note, style


def layout():
    a = proc("agriculture_annual").set_index("year")
    crops = sorted(proc("agriculture_crops").crop.unique())
    y = int(a.index.max())
    f1 = go.Figure()
    for c, n in (("crops_index_2014_16", "Crops"), ("livestock_index_2014_16", "Livestock"), ("food_index_2014_16", "Food")):
        f1.add_scatter(x=a.index, y=a[c], name=n, mode="lines+markers", marker=dict(size=4))
    f1.update_yaxes(title="index, 2014-16 = 100")
    f1.update_layout(title="Production indices")
    f2 = go.Figure(go.Scatter(x=a.index, y=a.agri_value_added_pct_gdp, mode="lines+markers", marker=dict(size=4), line=dict(color="#2ca02c")))
    f2.update_yaxes(title="% of GDP")
    f2.update_layout(title="Agriculture's share of GDP")
    f3 = go.Figure(go.Scatter(x=a.index, y=a.agri_employment_pct_total, mode="lines+markers", marker=dict(size=4), line=dict(color="#8c564b")))
    f3.update_yaxes(title="% of employment")
    f3.update_layout(title="Agriculture's share of employment")
    return html.Div([cards(card(f"Crops index {y}", f"{a.crops_index_2014_16[y]:.0f}"), card("Share of GDP", f"{a.agri_value_added_pct_gdp[y]:.1f}%"),
                           card("Share of employment", f"{a.agri_employment_pct_total[y]:.1f}%")),
                     grid(graph(f1), graph(f2), graph(f3), html.Div([html.Div([html.Label("Crop  ", className="label"), dcc.Dropdown(crops, "Olives", id="ag-crop", clearable=False, className="dropdown")]),
                                                                     dcc.Graph(id="ag-crop-chart", config={"displayModeBar": False})], className="panel")),
                     note("Sources: FAO and World Bank (step 1). The crop chart shows production and yield from 2012.")])


def register(app):
    @app.callback(Output("ag-crop-chart", "figure"), Input("ag-crop", "value"))
    def crop_chart(crop):
        d = proc("agriculture_crops")
        d = d[d.crop == crop]
        fig = go.Figure()
        fig.add_bar(x=d.year, y=d.production_t / 1000, name="Production (thousand t)", marker_color="#2ca02c")
        fig.add_scatter(x=d.year, y=d.yield_kg_per_ha, name="Yield (kg/ha)", yaxis="y2", mode="lines+markers", line=dict(color="#d62728"))
        fig.update_layout(yaxis=dict(title="thousand tonnes"), yaxis2=dict(title="kg per ha", overlaying="y", side="right", showgrid=False))
        return style(fig, 300, f"{crop}: production and yield")
