from collections.abc import Iterable
from typing import Any

import geopandas as gpd
import networkx as nx
import osmnx as ox
from joblib import Parallel, delayed
from shapely.geometry import Polygon


# Adapted from: https://github.com/gboeing/osmnx-examples/blob/main/notebooks/13-isolines-isochrones.ipynb
def _make_isochrones_task(
    G: nx.Graph,
    trip_time: int,
    center_node: Any,
    buffer: int,
) -> tuple[int, Polygon]:
    subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance="time")
    edges_gdf = ox.graph_to_gdfs(subgraph, nodes=False)

    return trip_time, Polygon(edges_gdf.buffer(buffer).geometry.unary_union.exterior)


def make_isochrones(
    G: nx.Graph,
    trip_times: Iterable[int],
    center_nodes: Iterable[Any],
    buffer: int = 25,
) -> gpd.GeoDataFrame:
    results: list[tuple[int, Polygon]] = list(
        Parallel(n_jobs=2)(
            delayed(_make_isochrones_task)(G, trip_time, center_node, buffer)
            for trip_time in trip_times
            for center_node in center_nodes
        )
    )
    results.sort(reverse=True, key=lambda x: x[0])
    isochrone_polys = {key: [value for k, value in results if k == key] for key, _ in results}

    return gpd.GeoDataFrame(
        {"trip_time": list(isochrone_polys.keys())},
        geometry=[gpd.GeoSeries(v).unary_union for v in isochrone_polys.values()],
        crs=G.graph["crs"],
    )
