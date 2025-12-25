import osmnx as ox
import os
from pathlib import Path
import logging
import geopandas as gpd
from typing import Tuple, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_place_name(place: str) -> Tuple[str, str, str]:
    """
    Parse a place name into its components (city, state, country).
    
    Args:
        place (str): Place name in format "City, State, Country"
        
    Returns:
        Tuple[str, str, str]: (city, state, country)
        
    Raises:
        ValueError: If place name is not in the expected format
    """
    parts = [part.strip() for part in place.split(",")]
    if len(parts) != 3:
        raise ValueError("Place name must be in format 'City, State, Country'")
    return parts[0], parts[1], parts[2]

def create_hierarchical_path(base_dir: str, city: str, state: str, country: str) -> Path:
    """
    Create a hierarchical directory path for OSM data.
    
    Args:
        base_dir (str): Base directory for OSM data
        city (str): City name
        state (str): State name
        country (str): Country name
        
    Returns:
        Path: Path object for the hierarchical directory
    """
    # Create safe names for directories
    safe_country = country.replace(" ", "_").lower()
    safe_state = state.replace(" ", "_").lower()
    safe_city = city.replace(" ", "_").lower()
    
    # Create the full path
    path = Path(base_dir) / safe_country / safe_state / safe_city
    path.mkdir(parents=True, exist_ok=True)
    
    return path

def get_osm_file_paths(base_dir: str, city: str, state: str, country: str) -> Tuple[Path, Path, Path]:
    """
    Get the expected file paths for OSM data.
    
    Args:
        base_dir (str): Base directory for OSM data
        city (str): City name
        state (str): State name
        country (str): Country name
        
    Returns:
        Tuple[Path, Path, Path]: Paths to network, features, and boundary files
    """
    safe_city = city.replace(" ", "_").lower()
    data_path = create_hierarchical_path(base_dir, city, state, country)
    
    network_path = data_path / f"{safe_city}_network.graphml"
    features_path = data_path / f"{safe_city}_all_features.geojson"
    boundary_path = data_path / f"{safe_city}_boundary.geojson"
    
    return network_path, features_path, boundary_path

def check_osm_data_exists(base_dir: str, city: str, state: str, country: str) -> bool:
    """
    Check if OSM data already exists for the given location.
    
    Args:
        base_dir (str): Base directory for OSM data
        city (str): City name
        state (str): State name
        country (str): Country name
        
    Returns:
        bool: True if all required files exist, False otherwise
    """
    network_path, features_path, boundary_path = get_osm_file_paths(base_dir, city, state, country)
    return all(path.exists() for path in [network_path, features_path, boundary_path])

def pull_osm_data(place: str, output_dir: str, force: bool = False) -> tuple[Path, Path, Path]:
    """
    Pull comprehensive OSM data for a specified place and save it to the output directory.
    
    Args:
        place (str): The place to pull data for (e.g., "Bar Harbor, Maine, USA")
        output_dir (str): Base directory to save the data to
        force (bool): If True, force re-download even if data exists
        
    Returns:
        tuple[Path, Path, Path]: Paths to the saved network, all features, and boundary files
    """
    try:
        # Parse the place name into components
        city, state, country = parse_place_name(place)
        
        # Get expected file paths
        network_path, features_path, boundary_path = get_osm_file_paths(output_dir, city, state, country)
        
        # Check if data already exists
        if not force and check_osm_data_exists(output_dir, city, state, country):
            logger.info(f"OSM data already exists for {city}, {state}, {country}")
            return network_path, features_path, boundary_path
        
        # Create hierarchical directory structure
        output_path = create_hierarchical_path(output_dir, city, state, country)
        logger.info(f"Created directory structure at: {output_path}")
        
        logger.info(f"Getting administrative boundary for {place}")
        # Get the administrative boundary polygon
        gdf_place = ox.geocode_to_gdf(place)
        boundary = gdf_place.loc[0, "geometry"]
        
        # Save the boundary
        gdf_place.to_file(str(boundary_path), driver="GeoJSON")
        logger.info(f"Saved boundary to {boundary_path}")
        
        logger.info(f"Downloading complete street network for {place}")
        # Download the entire street network (all modes)
        G = ox.graph_from_polygon(boundary, network_type="all")
        
        # Save the network
        ox.save_graphml(G, filepath=str(network_path))
        logger.info(f"Saved network to {network_path}")
        
        # Define all primary OSM feature keys
        tags = {
            "aerialway": True,
            "aeroway": True,
            "amenity": True,
            "barrier": True,
            "boundary": True,
            "building": True,
            "craft": True,
            "emergency": True,
            "geological": True,
            "healthcare": True,
            "highway": True,
            "historic": True,
            "landuse": True,
            "leisure": True,
            "man_made": True,
            "military": True,
            "natural": True,
            "office": True,
            "place": True,
            "power": True,
            "public_transport": True,
            "railway": True,
            "route": True,
            "shop": True,
            "telecom": True,
            "tourism": True,
            "water": True,
            "waterway": True
        }
        
        logger.info(f"Downloading all features for {place}")
        # Fetch all geometries with any of those tags inside the boundary
        all_features = ox.features_from_polygon(boundary, tags)
        
        # Save all features
        all_features.to_file(str(features_path), driver="GeoJSON")
        logger.info(f"Saved all features to {features_path}")
        
        # Log the feature keys we pulled
        logger.info(f"Downloaded feature keys: {all_features.columns.tolist()}")
        
        return network_path, features_path, boundary_path
        
    except Exception as e:
        logger.error(f"Error pulling OSM data: {str(e)}")
        raise
