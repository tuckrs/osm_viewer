from svg_renderer import SvgRenderer
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time
import numpy as np

def get_city_bounds(city_name: str, radius_km: float) -> dict:
    """Get city bounds based on center point and radius in kilometers"""
    # Initialize geocoder with a custom user agent
    geolocator = Nominatim(user_agent="city_map_art_generator")
    
    # Find city location
    print(f"\nLocating {city_name}...")
    location = geolocator.geocode(city_name)
    if not location:
        raise ValueError(f"Could not find location: {city_name}")
    
    # Add a small delay to respect rate limits
    time.sleep(1)
    
    # Calculate bounds using the radius
    center_point = (location.latitude, location.longitude)
    
    # Calculate rough bounds (this is an approximation)
    # 1 degree of latitude is approximately 111 km
    lat_offset = radius_km / 111.0
    # 1 degree of longitude varies with latitude
    lon_offset = radius_km / (111.0 * abs(np.cos(np.radians(location.latitude))))
    
    bounds = {
        'min_lat': location.latitude - lat_offset,
        'max_lat': location.latitude + lat_offset,
        'min_lon': location.longitude - lon_offset,
        'max_lon': location.longitude + lon_offset,
        'center': center_point
    }
    
    return bounds

def main():
    print("Welcome to City Map Art Generator!")
    print("=================================")
    
    # Get city name
    city = input("Enter city name (e.g., Austin, TX): ")
    
    # Get radius
    while True:
        try:
            radius = float(input("\nEnter radius in kilometers (e.g., 1.0 for downtown, 5.0 for wider area): "))
            if radius > 0:
                break
            print("Radius must be greater than 0")
        except ValueError:
            print("Please enter a valid number")
    
    # Get output filename
    output_file = input("\nEnter output filename (e.g., austin_downtown.svg): ")
    
    # Create renderer
    print("\nCreating map...")
    renderer = SvgRenderer()
    
    try:
        # Get city bounds based on radius
        bounds = get_city_bounds(city, radius)
        print(f"\nFound city center at: {bounds['center']}")
        
        # Remove center point before passing to renderer
        del bounds['center']
        
        # Generate map
        svg_path = renderer.create_minimal_map(city, bounds, output_file)
        print(f"\nSuccess! Map has been saved to: {svg_path}")
        print(f"Map covers a {radius}km radius around {city}")
        
    except Exception as e:
        print(f"\nError creating map: {str(e)}")

if __name__ == "__main__":
    main()
