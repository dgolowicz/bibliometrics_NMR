import pandas as pd
import sqlite3
import plotly.express as px
import dash
from dash import html, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import json
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import dash_leaflet.express as dlx
from dash_extensions.javascript import assign
from collections import defaultdict



style_handle = assign("""
function(feature, context){
    // If a style for the country exists in the hideout, use it.
    if (context.hideout && context.hideout.styles && context.hideout.styles[feature.properties.ISO_A2]) {
        return context.hideout.styles[feature.properties.ISO_A2];
    }
    // Otherwise, return a default style.
    return {color: 'black', weight: 1, fillOpacity: 0.1};
}
""")

def sum_collabs_in_years(x):
    if not x.empty:
        result = defaultdict(int)
        for d in x:
            for key, value in d.items():
                result[key] += value

        sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
        
        return dict(sorted_result)
    else: 
        return {}


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


def get_color(value, min_val=0, max_val=200, cmap_name="Blues"):
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    cmap = cm.get_cmap(cmap_name)  # Use cm.get_cmap() to retrieve the colormap
    rgba = cmap(norm(value))
    return mcolors.to_hex(rgba)



def collabs_dict(x, country):
    lst = list(filter(None, x['all_countries'].replace("[", "")\
                                              .replace("]", "")\
                                              .replace("'", "")\
                                              .replace(" ", "")\
                                              .split(',')))
    
    collabs = {x: lst.count(x) for x in lst if x != country}
    sorted_collabs = dict(sorted(collabs.items(), key=lambda item: item[1], reverse=True))
    
    return(sorted_collabs)
    

def generate_country_styles(selected_country, year_range):
    styles = {}
 
    query = "SELECT year_pubmed, GROUP_CONCAT(countries) AS all_countries\
            FROM publications\
            WHERE majority_country = '{country}'\
            AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
            GROUP BY year_pubmed\
            ORDER BY year_pubmed DESC".format(country=selected_country,
                                           year_start=year_range[0],
                                           year_end=year_range[1])
            
    df = pd.read_sql(query, conn)
    #df['collabs'] = df.apply(lambda x: collabs_dict(x, selected_country), axis=1)
    collab_dict = df.apply(lambda x: collabs_dict(x, selected_country), axis=1)  # TO DO!!! NOW ONLY FOR 2024
    
    summed_collab_dict = sum_collabs_in_years(collab_dict)
       
    max_collab = max(summed_collab_dict.values()) if summed_collab_dict else 1  # Avoid division by zero
        
    # Assign colors based on collaboration frequency
    for country_code, freq in summed_collab_dict.items():
        styles[country_code] = {
            "fillColor": get_color(freq, min_val=0, max_val=max_collab, cmap_name="Blues"),
            "fillOpacity": 0.8, 
            "color": "black",
            "weight": 1
        }
    #print(styles)
    return styles, max_collab


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


# Initialize Dash App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server  

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id="metric-dropdown",
                options=[
                    {"label": "No coloring", "value": "nocolors"},
                    {"label": "Collaborators (updates when selecting a country)", "value": "collabs"},
                    {"label": "GDP", "value": "gdp"},
                    {"label": "Population", "value": "population"}
                ],
                clearable=False,
                style={
                    "textAlign": "center",  # Center the text inside the dropdown
                    "width": "100%",  # Adjust width as needed
                    "margin": "auto",  # Centers the dropdown in the page
                    "display": "block"  # Ensures it is treated as a block element
                },
                placeholder="Select metrics for coloring the map"),
            html.Div(id='country-name',
                     style={'textAlign': 'center', 'fontSize': '24px', 'padding': '10px', 'backgroundColor': '#f0f0f0'},
                     children='Click on a country to see its name'),
            dl.Map(center=[20, 0], zoom=2, children=[
                dl.GeoJSON(data=countries,
                           id="geojson",
                           style=style_handle,  # use the dynamic style function
                           hoverStyle=dict(weight=2, color='red'),
                           hideout=dict(styles={})),  # initial empty styles mapping
                dl.LayerGroup(id="colorbar-layer")
                ], style={'height': '800px', 'width': '100%'})
        ], width=8),
        dbc.Col([
            dcc.Graph(id='barplot', responsive=False)
        ], width=4),
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

@app.callback(
    Output('geojson', 'hideout'),
    Output('colorbar-layer', 'children'),
    [Input('geojson', 'clickData'),
     Input('year-slider', 'value'),
     Input('metric-dropdown', 'value')])
def update_geojson_styles(click_data, year_range, dropdown):
    new_styles = {}  # Dictionary to hold styles
    colorbar = None


    if click_data and 'properties' in click_data and 'ISO_A2' in click_data['properties']:
        selected_country = click_data['properties']['ISO_A2']

        # Set the clicked country's style (always applied)
        new_styles[selected_country] = {
            "fillColor": "red",  # Highlight clicked country
            "fillOpacity": 0.5,
            "color": "black",
            "weight": 2
        }

        # If the dropdown is set to "Collaborators", apply additional styles
        if dropdown == 'collabs':
            collab_styles, max_collab = generate_country_styles(selected_country, year_range)
            new_styles.update(collab_styles)  # Merge the collaboration styles
            
            colorbar = dl.Colorbar(
                id="colorbar",
                width=30,
                height=750,
                colorscale="Blues",
                min=0,
                max=max_collab,
                position="bottomright",
                nTicks = 5,
            )  
            

    return {"styles": new_styles}, colorbar   # Update the map with new styles






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