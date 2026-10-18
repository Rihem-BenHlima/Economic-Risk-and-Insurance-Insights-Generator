"""Climate and risk: rainfall, heat, floods and drought for Tunis, yearly and by month."""
import pandas as pd
import plotly.graph_objects as go
from dash import html
from data import proc
from ui import card, cards, graph, grid, note


def layout():
    a, m = proc("climate_annual").set_index("year"), proc("climate_monthly")
    y = int(a.index.max())
    f1 = go.Figure(go.Bar(x=a.index, y=a.rainfall_mm, marker_color="#1f77b4"))
    f1.add_hline(y=a.rainfall_mm.mean(), line_dash="dash", line_color="#555", annotation_text="mean")
    f1.update_yaxes(title="mm")
    f1.update_layout(title="Annual rainfall")
    f2 = go.Figure(go.Bar(x=a.index, y=a.heat_days_ge35c, marker_color="#ff7f0e"))
    f2.update_yaxes(title="days")
    f2.update_layout(title="Days at or above 35 C")
    wet = a.heavy_rain_days_ge20mm.nlargest(3).index
    f3 = go.Figure(go.Bar(x=a.index, y=a.heavy_rain_days_ge20mm, marker_color=["#c0392b" if i in wet else "#17becf" for i in a.index]))
    f3.update_yaxes(title="days")
    f3.update_layout(title="Days with at least 20 mm of rain (flood risk; red = the three wettest years)")
    f4 = go.Figure(go.Scatter(x=a.index, y=a.dry_spell_max_days, mode="lines+markers", line=dict(color="#8c564b"), marker=dict(size=4)))
    f4.update_yaxes(title="days")
    f4.update_layout(title="Longest dry spell (days under 1 mm of rain: drought)")
    mm = m.copy()
    mm["year"], mm["mo"] = mm.month.str[:4].astype(int), mm.month.str[5:].astype(int)
    heat = mm.pivot(index="year", columns="mo", values="rainfall_mm")
    f5 = go.Figure(go.Heatmap(z=heat.values, x=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], y=heat.index, colorscale="Blues",
                              colorbar=dict(title="mm")))
    f5.update_layout(title="Rainfall by month and year")
    f5.update_yaxes(autorange="reversed")
    f6 = go.Figure(go.Scatter(x=a.index, y=a.temp_mean_c, mode="lines+markers", line=dict(color="#d62728"), marker=dict(size=4)))
    f6.update_yaxes(title="degrees C")
    f6.update_layout(title="Mean temperature")
    return html.Div([cards(card(f"Rainfall {y}", f"{a.rainfall_mm[y]:.0f} mm", f"mean {a.rainfall_mm.mean():.0f} mm"), card(f"Heat days {y}", f"{a.heat_days_ge35c[y]:.0f}", "days >= 35 C"),
                           card("Mean temperature", f"{a.temp_mean_c[y]:.1f} C", f"{y}"), card("Heaviest day", f"{a.max_daily_rain_mm[y]:.0f} mm", f"{y}")),
                     grid(graph(f1), graph(f2), graph(f3), graph(f4), graph(f5, 380), graph(f6)),
                     note("Source: Open-Meteo daily data for Tunis (step 1), summarised by month and year. This is the weather behind the climate risk for motor and property claims.")])
