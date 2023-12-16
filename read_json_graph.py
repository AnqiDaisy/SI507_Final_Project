#!/usr/bin/env python
# coding: utf-8

# In[3]:


import networkx as nx
import json

def load_graph_from_json(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return nx.readwrite.json_graph.node_link_graph(data)

def main():
    G = load_graph_from_json('movie_graph.json')
    print(f"Number of nodes: {G.number_of_nodes()}")
    print(f"Number of edges: {G.number_of_edges()}")

if __name__ == '__main__':
    main()


# In[ ]:




