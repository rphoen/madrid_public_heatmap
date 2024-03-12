from datetime import date, datetime, time

import geopandas as gpd
import networkx as nx
import pandas as pd
from pyproj import CRS
from shapely import Point

from .cache import DownloadCache

SOURCES = {
    "metro": "https://www.arcgis.com/sharing/rest/content/items/5c7f2951962540d69ffe8f640d94c246/data",
    "cercanias": "https://www.arcgis.com/sharing/rest/content/items/1a25440bf66f499bae2657ec7fb40144/data",
    "trams": "https://www.arcgis.com/sharing/rest/content/items/aaed26cc0ff64b0c947ac0bc3e033196/data",
    # "busses": "https://www.arcgis.com/sharing/rest/content/items/357e63c2904f43aeb5d8a267a64346d8/data",
}


class Schedules:
    def __init__(self, sources: dict[str, str] = SOURCES) -> None:
        self._sources = sources
        self._cache = DownloadCache()
        self._cache.download(sources)

    def get_stop_locations(self, name: str) -> gpd.GeoDataFrame:
        df = pd.read_csv(self._cache.get_path(name, "stops.txt"))
        df["geometry"] = df.apply(lambda x: Point(x["stop_lon"], x["stop_lat"]), axis=1)
        return gpd.GeoDataFrame(
            data=df[["stop_id", "geometry"]], crs="EPSG:4326", geometry="geometry"
        )

    def get_all_stop_locations(self) -> dict[str, gpd.GeoDataFrame]:
        return {name: self.get_stop_locations(name) for name in self._sources}

    def get_trip_graph(self, name: str) -> nx.Graph:
        def first_uniques(row, _set=set()):
            result = row["stop_id"] not in _set
            _set.add(row["stop_id"])
            return result

        stop_times = pd.read_csv(self._cache.get_path(name, "stop_times.txt"))
        stop_times = stop_times.loc[stop_times.apply(first_uniques, axis=1)]
        stops = pd.read_csv(self._cache.get_path(name, "stops.txt"))
        stops = {row["stop_id"]: (row["stop_lon"], row["stop_lat"]) for _, row in stops.iterrows()}

        placeholder_date = date(1970, 1, 1)
        G = nx.Graph()
        G.graph["crs"] = CRS.from_epsg(4326)

        for trip_id in stop_times["trip_id"].unique():
            trip_stops: pd.DataFrame = stop_times.loc[stop_times["trip_id"] == trip_id]
            last_time, last_stop = (
                time.fromisoformat(trip_stops.iloc[0]["arrival_time"]),
                trip_stops.iloc[0]["stop_id"],
            )
            G.add_node(last_stop, x=stops[last_stop][0], y=stops[last_stop][1])

            for _, row in trip_stops.iloc[1:].iterrows():
                curr_stop = row["stop_id"]
                curr_time = time.fromisoformat(row["arrival_time"])
                duration = (
                    abs(
                        datetime.combine(placeholder_date, curr_time)
                        - datetime.combine(placeholder_date, last_time)
                    ).total_seconds()
                    / 60
                )
                G.add_node(curr_stop, x=stops[curr_stop][0], y=stops[curr_stop][1])
                G.add_edge(last_stop, curr_stop, time=duration)
                last_time, last_stop = curr_time, curr_stop

        return G

    def get_all_trip_graphs(self) -> dict[str, nx.Graph]:
        return {name: self.get_trip_graph(name) for name in self._sources}
