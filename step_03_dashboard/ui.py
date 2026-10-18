"""Small shared pieces of the layout: cards, graphs, the grid, and the look of every figure."""
from dash import dcc, html

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#17becf", "#7f7f7f"]
INK, MUTED, LINE, BG = "#1b2a41", "#5f6b7a", "#e3e8ef", "#f5f7fa"


def style(fig, height=340, title=None):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=45, r=15, t=45 if (title or fig.layout.title.text) else 15, b=40),
                      legend=dict(orientation="h", y=-0.22, x=0), font=dict(size=12, color=INK), colorway=PALETTE,
                      title=dict(text=title or fig.layout.title.text, font=dict(size=14), x=0))
    return fig


def graph(fig, height=340, title=None, gid=None):
    kwargs = {"id": gid} if gid else {}
    return html.Div(dcc.Graph(figure=style(fig, height, title), config={"displayModeBar": False}, **kwargs), className="panel")


def card(label, value, sub=None, good=None):
    colour = {True: "#1a8f4c", False: "#c0392b", None: MUTED}[good]
    return html.Div([html.Div(label, className="card-label"), html.Div(value, className="card-value"),
                     html.Div(sub or "", className="card-sub", style={"color": colour})], className="card")


def cards(*items):
    return html.Div(list(items), className="cards")


def grid(*children, cols=2):
    return html.Div(list(children), className="grid", style={"gridTemplateColumns": f"repeat({cols}, minmax(0, 1fr))"})


def note(text):
    return html.P(text, className="note")


def pct(x, d=1):
    return f"{x:+.{d}f}%"
