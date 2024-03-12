from typing import Any

import networkx as nx
import osmnx as ox


def add_travel_times(G: nx.MultiDiGraph, travel_speed: float):
    meters_per_min = travel_speed * 1000 / 60

    for _, _, _, data in G.edges(data=True, keys=True):
        data["time"] = data["length"] / meters_per_min


def add_times_from_center(G: nx.Graph, center_node: Any, weight: str, dest: str):
    G.nodes[center_node][dest] = 0

    for node, time_from_center in nx.shortest_path_length(
        G, source=center_node, weight=weight
    ).items():
        G.nodes[node][dest] = time_from_center


def merge_schedules(network: nx.MultiDiGraph, schedules: nx.MultiDiGraph) -> None:
    schedules = ox.project_graph(schedules, network.graph["crs"])

    schedules_nodes = list(schedules)
    nearest_network_nodes = ox.nearest_nodes(
        network,
        [schedules.nodes[node]["x"] for node in schedules_nodes],
        [schedules.nodes[node]["y"] for node in schedules_nodes],
    )
    nearest_dict = {sn: nn for sn, nn in zip(schedules_nodes, nearest_network_nodes)}

    for src, dst, _, time in schedules.edges(keys=True, data="time"):
        network.add_edge(nearest_dict[src], nearest_dict[dst], time=time)
