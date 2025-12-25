import folium
import osmnx as ox
import json
from datetime import datetime
import os
import geopandas as gpd
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimestampEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Timestamp objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_interactive_map(network_path: str, features_path: str, boundary_path: str, output_path: str = None) -> str:
    """
    Create an interactive map using Folium.
    
    Args:
        network_path (str): Path to the network GraphML file
        features_path (str): Path to the features GeoJSON file
        boundary_path (str): Path to the boundary GeoJSON file
        output_path (str, optional): Path to save the map. If None, saves in the same directory as network_path
        
    Returns:
        str: Path to the saved map
    """
    try:
        # Load the data
        logger.info("Loading data for visualization...")
        G = ox.load_graphml(network_path)
        features = gpd.read_file(features_path)
        boundary = gpd.read_file(boundary_path)
        
        # Convert graph to GeoDataFrames
        nodes, edges = ox.graph_to_gdfs(G)
        edges = edges.to_crs(epsg=4326)
        
        # Compute map center
        map_center = [
            nodes.geometry.y.mean(),
            nodes.geometry.x.mean()
        ]
        
        # Create Folium map
        logger.info("Creating interactive map...")
        m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")
        
        # Add street network
        folium.GeoJson(
            edges[["geometry"]], 
            name="streets",
            style_function=lambda feat: {
                "color": "#666",
                "weight": 1,
                "opacity": 0.6
            }
        ).add_to(m)
        
        # Add boundary
        folium.GeoJson(
            boundary.to_crs(epsg=4326),
            name="boundary",
            style_function=lambda feat: {
                "fill": False,
                "color": "black",
                "weight": 2
            }
        ).add_to(m)
        
        # Filter and add buildings
        buildings = features[features['building'].notna()]
        if not buildings.empty:
            # Convert buildings to GeoJSON with custom encoder
            buildings_json = json.loads(
                json.dumps(
                    buildings.to_crs(epsg=4326).__geo_interface__,
                    cls=TimestampEncoder
                )
            )
            
            # Add buildings with popups
            folium.GeoJson(
                buildings_json,
                name="buildings",
                style_function=lambda feat: {
                    "fillColor": "orange",
                    "color": "none",
                    "fillOpacity": 0.6
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["building", "name"],
                    aliases=["Type", "Name"],
                    localize=True
                )
            ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Determine output path
        if output_path is None:
            output_path = str(Path(network_path).parent / "interactive_map.html")
        
        # Save the map
        logger.info(f"Saving interactive map to {output_path}")
        m.save(output_path)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error creating interactive map: {str(e)}")
        raise 