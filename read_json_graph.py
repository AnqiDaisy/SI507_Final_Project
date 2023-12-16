#!/usr/bin/env python
# coding: utf-8

# In[3]:


import networkx as nx
import json

def load_graph_from_json(filename):
    """
    Loads a graph from a JSON file.

    This function reads a JSON file and reconstructs a graph object from it. The JSON file
    is expected to represent the graph in a format compatible with NetworkX's node-link data.

    Args:
    filename (str): The path of the JSON file containing the graph data.

    Returns:
    networkx.Graph: A graph object reconstructed from the JSON data.
    """
    with open(filename, 'r') as f:
        data = json.load(f)
    return nx.readwrite.json_graph.node_link_graph(data)

def main():
    """
    Main function to demonstrate the loading and basic analysis of a graph.

    This function loads a graph from a JSON file and prints the number of nodes and edges
    in the graph. It serves as a simple demonstration of how to work with the saved graph data.

    No arguments are required.
    """
    G = load_graph_from_json('movie_graph.json')
    print(f"Number of nodes: {G.number_of_nodes()}")
    print(f"Number of edges: {G.number_of_edges()}")

if __name__ == '__main__':
    main()


# In[ ]:




