import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import tempfile
import webbrowser
import svgwrite
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from typing import Optional, Dict, List
import math
from datetime import datetime
from svg_renderer import SvgRenderer
import os

class MapType:
    CITY = "city"
    GOLF = "golf"

class CityBoundary:
    def __init__(self):
        # Direct Census API endpoints
        self.census_api_key = "553c46b2c8490f6e9f6f5bd4654e5a92cfd090e7"  # Demo key
        self.census_api_url = "https://api.census.gov/data/2020/dec/pl"
        self.osm_api_url = "https://nominatim.openstreetmap.org"
        
    def get_city_bounds(self, city: str, state: str) -> Optional[Dict]:
        """Get city boundary using Overpass API"""
        print(f"\nTrying to get boundary for {city}, {state}")
        
        # Known OSM relation IDs for major cities
        KNOWN_CITIES = {
            ("New York", "New York"): 175905,  # NYC
            ("Los Angeles", "California"): 207359,  # LA
            ("Chicago", "Illinois"): 122604,  # Chicago
            ("Houston", "Texas"): 2688911,  # Houston
            ("Phoenix", "Arizona"): 111257,  # Phoenix
            ("Austin", "Texas"): 113314  # Austin
        }
        
        # Check if we have a known relation ID
        relation_id = KNOWN_CITIES.get((city.strip(), state.strip()))
        if relation_id:
            print(f"Found known relation ID: {relation_id}")
            
            # Query Overpass API for the relation and its geometry
            overpass_url = "https://overpass-api.de/api/interpreter"
            query = f"""
            [out:json][timeout:25];
            (
              relation({relation_id});
              way(r);
              node(w);
            );
            out body;
            """
            
            print("\nQuerying Overpass API...")
            print(f"Query: {query}")
            
            try:
                response = requests.post(overpass_url, data={"data": query})
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get('elements', [])
                    print(f"Found {len(elements)} elements")
                    
                    if elements:
                        # Process the boundary elements
                        nodes = {}
                        ways = {}
                        relation = None
                        
                        for element in elements:
                            if element['type'] == 'node':
                                nodes[element['id']] = {
                                    'lat': element['lat'],
                                    'lon': element['lon']
                                }
                            elif element['type'] == 'way':
                                ways[element['id']] = element['nodes']
                            elif element['type'] == 'relation':
                                relation = element
                        
                        if relation and relation.get('members'):
                            print("Found relation and its members")
                            
                            # Build the polygon from outer ways
                            polygon = []
                            for member in relation['members']:
                                if member['type'] == 'way' and member['role'] == 'outer':
                                    way_id = member['ref']
                                    if way_id in ways:
                                        way_nodes = ways[way_id]
                                        for node_id in way_nodes:
                                            if node_id in nodes:
                                                node = nodes[node_id]
                                                polygon.append([node['lon'], node['lat']])
                            
                            if polygon:
                                print(f"Built polygon with {len(polygon)} points")
                                return {
                                    'type': 'overpass',
                                    'bounds': {
                                        'type': 'Polygon',
                                        'coordinates': [polygon]
                                    }
                                }
                            else:
                                print("No polygon points found")
                        else:
                            print("No relation or members found")
                    else:
                        print("No elements found in response")
                else:
                    print(f"Query failed: {response.text[:200]}")
            except Exception as e:
                print(f"Error querying Overpass API: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"No known relation ID for {city}, {state}")
        
        return None
    
    def get_state_fips(self, state: str) -> Optional[str]:
        """Get state FIPS code"""
        state_fips = {
            'ALABAMA': '01', 'ALASKA': '02', 'ARIZONA': '04', 'ARKANSAS': '05',
            'CALIFORNIA': '06', 'COLORADO': '08', 'CONNECTICUT': '09', 'DELAWARE': '10',
            'DISTRICT OF COLUMBIA': '11', 'FLORIDA': '12', 'GEORGIA': '13', 'HAWAII': '15',
            'IDAHO': '16', 'ILLINOIS': '17', 'INDIANA': '18', 'IOWA': '19',
            'KANSAS': '20', 'KENTUCKY': '21', 'LOUISIANA': '22', 'MAINE': '23',
            'MARYLAND': '24', 'MASSACHUSETTS': '25', 'MICHIGAN': '26', 'MINNESOTA': '27',
            'MISSISSIPPI': '28', 'MISSOURI': '29', 'MONTANA': '30', 'NEBRASKA': '31',
            'NEVADA': '32', 'NEW HAMPSHIRE': '33', 'NEW JERSEY': '34', 'NEW MEXICO': '35',
            'NEW YORK': '36', 'NORTH CAROLINA': '37', 'NORTH DAKOTA': '38', 'OHIO': '39',
            'OKLAHOMA': '40', 'OREGON': '41', 'PENNSYLVANIA': '42', 'RHODE ISLAND': '44',
            'SOUTH CAROLINA': '45', 'SOUTH DAKOTA': '46', 'TENNESSEE': '47', 'TEXAS': '48',
            'UTAH': '49', 'VERMONT': '50', 'VIRGINIA': '51', 'WASHINGTON': '53',
            'WEST VIRGINIA': '54', 'WISCONSIN': '55', 'WYOMING': '56'
        }
        return state_fips.get(state.upper())
    
    def get_place_fips(self, city: str, state: str) -> Optional[str]:
        """Get FIPS code using Census Geocoding API"""
        # Use city center coordinates for geocoding
        params = {
            'street': f'100 Main St',  # Generic central address
            'city': city,
            'state': state,
            'benchmark': 'Public_AR_Current',
            'vintage': 'Current_Current',
            'layers': 'all',
            'format': 'json'
        }
        
        response = requests.get(self.census_geocoder_url, params=params)
        if response.status_code == 200:
            data = response.json()
            try:
                result = data['result']['addressMatches'][0]['geographies']
                if 'Incorporated Places' in result:
                    place = result['Incorporated Places'][0]
                    return place['GEOID']
                elif 'Census Places' in result:
                    place = result['Census Places'][0]
                    return place['GEOID']
            except (KeyError, IndexError):
                print("No place FIPS found in geocoding response")
        return None
    
    def get_tiger_bounds_by_fips(self, place_fips: str) -> Optional[Dict]:
        """Get city boundary from TIGER using FIPS code"""
        params = {
            'where': f"GEOID = '{place_fips}'",
            'outFields': '*',
            'geometryType': 'esriGeometryPolygon',
            'spatialRel': 'esriSpatialRelIntersects',
            'outSR': '4326',
            'f': 'json'
        }
        
        print(f"Querying TIGER API with FIPS: {place_fips}")
        response = requests.get(self.tiger_base_url, params=params)
        print(f"TIGER response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"TIGER features found: {len(data.get('features', []))}")
            if data.get('features'):
                feature = data['features'][0]
                if 'geometry' in feature:
                    return {
                        'type': 'tiger',
                        'bounds': feature['geometry']
                    }
        return None
    
    def get_osm_bounds(self, city: str, state: str) -> Optional[Dict]:
        """Get city boundary from OSM Relations"""
        print(f"\nTrying OSM Relations API for {city}, {state}")
        
        # First try to get the relation ID for the city
        search_params = {
            'q': f"{city}, {state}, United States",
            'format': 'json',
            'limit': 1,
            'featuretype': 'city'
        }
        
        print(f"Search query: {search_params['q']}")
        response = requests.get(f"{self.osm_api_url}/search", params=search_params)
        print(f"Search response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Search failed: {response.text[:200]}")
            return None
        
        data = response.json()
        if not data:
            print("No results found")
            return None
        
        # Get the first result
        result = data[0]
        print(f"Found place: {result.get('display_name')}")
        print(f"OSM type: {result.get('osm_type')}")
        print(f"OSM ID: {result.get('osm_id')}")
        
        # Get the boundary data
        if result.get('osm_type') == 'relation':
            # Convert OSM ID to relation ID if needed
            osm_id = result['osm_id']
            if osm_id < 0:
                osm_id = abs(osm_id)
            
            # Get the relation details with geometry
            details_params = {
                'format': 'json',
                'osm_type': 'R',
                'osm_id': str(osm_id),
                'polygon_geojson': 1
            }
            
            print(f"\nFetching boundary for relation {osm_id}")
            response = requests.get(f"{self.osm_api_url}/details", params=details_params)
            print(f"Details response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Details request failed: {response.text[:200]}")
                return None
            
            data = response.json()
            if 'geometry' in data:
                print("Found boundary geometry")
                return {
                    'type': 'osm',
                    'bounds': data['geometry']
                }
            else:
                print("No geometry in response")
                print(f"Available keys: {list(data.keys())}")
        else:
            print(f"Result is not a relation: {result.get('osm_type')}")
        
        return None

class VectorMapMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Vector Map Maker")
        self.boundary_lookup = CityBoundary()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # City input
        ttk.Label(self.main_frame, text="City:").grid(row=0, column=0, sticky=tk.W)
        self.city_var = tk.StringVar(value="New York")
        self.city_entry = ttk.Entry(self.main_frame, textvariable=self.city_var)
        self.city_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # State input
        ttk.Label(self.main_frame, text="State:").grid(row=1, column=0, sticky=tk.W)
        self.state_var = tk.StringVar(value="New York")
        self.state_entry = ttk.Entry(self.main_frame, textvariable=self.state_var)
        self.state_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # Generate button
        self.generate_btn = ttk.Button(self.main_frame, text="Generate Map", command=self.generate_map)
        self.generate_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.grid(row=3, column=0, columnspan=2)
        
    def generate_map(self):
        city = self.city_var.get().strip()
        state = self.state_var.get().strip()
        
        # Get current directory
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"\nCurrent directory: {current_dir}")
        
        self.status_var.set(f"Looking up location: {city}, {state}")
        self.root.update()
        
        # Get coordinates and location info
        location = get_city_coordinates(f"{city}, {state}")
        if not location:
            self.status_var.set("Could not find location")
            return
            
        self.status_var.set(f"Found location: {location['display_name']}")
        self.root.update()
        
        # Try to get city boundary
        print("\nAttempting to get city boundary...")
        boundary = self.boundary_lookup.get_city_bounds(city, state)
        
        if boundary:
            print("\nBoundary data received:")
            print(f"Type: {boundary['type']}")
            print(f"Bounds data: {json.dumps(boundary['bounds'], indent=2)[:500]}...")
            
            self.status_var.set(f"Using {boundary['type']} boundary data")
            try:
                bbox = get_bbox_from_boundary(boundary['bounds'])
                print(f"\nCalculated bbox: {bbox}")
            except Exception as e:
                print(f"\nError calculating bbox: {str(e)}")
                print("Falling back to radius method...")
                bbox = get_bbox_from_radius(float(location['lat']), float(location['lon']), 5000)
        else:
            print("\nNo boundary data received")
            self.status_var.set("No city boundary found, using radius method...")
            bbox = get_bbox_from_radius(float(location['lat']), float(location['lon']), 5000)
        
        self.root.update()
        
        # Get OSM data for the area
        print(f"\nFetching OSM data with bbox: {bbox}")
        elements = get_osm_data(bbox)
        
        if not elements:
            self.status_var.set("No data received from OSM")
            return
        
        self.status_var.set(f"Received {len(elements)} elements")
        self.root.update()
        
        # Generate SVG
        svg_filename = f"city_{city.replace(' ', '_')}_minimal.svg"
        svg_path = os.path.join(current_dir, svg_filename)
        print(f"\nWill save SVG to: {svg_path}")
        
        try:
            generate_svg(elements, bbox, svg_path)
            self.status_var.set(f"Generated {svg_filename}")
            
            # Try to open the file
            if os.path.exists(svg_path):
                print(f"SVG file exists at: {svg_path}")
                print(f"File size: {os.path.getsize(svg_path)} bytes")
                import webbrowser
                webbrowser.open(svg_path)
            else:
                print(f"Warning: Could not find generated SVG at: {svg_path}")
                
        except Exception as e:
            print(f"Error in SVG generation: {str(e)}")
            self.status_var.set("Error generating SVG")

def get_city_coordinates(city_state):
    try:
        location_with_country = f"{city_state}, United States"
        result = Nominatim(user_agent="vector_map_maker").geocode(location_with_country)
        if result is None:
            result = Nominatim(user_agent="vector_map_maker").geocode(city_state)
        return result.raw
    except GeocoderTimedOut:
        time.sleep(1)
        return get_city_coordinates(city_state)

def get_bbox_from_boundary(boundary):
    """Convert boundary geometry to bounding box"""
    print(f"\nConverting boundary to bbox...")
    print(f"Boundary type: {type(boundary)}")
    
    if isinstance(boundary, list):
        # Handle Overpass API response format
        print("Processing Overpass API format...")
        # Find all nodes in the boundary
        nodes = {}
        ways = {}
        outer_way = None
        
        for element in boundary:
            if element['type'] == 'node':
                nodes[element['id']] = (element['lon'], element['lat'])
            elif element['type'] == 'way':
                ways[element['id']] = element['nodes']
            elif element['type'] == 'relation':
                for member in element.get('members', []):
                    if member.get('role') == 'outer':
                        outer_way = member.get('ref')
                        break
        
        if outer_way and outer_way in ways:
            coords = [nodes[node_id] for node_id in ways[outer_way] if node_id in nodes]
            if coords:
                lons = [p[0] for p in coords]
                lats = [p[1] for p in coords]
                return [
                    min(lons),  # Left
                    min(lats),  # Bottom
                    max(lons),  # Right
                    max(lats)   # Top
                ]
    
    elif isinstance(boundary, dict):
        print("Processing GeoJSON format...")
        if boundary.get('type') == 'Polygon':
            coords = boundary['coordinates'][0]
        elif boundary.get('type') == 'MultiPolygon':
            coords = boundary['coordinates'][0][0]
        else:
            raise ValueError(f"Unsupported geometry type: {boundary.get('type')}")
        
        lons = [p[0] for p in coords]
        lats = [p[1] for p in coords]
        return [
            min(lons),  # Left
            min(lats),  # Bottom
            max(lons),  # Right
            max(lats)   # Top
        ]
    
    raise ValueError("Could not process boundary data format")

def get_bbox_from_radius(lat, lon, radius_m):
    """Calculate bounding box from radius"""
    radius_deg = radius_m / 111000  # Approximate conversion from meters to degrees
    return [
        lon - radius_deg,  # Left
        lat - radius_deg,  # Bottom
        lon + radius_deg,  # Right
        lat + radius_deg   # Top
    ]

def get_osm_data(bbox):
    """Get OSM data for the area"""
    print(f"\nFetching OSM data...")
    print(f"Using bbox: {bbox}")
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential)$"]
        ({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
      way["building"]
        ({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
      way["leisure"="park"]
        ({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
      way["natural"="water"]
        ({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
    );
    (._;>;);
    out body;
    """
    
    print("Sending Overpass query...")
    try:
        response = requests.post(overpass_url, data={"data": query})
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            print(f"Received {len(elements)} elements")
            return elements
        else:
            print(f"Query failed: {response.text[:200]}")
            return []
            
    except Exception as e:
        print(f"Error querying Overpass API: {str(e)}")
        return []

def generate_svg(elements, bbox, filename):
    """Generate SVG for city map"""
    print(f"\nGenerating SVG...")
    print(f"Using bbox: {bbox}")
    print(f"Number of elements: {len(elements)}")
    
    # Convert bbox to bounds format expected by SVG renderer
    bounds = {
        'min_lon': bbox[0],
        'min_lat': bbox[1],
        'max_lon': bbox[2],
        'max_lat': bbox[3]
    }
    print(f"Converted bounds: {bounds}")
    
    # Count element types
    type_counts = {}
    for element in elements:
        elem_type = element.get('type', 'unknown')
        if elem_type == 'way' and 'tags' in element:
            for tag_type, value in element['tags'].items():
                if tag_type in ['highway', 'building', 'leisure', 'natural']:
                    key = f"{tag_type}={value}"
                    type_counts[key] = type_counts.get(key, 0) + 1
        else:
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    
    print("\nElement types found:")
    for elem_type, count in type_counts.items():
        print(f"- {elem_type}: {count}")
    
    try:
        renderer = SvgRenderer()
        print("\nCreating SVG with renderer...")
        svg = renderer.create_city_svg(elements, bounds, "minimal")  # Pass bounds here
        
        print(f"Saving SVG to {filename}")
        svg.saveas(filename)
        print("SVG saved successfully")
        
        # Verify file was created
        import os
        if os.path.exists(filename):
            print(f"Verified: {filename} exists")
            print(f"File size: {os.path.getsize(filename)} bytes")
        else:
            print(f"Warning: {filename} was not created!")
            
    except Exception as e:
        print(f"Error generating SVG: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    root = tk.Tk()
    app = VectorMapMaker(root)
    root.mainloop()

if __name__ == "__main__":
    main()
