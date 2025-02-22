import pandas as pd
import sqlite3
import plotly.express as px
import dash
from dash import html, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import json

# Path to the preloaded database
DB_FILE = "data.db"

# Load GeoJSON data (still needed)
with open('./maps/world.geojson') as f:
    countries = json.load(f)

# Create Persistent SQLite Connection (Better Performance)
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# Create Index for Faster Queries (Only Run Once)
cursor.execute("CREATE INDEX IF NOT EXISTS idx_year_pubmed ON publications(year_pubmed);")
conn.commit()  # Save changes

# Optimized Query Function (Uses Persistent Connection)
def get_pubs_per_year_per_country(country_code, year_range):
    query = "SELECT year_pubmed,COUNT(*) as count FROM publications\
         WHERE majority_country = '{country}'\
         AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
         GROUP BY year_pubmed\
         ORDER BY year_pubmed DESC".format(country=country_code,
                                           year_start=year_range[0],
                                           year_end=year_range[1])
    pubs_per_year = pd.read_sql(query, conn)
    return pubs_per_year

# Initialize Dash App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server  

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div(id='country-name',
                     style={'textAlign': 'center', 'fontSize': '24px', 'padding': '10px', 'backgroundColor': '#f0f0f0'},
                     children='Click on a country to see its name'),
            # html.Label([
            #     "Show Postal Codes",
            #     dcc.Checklist(id='toggle-postal', options=[{'label': '', 'value': 'show'}], value=[])
            # ], style={'margin': '10px'}),
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
    ]),
    # slider
    dbc.Row([
        dbc.Col([
            dcc.RangeSlider(
                id='year-slider',
                min=2000,
                max=2024,
                step=1,
                marks={i: str(i) for i in range(2000, 2024+1, 2)},  # every 2 years
                value=[2000, 2024],  # Default
                tooltip={"placement": "bottom", "always_visible": True, "style": {"color": "White", "fontSize": "18px"}},
            )
        ], width=28)
    ], style={'padding': '20px'})
], fluid=True)    

# Update Graph using callbacks
@app.callback(Output('barplot', 'figure'),
              [Input('geojson', 'clickData'),
               Input('year-slider', 'value')])
def update_bar_chart(click_data, year_range):
    if click_data and 'properties' in click_data and 'ISO_A2' in click_data['properties']:
        country_code = click_data['properties']['ISO_A2']
        pubs_per_year = get_pubs_per_year_per_country(country_code, year_range)
        fig = px.bar(pubs_per_year, y="year_pubmed", x="count", orientation='h', height=800)
        fig.update_traces(marker_color='black')
        return fig
    return 'Click on a country for statistics'

@app.callback(Output('country-name', 'children'), Input('geojson', 'clickData'))
def display_country_name(click_data):
    if click_data and 'properties' in click_data and 'NAME' in click_data['properties']:
        return f"{click_data['properties']['NAME']}"
    return "Click on a country to see its name."

# @app.callback(Output('postal-layer', 'children'), Input('toggle-postal', 'value'))
# def toggle_postal_codes(show_postal):
#     if 'show' in show_postal:
#         labels = [dl.Marker(position=[f['properties'].get('label_y', 0), f['properties'].get('label_x', 0)],
#                             children=dl.Tooltip(f['properties'].get('postal', ''), permanent=True))
#                   for f in countries['features'] if 'postal' in f['properties']]
#         return labels
#     return []

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=False)