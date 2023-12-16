#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import requests
import time
import json
import os
import networkx as nx
import ast
import matplotlib.pyplot as plt


# In[2]:


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

def save_cache(cache_data, cache_file):
    """
    Saves a dictionary as JSON to a specified file.

    Args:
    cache_data (dict): The data to save.
    cache_file (str): File path where the JSON data should be saved.
    """
    with open(cache_file, 'w') as file:
        json.dump(cache_data, file)

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

    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        cache_data[str(movie_id)] = {
            'popularity': data.get('popularity'),
            'revenue': data.get('revenue'),
            'tagline': data.get('tagline'),
            'vote_average': data.get('vote_average'),
            'vote_count': data.get('vote_count')
        }
        save_cache(cache_data, cache_file) 
        return cache_data[str(movie_id)]
    else:
        return None

def add_genre_edges(graph, df):
    """
    Adds edges between movies in a graph based on shared genres.

    Args:
    graph (networkx.Graph): The graph to which the edges will be added.
    df (pandas.DataFrame): The DataFrame containing movie data, including genres.
    """
    genre_dict = {}
    for index, row in df.iterrows():
        genres = row['genre_names']
        for genre in genres:
            if genre in genre_dict:
                for movie_id in genre_dict[genre]:
                    graph.add_edge(row['id'], movie_id)
                genre_dict[genre].append(row['id'])
            else:
                genre_dict[genre] = [row['id']]


# In[3]:


def recommend_movies_based_on_genre(genres, graph, num_recommendations=5):
    """
    Recommends movies based on specified genres from a given graph.

    Args:
    genres (list): A list of genres to filter movies by.
    graph (networkx.Graph): The graph representing movies and their relationships.
    num_recommendations (int): The number of recommended movies to return.

    Returns:
    list: A list of dictionaries, each containing 'id' and 'title' of the recommended movies.
    """
    recommended_movies = []

    for node in graph.nodes(data=True):
        if all(genre in node[1]['genres'] for genre in genres):
            recommended_movies.append({'id': node[0], 'title': node[1]['title']})

    return recommended_movies[:num_recommendations]

def recommend_movies_with_detailed_info(liked_movie_titles, df, graph, num_recommendations=5):
    """
    Recommends movies based on detailed information like genres overlap with liked movies.

    Args:
    liked_movie_titles (list): A list of movie titles that the user likes.
    df (pandas.DataFrame): DataFrame containing movie data.
    graph (networkx.Graph): The graph representing movies and their relationships.
    num_recommendations (int): Number of recommendations to return.

    Returns:
    list: A list of dictionaries with recommended movies' 'id' and 'title'.
    """
    genre_overlap_count = {}
    liked_movies_info = {}
    liked_movie_ids = [] 

    for movie_title in liked_movie_titles:
        movie_row = df[df['title_x'] == movie_title]
        if not movie_row.empty:
            movie_id = movie_row.iloc[0]['id']
            liked_movie_ids.append(movie_id) 
            if movie_id in graph:
                movie_info = graph.nodes[movie_id]
                liked_movies_info[movie_id] = {'title': movie_info['title'], 'genres': movie_info['genres']}  

    for node in graph.nodes(data=True):
        movie_genres = set(node[1]['genres'])
        total_overlap = sum(len(movie_genres.intersection(liked_genres['genres'])) for liked_genres in liked_movies_info.values())
        genre_overlap_count[node[0]] = total_overlap

    df_copy = df.copy()
    df_copy['genre_overlap'] = df_copy['id'].map(genre_overlap_count)

    sorted_movies = df_copy.sort_values(by=['genre_overlap', 'vote_average', 'popularity'], ascending=[False, False, False])
    sorted_movies = sorted_movies[~sorted_movies['id'].isin(liked_movie_ids)]  
    
    recommended_movies_info = sorted_movies.head(num_recommendations)
    return [{'id': row['id'], 'title': row['title_x']} for _, row in recommended_movies_info.iterrows()]


