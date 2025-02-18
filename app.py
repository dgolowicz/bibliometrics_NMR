import pandas as pd
#import sqlite3
import plotly.express as px
import dash
from dash import html, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import json

# Path to the preloaded database
#DB_FILE = "data.db"

# Load GeoJSON data (still needed)
with open('./maps/worldmap.geo.json') as f:
    countries = json.load(f)

# Load dataframe to RAM
df = pd.read_pickle('./df_render.pkl')

# # Fetch Data from DB (only when needed)
# def get_pubs_per_year():
#     conn = sqlite3.connect(DB_FILE)
#     query = "SELECT year_pubmed, COUNT(*) as count FROM publications GROUP BY year_pubmed ORDER BY count DESC"
#     pubs_per_year = pd.read_sql(query, conn)
#     conn.close()
#     return pubs_per_year

# Fetch Data from DB (only when needed)
def get_pubs_per_year():
    pubs_per_year = df.groupby(by='year_pubmed')[['pmid']]\
                    .count().reset_index()\
                    .rename(columns={'pmid':'count'})\
                    .sort_values(by='year_pubmed', ascending=False)
    return pubs_per_year

# Initialize Dash App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# server instance (for Gunicorn)
server = app.server  

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div(id='country-name',
                     style={'textAlign': 'center', 'fontSize': '24px', 'padding': '10px', 'backgroundColor': '#f0f0f0'},
                     children='Click on a country to see its name'),
            html.Label([
                "Show Postal Codes",
                dcc.Checklist(id='toggle-postal', options=[{'label': '', 'value': 'show'}], value=[])
            ], style={'margin': '10px'}),
            dl.Map(center=[20, 0], zoom=2, children=[
                dl.GeoJSON(data=countries, id="geojson",
                           style=dict(color='black', weight=1, fillOpacity=0.1),
                           hoverStyle=dict(weight=2, color='red')),
                dl.LayerGroup(id='postal-layer')
            ], style={'height': '800px', 'width': '100%'})
        ], width=6),
        dbc.Col([
            dcc.Graph(id='barplot', responsive=False)
        ], width=6),
    ])
], fluid=True)

# Update Graph Dynamically
@app.callback(Output('barplot', 'figure'), Input('geojson', 'clickData'))
def update_bar_chart(_):
    pubs_per_year = get_pubs_per_year()
    fig = px.bar(pubs_per_year, y="year_pubmed", x="count", orientation='h', height=800)
    fig.update_traces(marker_color='black')
    return fig

@app.callback(Output('country-name', 'children'), Input('geojson', 'clickData'))
def display_country_name(click_data):
    if click_data and 'properties' in click_data and 'name' in click_data['properties']:
        return f"{click_data['properties']['name']}"
    return "Click on a country to see its name."

@app.callback(Output('postal-layer', 'children'), Input('toggle-postal', 'value'))
def toggle_postal_codes(show_postal):
    if 'show' in show_postal:
        labels = [dl.Marker(position=[f['properties'].get('label_y', 0), f['properties'].get('label_x', 0)],
                            children=dl.Tooltip(f['properties'].get('postal', ''), permanent=True))
                  for f in countries['features'] if 'postal' in f['properties']]
        return labels
    return []

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=False)