#!/usr/bin/env python
# coding: utf-8

# In[9]:


import pandas as pd
import requests
import time
import json
import os
import networkx as nx
import ast
import matplotlib.pyplot as plt


# In[10]:


def parse_json_column(df, column_name):
    return df[column_name].apply(json.loads)

def extract_names_from_json(json_data):
    return [item['name'] for item in json_data if 'name' in item]

def load_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            return json.load(file)
    return {}

def save_cache(cache_data, cache_file):
    with open(cache_file, 'w') as file:
        json.dump(cache_data, file)

def fetch_tmdb_data(movie_id, api_key, cache_data, cache_file):
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


# In[11]:


def recommend_movies_based_on_genre(genres, graph, num_recommendations=5):
    recommended_movies = []

    for node in graph.nodes(data=True):
        if all(genre in node[1]['genres'] for genre in genres):
            recommended_movies.append({'id': node[0], 'title': node[1]['title']})

    return recommended_movies[:num_recommendations]

def recommend_movies_with_detailed_info(liked_movie_ids, df, graph, num_recommendations=5):
    genre_overlap_count = {}
    liked_movies_info = {}
    for movie_id in liked_movie_ids:
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

def recommend_movies(preferences, df, num_recommendations=5):
    filtered_movies = df
    for key, value in preferences.items():
        if key in df.columns and value:
            if key == 'cast_name' or key == 'crew_name':
                filtered_movies = filtered_movies[filtered_movies[key].apply(lambda x: value in x)]
            else:
                filtered_movies = filtered_movies[filtered_movies[key] == value]

    recommended_movies = filtered_movies.sort_values(by=['vote_average', 'popularity'], ascending=False)
    return [{'id': row['id'], 'title': row['title_x']} for _, row in recommended_movies.head(num_recommendations).iterrows()]


# In[22]:


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
            cast_pref = input("Enter your preferred actor/actress: ")
            if cast_pref:
                preferences['cast_name'] = cast_pref
            crew_pref = input("Enter your preferred director: ")
            if crew_pref:
                preferences['crew_name'] = crew_pref

            recommended_movies = recommend_movies(preferences, df, num_recommendations=5)
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