def recommend_movies(preferences, df, graph, num_recommendations=5):
    """
    Recommends movies based on a set of user preferences including genres, cast, and crew.

    Args:
    preferences (dict): A dictionary of user preferences.
    df (pandas.DataFrame): DataFrame containing movie data.
    graph (networkx.Graph): The graph representing movies and their relationships.
    num_recommendations (int): Number of recommendations to return.

    Returns:
    list: A list of dictionaries with recommended movies' 'id' and 'title'.
    """
    genre_filtered = cast_filtered = crew_filtered = pd.DataFrame()
    if 'genres' in preferences and preferences['genres']:
        genre_filtered = df[df['genre_names'].apply(lambda x: preferences['genres'] in x)]
    if 'cast_name' in preferences and preferences['cast_name']:
        cast_filtered = df[df['cast_names'].apply(lambda x: preferences['cast_name'] in x)]
    if 'crew_name' in preferences and preferences['crew_name']:
        crew_filtered = df[df['crew_names'].apply(lambda x: preferences['crew_name'] in x)]

    filtered_movies = df.copy()
    if not genre_filtered.empty:
        filtered_movies = filtered_movies[filtered_movies['id'].isin(genre_filtered['id'])]
    if not cast_filtered.empty:
        filtered_movies = filtered_movies[filtered_movies['id'].isin(cast_filtered['id'])]
    if not crew_filtered.empty:
        filtered_movies = filtered_movies[filtered_movies['id'].isin(crew_filtered['id'])]

    genre_overlap_count = {}
    for node_id, node_data in graph.nodes(data=True):
        node_genres = set(node_data['genres'])
        for _, movie_row in filtered_movies.iterrows():
            if node_id == movie_row['id']:
                continue
            movie_genres = set(graph.nodes[movie_row['id']]['genres']) if movie_row['id'] in graph else set()
            total_overlap = len(node_genres.intersection(movie_genres))
            genre_overlap_count[node_id] = total_overlap

    filtered_movies['genre_overlap'] = filtered_movies['id'].map(genre_overlap_count)

    sorted_movies = filtered_movies.sort_values(by=['genre_overlap', 'vote_average', 'popularity'], ascending=[False, False, False])

    recommended_movies_info = sorted_movies.head(num_recommendations)
    return [{'id': row['id'], 'title': row['title_x']} for _, row in recommended_movies_info.iterrows()]


# In[4]:


