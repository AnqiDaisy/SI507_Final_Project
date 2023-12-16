# SI507_Final_Project
SI507 Final Project for Anqi Sun

This project is a Movie Recommendation System.

# API

Special instructions: to use the TMDB API, you may request a API key here: https://developer.themoviedb.org/docs/authentication-application

By applying the API key, the information can be retrieved via url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"

# Interact with the program
You may interact with the program via command line prompts. 7 choices are available for the user, including:

1 - Query Details of a Specific Movie (Get specific information about a certain movie)

2 - View the Genre and Counts of All Movies (View the histogram of genre and counts)

3 - Show the Visualized Network of All Movies (View the visualization of network)

4 - Recommend Movies Based on Preferred Genres (user input1 or more preferred genres, and the system will provide at most 5 recommendation movies based on the network)

5 - Recommend Movies Based on Liked Movie History (user input 1 or more previously loved movies, and the system will provide at most 5 recommendation movies based on the network and also vote average and popularity)

6 - Recommend Movies Based on Favorite Genre, Cast, and Crew (user input 1 favorite genre, 1 favorite cast, and 1 favorite cast, and the system will provide at most 5 recommendation movies based on the network and also vote average and popularity)

7 – Exit


After option 1,4,5,7, if you want to get details about any recommended movie, you are also provided for 5 options: 

1 - Basic Information (including 'id', 'title_x', 'overview', 'release_date', 'genre_names', 'homepage')

2 - Language and Cast/Crew (including 'id', 'title_x', 'original_language', 'runtime', 'cast_names', 'crew_names')

3 - Production and Financials (including 'id', 'title_x', 'production_companies', 'production_countries', 'budget', 'revenue')

4 - Ratings and Popularity (including 'id', 'title_x', 'popularity', 'vote_average', 'vote_count') 

5 - All Information (including all the information about one movie we have in our dataset)



# Packages required
Python packages required: pandas, requests, network, ast, matplotlib.pyplot, (also json and os)

# Files
final_anqi.py is the complete code for this project

cache.json is the cache for information retrieved from TMDB API

construct_graph.py is the python file that constructs the graphs from stored data

movie_graph.json is the JSON file with the graph

read_json_graph.py is a stand along python file that reads the json of the graph

tmdb_5000_credits.csv.zip is the zip of the tmdb_5000_credits.csv data

tmdb_5000_movies.csv is the tmdb_5000_movies data

# Data Structure (network)
Our system utilizes a graph to represent and analyze relationships between movies based on various attributes like genres, cast, and crew. The graph structure facilitates the identification of similar movies and enhances the recommendation process.

Nodes: In the graph, each node represents an individual movie. Every node is tagged with several attributes including:

id: A unique identifier for the movie.

title: The title of the movie.

genres: A list of genres associated with the movie.

Edges: Edges in the graph represent the relationships between movies. An edge is formed between two movies if they share certain characteristics. Currently, edges are primarily based on shared genres. If two movies belong to the same genre, an edge is created between them.

Graph Type: The graph is undirected, indicating that the relationships are mutual. The connection between any two movies does not have a direction or hierarchy.

Graph Construction Process
Node Creation: For each movie in the dataset, a node is created in the graph with its associated attributes.

Edge Formation: To form edges, the graph algorithm iterates through each movie and identifies other movies that share common genres. An edge is established for each of these shared attributes.

 



