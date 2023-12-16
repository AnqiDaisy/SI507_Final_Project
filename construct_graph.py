#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import networkx as nx
import json
import os

def parse_json_column(df, column_name):
    return df[column_name].apply(json.loads)

def extract_names_from_json(json_data):
    return [item['name'] for item in json_data if 'name' in item]

def load_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            return json.load(file)
    return {}

def fetch_tmdb_data(movie_id, api_key, cache_data, cache_file):
    if str(movie_id) in cache_data:  
        return cache_data[str(movie_id)]

def add_genre_edges(graph, df):
    genre_dict = {}
    for index, row in df.iterrows():
        movie_id = row['id']
        genres = row['genre_names']
        for genre in genres:
            if genre in genre_dict:
                for other_movie_id in genre_dict[genre]:
                    graph.add_edge(movie_id, other_movie_id)
                genre_dict[genre].append(movie_id)
            else:
                genre_dict[genre] = [movie_id]

def create_movie_graph(df):
    G = nx.Graph()
    for index, row in df.iterrows():
        G.add_node(row['id'], title=row['original_title'], genres=row['genre_names'])
    
    add_genre_edges(G, df)
    return G

def save_graph_to_json(graph, filename):
    graph_data = nx.readwrite.json_graph.node_link_data(graph)
    with open(filename, 'w') as f:
        json.dump(graph_data, f)

def main():
    credits_df = pd.read_csv('tmdb_5000_credits.csv')
    movies_df = pd.read_csv('tmdb_5000_movies.csv')

    credits_df['cast'] = parse_json_column(credits_df, 'cast')
    credits_df['crew'] = parse_json_column(credits_df, 'crew')
    movies_df['genres'] = parse_json_column(movies_df, 'genres')
    movies_df['keywords'] = parse_json_column(movies_df, 'keywords')
    movies_df['production_companies'] = parse_json_column(movies_df, 'production_companies')
    movies_df['production_countries'] = parse_json_column(movies_df, 'production_countries')
    movies_df['spoken_languages'] = parse_json_column(movies_df, 'spoken_languages')

    merged_df = pd.merge(movies_df, credits_df, how='left', left_on='id', right_on='movie_id')

    merged_df['cast_names'] = merged_df['cast'].apply(extract_names_from_json)
    merged_df['crew_names'] = merged_df['crew'].apply(extract_names_from_json)
    merged_df['genre_names'] = merged_df['genres'].apply(extract_names_from_json)
    merged_df['keyword_names'] = merged_df['keywords'].apply(extract_names_from_json)
    merged_df['production_company_names'] = merged_df['production_companies'].apply(extract_names_from_json)
    merged_df['production_country_names'] = merged_df['production_countries'].apply(extract_names_from_json)
    merged_df['spoken_language_names'] = merged_df['spoken_languages'].apply(extract_names_from_json)

    merged_df = merged_df.drop(columns=['title_y', 'movie_id', 'cast', 'crew', 'genres', 'keywords', 'production_companies', 'production_countries', 'spoken_languages'])

    merged_df.dropna(subset=['overview', 'release_date', 'runtime'], inplace=True)

    cache_file = 'cache.json'
    cache_data = load_cache(cache_file)

    api_key = "2bd7f718b7eaf4479d7e043103aaaaaf"

    for movie_id in merged_df['id'][:1035]:
        fetch_tmdb_data(movie_id, api_key, cache_data, cache_file)

    with open(cache_file, 'r') as file:
        cache_data = json.load(file)

    tmdb_data_df = pd.DataFrame.from_dict(cache_data, orient='index').reset_index()
    tmdb_data_df.rename(columns={'index': 'id'}, inplace=True)
    tmdb_data_df['id'] = tmdb_data_df['id'].astype(int)

    final_df = pd.merge(merged_df, tmdb_data_df, on='id', how='left')
    df=final_df[:1035]
    G = create_movie_graph(df)
    save_graph_to_json(G, 'movie_graph.json')

if __name__ == '__main__':
    main()