def main():
    """
    Main function to run the Movie Recommendation System. It performs several tasks including:
    - Loading and merging movie datasets.
    - Parsing JSON columns in the datasets.
    - Creating a graph structure to represent movies and their relationships.
    - Providing an interactive command-line interface for users to interact with the system.

    The user can query movie details, view genres, visualize the movie network, and get movie recommendations based on different criteria.

    The function does not take any arguments and returns nothing. It continuously runs an interactive loop until the user decides to exit.
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
    G = nx.Graph()
    for index, row in df.iterrows():
        genres = row['genre_names']
        G.add_node(row['id'], title=row['original_title'], genres=genres)
    add_genre_edges(G, df)

    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    while True:
        print("\nMovie Recommendation System")
        print("1 - Query Details of a Specific Movie")
        print("2 - View the Genre and Counts of All Movies")
        print("3 - Show the Visualized Network of All Movies")
        print("4 - Recommend Movies Based on Perfered Genres")
        print("5 - Recommend Movies Based on Liked Movie History")
        print("6 - Recommend Movies Based on Favorite Genre, Cast, and Crew")
        print("7 - Exit")

        choice = input("Enter the number of your choice: ")
        
        
        if choice == '1':
            query = input("Enter the movie title to query: ")
            movie_details = final_df[final_df['title_x'] == query]
            if not movie_details.empty:
                print("\nSelect information to display:")
                print("1 - Basic Information")
                print("2 - Language and Cast/Crew")
                print("3 - Production and Financials")
                print("4 - Ratings and Popularity")
                print("5 - All Information")
                info_choice = input("Enter your choice: ")

                if info_choice == '1':
                    display_cols = ['id', 'title_x', 'overview', 'release_date', 'genre_names', 'homepage']
                elif info_choice == '2':
                    display_cols = ['id', 'title_x', 'original_language', 'runtime', 'cast_names', 'crew_names']
                elif info_choice == '3':
                    display_cols = ['id', 'title_x', 'production_company_names', 'production_country_names', 'budget', 'revenue']
                elif info_choice == '4':
                    display_cols = ['id', 'title_x', 'popularity', 'vote_average', 'vote_count']
                elif info_choice == '5':
                    display_cols = movie_details.columns.tolist()
                else:
                    print("Invalid choice. Showing all information.")
                    display_cols = movie_details.columns.tolist()

                print(movie_details[display_cols].iloc[0])
            else:
                print("Movie not found.")
        
        elif choice == "2":
            genre_counts = final_df['genre_names'].explode().value_counts()
            plt.figure(figsize=(12, 6))
            genre_counts.plot(kind='bar')
            plt.title('Number of Movies per Genre')
            plt.xlabel('Genre')
            plt.ylabel('Number of Movies')
            plt.xticks(rotation=45)
            plt.show()
            
        elif choice == '3':
            sub_nodes = list(G.nodes)
            sub_graph = G.subgraph(sub_nodes)
            plt.figure(figsize=(12, 12))
            pos = nx.spring_layout(sub_graph)
            nx.draw_networkx_nodes(sub_graph, pos, node_size=10)
            nx.draw_networkx_edges(sub_graph, pos, width=0.0005)
            plt.title("Network Visualization")
            plt.show()

        elif choice == '4':
            while True:
                genres_input = input("Enter desired movie genres, separated by commas: ")
                genres = [genre.strip() for genre in genres_input.split(',')]
                available_genres = set(final_df['genre_names'].explode())

                not_found_genres = [genre for genre in genres if genre not in available_genres]
                if not not_found_genres:
                    recommendations = recommend_movies_based_on_genre(genres, G, num_recommendations=5)
                    print("Recommended Movies (ID - Title): ")
                    for movie in recommendations:
                        print(f"{movie['id']} - {movie['title']}")
                    break
                else:
                    print(f"These genres were not found: {', '.join(not_found_genres)}. Please try again.")

        elif choice == '5':
            while True:
                movie_titles_input = input("Enter desired movie titles, separated by commas: ")
                movie_titles = [title.strip() for title in movie_titles_input.split(',')]
                not_found_titles = [title for title in movie_titles if final_df[final_df['title_x'] == title].empty]
                if not not_found_titles:
                    recommendations = recommend_movies_with_detailed_info(movie_titles, final_df, G, num_recommendations=5)
                    print("Recommended Movies (ID - Title): ")
                    for movie in recommendations:
                        print(f"{movie['id']} - {movie['title']}")
                    break
                else:
                    print(f"These titles were not found: {', '.join(not_found_titles)}. Please try again.")

        elif choice == '6':
            preferences = {}
            genre_pref = input("Enter your preferred genre: ")
            if genre_pref:
                preferences['genres'] = genre_pref
            cast_pref = input("Enter your preferred actor/actress (Firstname Lastname): ")
            if cast_pref:
                preferences['cast_name'] = cast_pref
            crew_pref = input("Enter your preferred director (Firstname Lastname): ")
            if crew_pref:
                preferences['crew_name'] = crew_pref

            recommended_movies = recommend_movies(preferences, df, graph = G, num_recommendations=5)
            print("Recommended Movies (ID - Title): ")
            for movie in recommended_movies:
                print(f"{movie['id']} - {movie['title']}")

        elif choice == '7':
            print("Thank you for using the Movie Recommendation System!")
            break

        else:
            print("Invalid input, please try again!")

        if choice in ['4', '5', '6']:
            while True:
                detail_choice = input("\nDo you want details about a specific movie? Enter movie ID or 'no' to skip: ")
                if detail_choice.lower() == 'no':
                    break
                elif detail_choice.isdigit():
                    movie_id = int(detail_choice)
                    movie_details = final_df[final_df['id'] == movie_id]
                    if not movie_details.empty:
                        print("\nSelect information to display:")
                        print("1 - Basic Information")
                        print("2 - Language and Cast/Crew")
                        print("3 - Production and Financials")
                        print("4 - Ratings and Popularity")
                        print("5 - All Information")
                        info_choice = input("Enter your choice: ")

                        if info_choice == '1':
                            display_cols = ['id', 'title_x', 'overview', 'release_date', 'genre_names', 'homepage']
                        elif info_choice == '2':
                            display_cols = ['id', 'title_x', 'original_language', 'runtime', 'cast_names', 'crew_names']
                        elif info_choice == '3':
                            display_cols = ['id', 'title_x', 'production_company_names', 'production_country_names', 'budget', 'revenue']
                        elif info_choice == '4':
                            display_cols = ['id', 'title_x', 'popularity', 'vote_average', 'vote_count']
                        elif info_choice == '5':
                            display_cols = movie_details.columns.tolist()
                        else:
                            print("Invalid choice. Showing all information.")
                            display_cols = movie_details.columns.tolist()

                        print(movie_details[display_cols].iloc[0])
                    else:
                        print("Movie ID not found.")
                else:
                    print("Please enter a numeric movie ID or 'no'.")

if __name__ == "__main__":
    main()


# In[ ]:




