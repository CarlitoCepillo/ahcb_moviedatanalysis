import sys
import dash
import flask
from dash import dcc
from dash import html
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
import dateutil as du
import json
import matplotlib.pyplot as plt

def convert_genres(s):
	l = json.loads(s.replace('\'', '"'))
	ret = []
	for d in l:
		ret.append(d['name'])
	return ret

class ThemeAnalysis():

    def __init__(self, application = None):

        self.df = pd.read_csv('AHCB_movie_data_analysis/theme_popularite/data/theme_popularite.csv')
        self.df.genres = self.df.genres.apply(convert_genres)
        df_exploded = self.df.explode('genres')
        self.df_year = df_exploded.groupby(["release_year","genres"], as_index=False).agg({"budget":"sum", "revenue":"sum", "popularity":"mean", "vote_average":"mean", "vote_count":"mean", "title":"count"})
        self.df_year = self.df_year.set_index('release_year')
        self.years = sorted(set(self.df_year.index.values))

        self.df_bar = df_exploded.copy()
        self.df_bar["release_year"] = (self.df_bar["release_year"] / 10)
        self.df_bar = self.df_bar.astype({"release_year":"int32"})
        self.df_bar["release_year"] = (self.df_bar["release_year"] * 10)

        self.last_working_year = 1915
        self.df_bar = self.df_bar.groupby(["release_year", "genres"]).agg({"title":"count"}).reset_index()
        

        self.main_layout = html.Div(children=[
            html.H3(children='Évolution des revenus des films par rapport à leurs genres et au budget alloué'),

            html.Div('Commencez par cliquer sur une date de votre choix sur le slider. Déplacez la souris sur une bulle pour avoir les graphiques du thème en bas. Utilisez le slider pour choisir l\'année.'), 

            html.Div([
                    html.Div([ dcc.Graph(id='theme-main-graph', animate=True), ], style={'width':'90%', }),

                    html.Div([
                        html.Br(),
                        html.Br(),
                        html.Br(),
                        html.Br(),
                        html.Br(),
                    ], style={'margin-left':'15px', 'width': '7em', 'float':'right'}),
                ], style={
                    'padding': '10px 50px', 
                    'display':'flex',
                    'justifyContent':'center'
                }),            
            
            html.Div([
                html.Div(
                    dcc.Slider(
                            id='theme-crossfilter-year-slider',
                            min=self.years[0],
                            max=self.years[-1],
                            step = 1,
                            value=self.years[0],
                            marks={str(year): str(year) for year in self.years[::5]},
                    ),
                    style={'display':'inline-block', 'width':"90%"}
                ),
                ], style={
                    'padding': '0px 50px', 
                    'width':'100%'
                }),

            html.Br(),
            html.Div(id='theme-div-theme'),

            html.Div([
                dcc.Graph(id='theme-revenue-time-series', 
                          style={'width':'33%', 'display':'inline-block'}),
                dcc.Graph(id='theme-budget-time-series',
                          style={'width':'33%', 'display':'inline-block', 'padding-left': '0.5%'}),
                dcc.Graph(id='theme-moviecount-bar-plot',
                          style={'width':'33%', 'display':'inline-block', 'padding-left': '0.5%'}),
            ], style={ 'display':'flex', 
                       'borderTop': 'thin lightgrey solid',
                       'borderBottom': 'thin lightgrey solid',
                       'justifyContent':'center', }),
            html.Br(),
            dcc.Markdown("""
            #### À propos
            * Données : [Kaggle / TMdB](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset)
            * (c) 2022 Adrien Huet et Charlie Brosse
            """),
           

        ], style={
                 'padding': '10px 50px 10px 50px',
                 }
        )
        
        if application:
            self.app = application
        else:
            self.app = dash.Dash(__name__)
            self.app.layout = self.main_layout
        self.app.callback(
            dash.dependencies.Output('theme-main-graph', 'figure'),
            [dash.dependencies.Input('theme-crossfilter-year-slider', 'value')])(self.update_graph)
        self.app.callback(
            dash.dependencies.Output('theme-div-theme', 'children'),
            dash.dependencies.Input('theme-main-graph', 'hoverData'))(self.theme_chosen)
        self.app.callback(
            dash.dependencies.Output('theme-revenue-time-series', 'figure'),
            [dash.dependencies.Input('theme-main-graph', 'hoverData'),])(self.update_revenue_timeseries)
        self.app.callback(
            dash.dependencies.Output('theme-budget-time-series', 'figure'),
            [dash.dependencies.Input('theme-main-graph', 'hoverData'),])(self.update_budget_timeseries)
        self.app.callback(
            dash.dependencies.Output('theme-moviecount-bar-plot', 'figure'),
            [dash.dependencies.Input('theme-main-graph', 'hoverData'),])(self.update_moviecount_barplot)


    def update_graph(self, year):
        try:
            size = self.df_year.loc[year]['title'].to_numpy()
            self.last_working_year = year
        except:
            year = self.last_working_year
            size = self.df_year.loc[year]['title'].to_numpy()

        nb_films = size.sum()
        s = [((s/nb_films) * 100)*2 + 10 for s in size]

        dfg = self.df_year.loc[year]
        fig = px.scatter(dfg, x = "budget", y = "revenue", 
                        size = s, 
                        color = "genres",
                        hover_name="genres")
        fig.update_layout(
                    xaxis = dict(title='Budget moyen par film',
                    type= 'linear'),
        yaxis = dict(title="Revenu moyen par film", 
            ),

        margin={'l': 40, 'b': 30, 't': 10, 'r': 0},
        hovermode='closest',
        showlegend=False,
        )
            

        return fig

    def create_time_series(self, genre, what, title):
        return {
            'data': [go.Scatter(
                x = self.years,
                y = self.df_year[self.df_year["genres"] == genre][what],
                mode = 'lines+markers',
            )],
            'layout': {
                'height': 325,
                'margin': {'l': 50, 'b': 20, 'r': 10, 't': 20},
                'yaxis': {'title':title},
                'xaxis': {'showgrid': False}
            }
        }


    def get_theme(self, hoverData):
        if hoverData == None:  # init value
            return "War"
        return hoverData['points'][0]['hovertext']

    def theme_chosen(self, hoverData):
        return self.get_theme(hoverData)

    # graph movie revenue vs years
    def update_revenue_timeseries(self, hoverData):
        theme = self.get_theme(hoverData)
        return self.create_time_series(theme, 'revenue', 'Revenu moyen généré par le film (US $)')

    # graph movie budget vs years
    def update_budget_timeseries(self, hoverData):
        theme = self.get_theme(hoverData)
        return self.create_time_series(theme, 'budget', "Budget moyen du film (US $)")

    # graph movie count vs years
    def update_moviecount_barplot(self, hoverData):
        theme = self.get_theme(hoverData)

        xlab = [1910,1920,1930,1940,1950,1960,1970,1980,1990,2000,2010]

        return {
            'data': [go.Bar(
                x = xlab,
                y = self.df_bar[self.df_bar["genres"] == theme]["title"],
                # mode = 'lines+markers',
            )],
            'layout': {
                'height': 325,
                # 'margin': {'l': 50, 'b': 20, 'r': 10, 't': 20},
                'yaxis': {'title':"Nombre de films",},
                'xaxis': {'showgrid': False}
            }
        }


    def run(self, debug=False, port=8050):
        self.app.run_server(host="0.0.0.0", debug=debug, port=port)

if __name__ == '__main__':
    tmA = ThemeAnalysis()
    tmA.run(port=8055)