#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import networkx as nx
import json
import os

def parse_json_column(df, column_name):
    """
    Parses a JSON-formatted string in a DataFrame column into a Python object.

    Args:
    df (pandas.DataFrame): The DataFrame containing the column.
    column_name (str): The name of the column to parse.

    Returns:
    pandas.Series: A Series where each entry is the parsed Python object from the JSON string.
    """
    return df[column_name].apply(json.loads)

def extract_names_from_json(json_data):
    """
    Extracts a list of names from a list of dictionaries.

    Args:
    json_data (list): A list of dictionaries.

    Returns:
    list: A list of names extracted from the input data.
    """
    return [item['name'] for item in json_data if 'name' in item]

def load_cache(cache_file):
    """
    Loads JSON data from a specified file if it exists.

    Args:
    cache_file (str): File path of the JSON cache file.

    Returns:
    dict: The loaded JSON data as a dictionary, or an empty dictionary if the file does not exist.
    """
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            return json.load(file)
    return {}

def fetch_tmdb_data(movie_id, api_key, cache_data, cache_file):
    """
    Fetches data for a specific movie from The Movie Database (TMDb) API, using caching to save and retrieve data.

    Args:
    movie_id (int): The unique identifier of the movie.
    api_key (str): TMDb API key.
    cache_data (dict): The current cache of movie data.
    cache_file (str): The file path for storing the cache.

    Returns:
    dict: A dictionary containing data for the movie, or None if the request fails.
    """
    if str(movie_id) in cache_data:  
        return cache_data[str(movie_id)]

def add_genre_edges(graph, df):
    """
    Adds edges between movies in a graph based on shared genres.

    Args:
    graph (networkx.Graph): The graph to which the edges will be added.
    df (pandas.DataFrame): The DataFrame containing movie data, including genres.
    """
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
    """
    Creates a graph from a DataFrame of movie data.

    Each movie in the DataFrame is represented as a node in the graph, with attributes such as
    title and genres. Edges are added between movies that share genres.

    Args:
    df (pandas.DataFrame): The DataFrame containing movie data.

    Returns:
    networkx.Graph: A graph representing the movies and their relationships based on shared genres.
    """
    G = nx.Graph()
    for index, row in df.iterrows():
        G.add_node(row['id'], title=row['original_title'], genres=row['genre_names'])
    
    add_genre_edges(G, df)
    return G

def save_graph_to_json(graph, filename):
    """
    Saves a graph to a JSON file.

    This function converts a graph into a JSON format and writes it to a file, allowing
    the graph to be saved and later reloaded.

    Args:
    graph (networkx.Graph): The graph to be saved.
    filename (str): The path of the file where the graph should be saved.
    """
    graph_data = nx.readwrite.json_graph.node_link_data(graph)
    with open(filename, 'w') as f:
        json.dump(graph_data, f)

def main():
    """
    The main function of construct graph.

    This function performs several key tasks:
    - Loads and processes movie data from CSV files.
    - Creates a graph representing the relationships between movies.
    - Saves the graph to a JSON file for later use.

    The function is the entry point of the system and does not take any arguments or return any value.
    """
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

