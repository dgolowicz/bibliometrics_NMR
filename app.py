import pandas as pd
import sqlite3
import plotly.express as px
import dash
from dash import html, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import json
import matplotlib.cm as cm
import matplotlib.colors as mcolors
#import dash_leaflet.express as dlx
from dash_extensions.javascript import assign
from collections import defaultdict



style_handle = assign("""
function(feature, context){
    // If a style for the country exists in the hideout, use it.
    if (context.hideout && context.hideout.styles && context.hideout.styles[feature.properties.ISO_A2]) {
        return context.hideout.styles[feature.properties.ISO_A2];
    }
    // Otherwise, return a default style.
    return {color: 'black', weight: 1, fillOpacity: 0.05};
}
""")

def best_collabs(x):
    nmax = len(list(x.items()))
    if nmax >= 5:
        output = str(list(x.items())[0:5]).replace("'","").replace("[","").replace("]","").replace("]","")\
                                                .replace("(","").replace(")","").replace(",",":")
        return 'Most foreign affiliations: ' + output
    elif nmax < 5 and nmax >= 1:
        output = str(list(x.items())[0:nmax]).replace("'","").replace("[","").replace("]","").replace("]","")\
                                                .replace("(","").replace(")","").replace(",",":")
        return 'Most foreign affiliations: ' + output
    else:
        return 'No foreign affiliations'

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
    

# return info if dataframe for plotting (top and bottom chart) is empty for the selected country:
def empty_df_info():
    return  go.Figure(layout=go.Layout(title=dict(text="No data available for this country in a selected year range",
                                                    x=0.5,y=0.5, xanchor='center', yanchor='top'),
                                        template='plotly_white',xaxis=dict(visible=False),yaxis=dict(visible=False)))
    

def get_pubs_per_year_per_country(country_code, year_range):
    query = "SELECT year_pubmed as Year, COUNT(*) as 'Articles' FROM publications\
         WHERE majority_country = '{country}'\
         AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
         GROUP BY year_pubmed\
         ORDER BY year_pubmed DESC".format(country=country_code,
                                           year_start=year_range[0],
                                           year_end=year_range[1])
    pubs_per_year = pd.read_sql(query, conn)
    return pubs_per_year

def openacces_per_year_per_country(country_code, year_range):
         
    query = "SELECT year_pubmed as Year, ROUND(CAST(SUM(is_open_access) AS FLOAT)*100 / COUNT(is_open_access),1) as 'Open access' FROM publications\
            WHERE majority_country = '{country}'\
            AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
            GROUP BY year_pubmed\
            ORDER BY year_pubmed DESC".format(country=country_code,
                                        year_start=year_range[0],
                                        year_end=year_range[1])    

    oa_per_year = pd.read_sql(query, conn)
    if oa_per_year.empty:
        return oa_per_year
    else:
        oa_per_year['Paid access'] = oa_per_year.apply(lambda x: 100 - x['Open access'], axis=1)
    
    return oa_per_year


def get_color(value, min_val=0, max_val=200, cmap_name="Blues"):
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    cmap = cm.get_cmap(cmap_name)  # Use cm.get_cmap() to retrieve the colormap
    rgba = cmap(norm(value))
    return mcolors.to_hex(rgba)

# def get_color_avg_authors(value, min_val=0, max_val=200, cmap_name="RdBu"):
#     norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
#     cmap = cm.get_cmap(cmap_name)  # Use cm.get_cmap() to retrieve the colormap
#     rgba = cmap(norm(value))
#     return mcolors.to_hex(rgba)



def collabs_dict(x, country):
    lst = list(filter(None, x['all_countries'].replace("[", "")\
                                              .replace("]", "")\
                                              .replace("'", "")\
                                              .replace(" ", "")\
                                              .split(',')))
    
    collabs = {x: lst.count(x) for x in lst if x != country}
    sorted_collabs = dict(sorted(collabs.items(), key=lambda item: item[1], reverse=True))
    
    return(sorted_collabs)
    

def collaborators(selected_country, year_range):
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
    collab_dict = df.apply(lambda x: collabs_dict(x, selected_country), axis=1)
    
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
    return styles, max_collab, summed_collab_dict

def avg_number_authors(year_range, min_records):
    styles = {}
    
    query = "SELECT majority_country,ROUND(AVG(authors_number),2) FROM publications\
                WHERE majority_country != 'Multinational'\
                AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
                GROUP BY majority_country\
                HAVING COUNT(*) >= {min_papers}".format(year_start=year_range[0],
                                                          year_end=year_range[1],
                                                          min_papers = min_records)
                
    cursor.execute(query)
    result_dict = dict(cursor.fetchall())
    max_av_authors = max(result_dict.values(), default=100)
    min_av_authors = min(result_dict.values(), default=1)
    
    # Assign colors based on number of average number of authors
    for country_code, av_authors in result_dict.items():
        styles[country_code] = {
            "fillColor": get_color(av_authors, min_val=min_av_authors,
                                   max_val=max_av_authors, cmap_name="Blues"),
            "fillOpacity": 0.8, 
            "color": "black",
            "weight": 1
        }
    print(min_records)
    return styles, min_av_authors, max_av_authors, result_dict

def avg_number_references(year_range, min_records):
    styles = {}
    
    query = "SELECT majority_country,ROUND(AVG(n_references),2) FROM publications\
                WHERE majority_country != 'Multinational'\
                AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
                GROUP BY majority_country\
                HAVING COUNT(*) >= {min_papers}".format(year_start=year_range[0],
                                                          year_end=year_range[1],
                                                          min_papers = min_records)
                
    cursor.execute(query)
    result_dict = dict(cursor.fetchall())
    max_av_references = max(result_dict.values(), default=100)
    min_av_references = min(result_dict.values(), default=1)
    
    # Assign colors based on number of average number of authors
    for country_code, av_references in result_dict.items():
        styles[country_code] = {
            "fillColor": get_color(av_references, min_val=min_av_references,
                                   max_val=max_av_references, cmap_name="Blues"),
            "fillOpacity": 0.8, 
            "color": "black",
            "weight": 1
        }
    print(min_records)
    return styles, min_av_references, max_av_references, result_dict


def open_access_perc(year_range, min_records):
    styles = {}
    
    query = "SELECT majority_country, ROUND(CAST(SUM(is_open_access) AS FLOAT)*100 / COUNT(is_open_access),1) FROM publications\
                WHERE majority_country != 'Multinational'\
                AND year_pubmed BETWEEN '{year_start}' AND '{year_end}'\
                GROUP BY majority_country\
                HAVING COUNT(*) >= {min_papers}".format(year_start=year_range[0],
                                                          year_end=year_range[1],
                                                          min_papers = min_records)
                
    cursor.execute(query)
    result_dict = dict(cursor.fetchall())
    #max_perc_oa = max(result_dict.values(), default=100)
    #min_perc_oa = min(result_dict.values(), default=0)
    
    # Assign colors based on number of average number of authors
    for country_code, oa_perc in result_dict.items():
        styles[country_code] = {
            "fillColor": get_color(oa_perc, min_val=0,
                                   max_val=100, cmap_name="RdBu"),
            "fillOpacity": 0.8, 
            "color": "black",
            "weight": 1
        }
    return styles, result_dict

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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],suppress_callback_exceptions=True)

server = app.server  

app.layout = dbc.Container([
    dbc.Row([
        
        dbc.Col([
            dcc.Store(id="stored-min-papers", data=100),
            dcc.Dropdown(
                id="metric-dropdown",
                options=[
                    {"label": "No coloring", "value": "nocolors"},
                    {"label": "Collaborators (updates when selecting a country)", "value": "collabs"},
                    {"label": "Average number of authors", "value": "avg_authors"},
                    {"label": "Open Access (percent)", "value": "open_access"},
                    {"label": "Average number of references", "value": "avg_references"}
                ],
                clearable=False,
                style={
                    "textAlign": "center",
                    "width": "100%",
                    "margin": "auto",
                    "display": "block"
                },
                placeholder="Select metrics for coloring the map"),
            html.Div(id='country-name',
                     style={'textAlign': 'center', 'fontSize': '24px', 'padding': '10px', 'backgroundColor': '#f0f0f0'},
                     children='Click on a country to see its name'),
            html.Div(id='extra-info-top',
                     style={'textAlign': 'center', 'fontSize': '12px', 'padding': '1px', 'backgroundColor': 'rgba(0, 0, 0, 0.135)'},
                     children='\u00A0'),
            dl.Map(center=[20, 0], zoom=2, attributionControl=False, children=[
                dl.GeoJSON(data=countries,
                           id="geojson",
                           style=style_handle,  # use the dynamic style function
                           hoverStyle=dict(weight=3, color='red'),
                           hideout=dict(styles={})),  # initial empty styles mapping
                dl.LayerGroup(id="colorbar-layer")
                ], style={'height': '700px', 'width': '100%'}),
                html.Div(id='extra-info',style={'textAlign': 'center', 'fontSize': '14px', 'padding': '10px','backgroundColor': '#f0f0f0'},
                        children=[html.Span(id='info-text', children='\u00A0'),  # Placeholder text
                                dcc.Input(
                                    id='min-papers-input',
                                    type='number',
                                    placeholder='100',
                                    value=100,
                                    style={'display': 'none'}  # Initially hidden
                                    )
                                ]
                         )
            ],width=8),
        
        
        dbc.Col(
            [dcc.Dropdown(
                id="top-plot-dropdown",
                options=[
                    {"label": "No plot", "value": "no_plot"},
                    {"label": "Number of articles", "value": "plot_pub_num"},
                    {"label": "Open access articles", "value": "plot_open_acc"}
                ],
                clearable=False,
                style={
                    "textAlign": "center",
                    "width": "100%",
                    "margin": "auto",
                    "display": "block"
                },
                placeholder='Select country-specific plot'),
            html.Div(
                id='top-plot-container',
                children=[dcc.Graph(id='top-plot', responsive=True, style={'width': '100%', 'height': '100%'})],
                style={'height': '400px', 'width': '100%', 'padding-bottom': '10px'}
            ),
            
            dcc.Dropdown(
                id="bottom-plot-dropdown",
                options=[
                    {"label": "No coloring", "value": "nocolors"},
                    {"label": "Collaborators (updates when selecting a country)", "value": "collabs"}
                ],
                clearable=False,
                style={
                    "textAlign": "center",
                    "width": "100%",
                    "margin": "auto",
                    "display": "block"
                },
                placeholder='Select country-specific plot'),
            html.Div(
                id='bottom-plot-container',
                children=[dcc.Graph(id='bottom-plot', responsive=True, style={'width': '100%', 'height': '100%'})],
                style={'height': '400px', 'width': '100%'}
            )
            ],width=4),
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

# Top plot callack
@app.callback(Output('top-plot', 'figure'),
              [Input('geojson', 'clickData'),
               Input('year-slider', 'value'),
               Input('top-plot-dropdown', 'value')])
def update_chart_top(click_data, year_range, dropdown):
    if click_data and 'properties' in click_data and 'ISO_A2' in click_data['properties']:
        country_code = click_data['properties']['ISO_A2']
        
        # Plot number of articles per year
        if dropdown == 'plot_pub_num':
            pubs_per_year = get_pubs_per_year_per_country(country_code, year_range)
            fig = px.bar(pubs_per_year, x='Year', y='Articles', orientation='v', template='plotly_white')
            fig.update_traces(marker_color='grey', width=0.5)
            fig.update_layout(bargap=0.2, hoverlabel=dict(font=dict(color='white')))
            fig.update_xaxes(range=[year_range[0]-1, year_range[1]+0.5], title_font=dict(size=14),
                             tickfont=dict(size=14), tickangle=0, ticks='outside', tickwidth=2.5, tickcolor='rgba(0, 0, 0, 0.1)',)
            fig.update_yaxes(title_font=dict(size=14), tickfont=dict(size=14), gridcolor='rgba(0, 0, 0, 0.1)', gridwidth=1, griddash='solid')
            if pubs_per_year.empty:
                fig = empty_df_info()
            return fig
        
        # Plot open access percentage per year
        if dropdown == 'plot_open_acc':
            oa_per_year = openacces_per_year_per_country(country_code, year_range)
            fig = px.bar(oa_per_year, x='Year', y=['Open access', 'Paid access'], orientation='v', template='plotly_white',
                         color_discrete_map={'Open access': 'black', 'Paid access': 'rgba(0, 0, 0, 0.1)'})
            fig.update_traces(width=0.5)
            fig.update_layout(yaxis_title='Articles (%)', bargap=0.2, hoverlabel=dict(font=dict(color='white')),
                              legend=dict(title='', orientation='h', yanchor='top', y=1.1, xanchor='center', x=0.5))
            fig.update_xaxes(range=[year_range[0]-1, year_range[1]+0.5], title_font=dict(size=14),
                             tickfont=dict(size=14), tickangle=0, ticks='outside', tickwidth=2.5, tickcolor='rgba(0, 0, 0, 0.1)',)
            fig.update_yaxes(title_font=dict(size=14), tickfont=dict(size=14), gridcolor='rgba(0, 0, 0, 0.1)', gridwidth=1, griddash='solid')
            fig.for_each_trace(lambda trace: trace.update(hovertemplate=f"<span style='color:{'white' if trace.name == 'Open access (%)' else 'black'}'>"
                                                                        f"{trace.name}: %{{y}}%</span><extra></extra>"))  
            if oa_per_year.empty:
                fig = empty_df_info()
            return fig
        
        
    return  go.Figure(layout=go.Layout(title=dict(text="Click on a country and select plot type",
                                                  x=0.5,y=0.5, xanchor='center', yanchor='top'),
                                       template='plotly_white',xaxis=dict(visible=False),yaxis=dict(visible=False)))

# Bottom plot callack
@app.callback(Output('bottom-plot', 'figure'),
              [Input('geojson', 'clickData'),
               Input('year-slider', 'value'),
               Input('bottom-plot-dropdown', 'value')])
def update_chart_bottom(click_data, year_range, dropdown):
    if click_data and 'properties' in click_data and 'ISO_A2' in click_data['properties']:
        country_code = click_data['properties']['ISO_A2']
        
        if dropdown == 'plot_pub_num':
            pubs_per_year = get_pubs_per_year_per_country(country_code, year_range)
            print(pubs_per_year)
            fig = px.bar(pubs_per_year, y='Year', x='Number of articles', orientation='h', template='plotly_white')
            fig.update_traces(marker_color='black')
            return fig
    return  go.Figure(layout=go.Layout(title=dict(text="Click on a country and select plot type",
                                                  x=0.5,y=0.5, xanchor='center', yanchor='top'),
                                       template='plotly_white',xaxis=dict(visible=False),yaxis=dict(visible=False)))
    
@app.callback(Output('country-name', 'children'), Input('geojson', 'clickData'))
def display_country_name(click_data):
    if click_data and 'properties' in click_data and 'NAME' in click_data['properties']:
        return f"{click_data['properties']['NAME']}"
    return "Click on a country to see its name."

# pop up window for setting lower limit of publications to qualify country
# for calculation of average number of authors
@app.callback(
    Output("stored-min-papers", "data"),
    Input({'type': 'dynamic-input', 'id': 'min-papers-input'}, "value"),
    prevent_initial_call=True
)
def store_min_papers(value):
    if value is None or value == '':
        return 100
    return value 

@app.callback(
    Output('geojson', 'hideout'),
    Output('colorbar-layer', 'children'),
    Output('extra-info', 'children'),
    Output('extra-info-top', 'children'),
    [Input('geojson', 'clickData'),
     Input('year-slider', 'value'),
     Input('metric-dropdown', 'value'),
     Input('stored-min-papers', 'data')],
    prevent_initial_call=True
)
def update_geojson_styles(click_data, year_range, dropdown, min_papers_input):
    new_styles = {}  # Dictionary to hold styles
    extra_info = '\u00A0'
    extra_info_top = '\u00A0'
    colorbar = None


    if click_data and 'properties' in click_data and 'ISO_A2' in click_data['properties']:
        selected_country = click_data['properties']['ISO_A2']

        # Set the clicked country's style (always applied)
        new_styles[selected_country] = {
            "fillColor": "red",  # Highlight clicked country
            "fillOpacity": 0.5,
            "color": "black",
            "weight": 2.5
        }
        #COLLABORATORS MAP
        if dropdown == 'collabs':
            collab_styles, max_collab, collab_dict = collaborators(selected_country, year_range)
            new_styles.update(collab_styles)  # Merge the collaboration styles
            
            colorbar = dl.Colorbar(
                id="colorbar",
                width=20,
                height=550,
                colorscale="Blues",
                min=0,
                max=max_collab,
                position="bottomleft",
                nTicks = 5,
            )

            extra_info = best_collabs(collab_dict)
    
    
    # AVG AUTHORS MAP
    if dropdown == 'avg_authors':
        avg_authors_styles, min_avg_authors, max_avg_authors, avg_authors_result_dict = avg_number_authors(year_range, min_papers_input)
        new_styles.update(avg_authors_styles)


        colorbar = dl.Colorbar(
            id="colorbar",
            width=20,
            height=550,
            colorscale="Blues",
            min=int(min_avg_authors),
            max=int(max_avg_authors) + 1,
            position="bottomleft",
            nTicks=int(max_avg_authors) + 2
        )

        # Display the input field for 'avg_authors'
        extra_info = html.Span([
            "Include countries with at least ",
            dcc.Input(
                id={'type': 'dynamic-input', 'id': 'min-papers-input'},
                type='number',
                debounce=True,
#                placeholder='10',
                value=min_papers_input,
                style={'display': 'inline-block', 'width': '60px', 'margin': '0 5px'}
            ),
            " publications in a selected years range (confirm by pressing enter)"
        ])
        
        # Display the top extra info
        try:
            extra_info_top = avg_authors_result_dict[selected_country]
        except (NameError, KeyError):
            extra_info_top = '\u00A0'
            
    # AVG REFERENCES MAP
    if dropdown == 'avg_references':
        avg_references_styles, min_avg_references, max_avg_references, avg_references_result_dict = avg_number_references(year_range, min_papers_input)
        new_styles.update(avg_references_styles)

        colorbar = dl.Colorbar(
            id="colorbar",
            width=20,
            height=550,
            colorscale="Blues",
            min=int(min_avg_references),
            max=int(max_avg_references) + 1,
            position="bottomleft",
            nTicks=10
        )

        # Display the input field for 'avg_authors'
        extra_info = html.Span([
            "Include countries with at least ",
            dcc.Input(
                id={'type': 'dynamic-input', 'id': 'min-papers-input'},
                type='number',
                debounce=True,
#                placeholder='10',
                value=min_papers_input,
                style={'display': 'inline-block', 'width': '60px', 'margin': '0 5px'}
            ),
            " publications in a selected years range (confirm by pressing enter)"
        ])
        
        # Display the top extra info
        try:
            extra_info_top = avg_references_result_dict[selected_country]
        except (NameError, KeyError):
            extra_info_top = '\u00A0'
            
            
    # OPEN ACCESS PERCENT MAP
    if dropdown == 'open_access':
        oa_styles, oa_result_dict = open_access_perc(year_range, min_papers_input)
        new_styles.update(oa_styles)

        colorbar = dl.Colorbar(
            id="colorbar",
            width=20,
            height=550,
            colorscale="RdBu",
            min=0,
            max=100,
            position="bottomleft",
            nTicks=11
        )

        # Display the input field for 'avg_authors'
        extra_info = html.Span([
            "Include countries with at least ",
            dcc.Input(
                id={'type': 'dynamic-input', 'id': 'min-papers-input'},
                type='number',
                debounce=True,
#                placeholder='10',
                value=min_papers_input,
                style={'display': 'inline-block', 'width': '60px', 'margin': '0 5px'}
            ),
            " publications in a selected years range (confirm by pressing enter)"
        ])
        
        # Display the top extra info
        try:
            extra_info_top = str(oa_result_dict[selected_country]) + '%'
        except (NameError, KeyError):
            extra_info_top = '\u00A0'

    return {"styles": new_styles}, colorbar, extra_info, extra_info_top







# @app.callback(Output('postal-layer', 'children'), Input('toggle-postal', 'value'))
# def toggle_postal_codes(show_postal):
#     if 'show' in show_postal:
#         labels = [dl.Marker(position=[f['properties'].get('label_y', 0), f['properties'].get('label_x', 0)],
#                             children=dl.Tooltip(f['properties'].get('postal', ''), permanent=True))
#                   for f in countries['features'] if 'postal' in f['properties']]
#         return labels
#     return []

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=True)