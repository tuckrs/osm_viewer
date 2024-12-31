import svgwrite
import math
import os
from datetime import datetime
import subprocess
from typing import List, Tuple, Dict, Optional
import numpy as np
import overpy
from decimal import Decimal
import PIL
from PIL import Image

try:
    import cairosvg
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False

class SvgRenderer:
    def __init__(self, width_inches=11, height_inches=14, dpi=300):
        self.width_inches = width_inches
        self.height_inches = height_inches
        self.dpi = dpi
        self.width_px = width_inches * dpi
        self.height_px = height_inches * dpi
        self.api = overpy.Overpass()
        self.inkscape_path = None
        
        # Default styles for different road types
        self.default_styles = {
            'motorway': {'stroke': '#333333', 'stroke-width': 4},
            'primary': {'stroke': '#666666', 'stroke-width': 3},
            'secondary': {'stroke': '#888888', 'stroke-width': 2},
            'residential': {'stroke': '#AAAAAA', 'stroke-width': 1}
        }
        
    def create_minimal_map(self, area_name: str, bounds: Dict[str, float], 
                          output_file: str, style: Optional[Dict] = None, show_street_names=False) -> str:
        """Create a minimal style map for the given area and bounds.
        
        Args:
            area_name: Name of the area (e.g., city name)
            bounds: Dictionary with min_lat, max_lat, min_lon, max_lon
            output_file: Path to save the SVG file
            style: Optional custom styles for different road types
            show_street_names: Optional flag to show street names
            
        Returns:
            Path to the created SVG file
        """
        # Create SVG drawing
        dwg = svgwrite.Drawing(output_file, 
                             size=(f"{self.width_inches}in", f"{self.height_inches}in"),
                             viewBox=(f"0 0 {self.width_px} {self.height_px}"))
        
        # Use provided style or default styles
        road_styles = self.default_styles.copy()
        if style:
            road_styles.update(style)
            
        # Create groups
        roads_group = dwg.g(id='roads')
        dwg.add(roads_group)
        
        if show_street_names:
            text_group = dwg.g(id='street-names', style='font-family: Arial, sans-serif; font-size: 4px; fill: #666666')
            dwg.add(text_group)
            
            # Keep track of street names already added
            used_street_names = set()
        
        # Fetch road data from OSM
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"]({bounds['min_lat']},{bounds['min_lon']},{bounds['max_lat']},{bounds['max_lon']});
            );
            out body;
            >;
            out skel qt;
        """
        result = self.api.query(query)
        
        # Process each way (road)
        ways_data = []
        for way in result.ways:
            # Get road type and name
            road_type = way.tags.get("highway", "residential")
            name = way.tags.get('name', '') if show_street_names else ''
            
            # Get style for this road type
            style = road_styles.get(road_type, road_styles['residential'])
            
            # Get name for this road if show_street_names is True
            name = way.tags.get('name', '') if show_street_names else ''
            
            # Transform coordinates
            points = [(float(node.lat), float(node.lon)) for node in way.nodes]
            transformed = self.transform_coordinates(points, bounds)
            
            # Create path
            path_data = f"M {transformed[0][0]},{transformed[0][1]}"
            for x, y in transformed[1:]:
                path_data += f" L {x},{y}"
            
            # Add path to SVG
            path = dwg.path(d=path_data, 
                          stroke=style['stroke'],
                          stroke_width=style['stroke-width'],
                          fill='none')
            roads_group.add(path)
            
            # Add street name if enabled and name exists and hasn't been used yet
            if show_street_names and name and name not in used_street_names:
                # Calculate middle point
                mid_idx = len(transformed) // 2
                mid_x = transformed[mid_idx][0]
                mid_y = transformed[mid_idx][1]
                
                # Calculate angle
                if mid_idx > 0:
                    dx = transformed[mid_idx][0] - transformed[mid_idx-1][0]
                    dy = transformed[mid_idx][1] - transformed[mid_idx-1][1]
                    angle = math.degrees(math.atan2(dy, dx))
                    # Adjust angle to keep text readable
                    if angle > 90:
                        angle -= 180
                    elif angle < -90:
                        angle += 180
                else:
                    angle = 0
                
                text = dwg.text(name, insert=(mid_x, mid_y),
                              transform=f'rotate({angle} {mid_x} {mid_y})',
                              style='font-size: 4px; fill: #666666')
                text_group.add(text)
                used_street_names.add(name)
        
        # Save and close the SVG file
        dwg.save()
        return output_file
        
    def transform_coordinates(self, points: List[Tuple[float, float]], 
                            bounds: Dict[str, float]) -> List[Tuple[float, float]]:
        """Transform geo coordinates to SVG coordinates"""
        # Calculate scaling to fit in SVG while maintaining aspect ratio
        lat_range = float(bounds['max_lat'] - bounds['min_lat'])
        lon_range = float(bounds['max_lon'] - bounds['min_lon'])
        
        # Add 5% padding
        padding = 0.05
        lat_padding = lat_range * padding
        lon_padding = lon_range * padding
        
        # Adjust bounds with padding
        lat_range += 2 * lat_padding
        lon_range += 2 * lon_padding
        min_lat = float(bounds['min_lat']) - lat_padding
        min_lon = float(bounds['min_lon']) - lon_padding
        
        # Calculate aspect ratios
        map_aspect = lon_range / lat_range
        svg_aspect = self.width_px / self.height_px
        
        # Determine scaling factors
        if map_aspect > svg_aspect:
            # Map is wider than SVG
            scale_x = self.width_px / lon_range
            scale_y = -scale_x  # Negative because SVG Y increases downward
        else:
            # Map is taller than SVG
            scale_y = -self.height_px / lat_range  # Negative because SVG Y increases downward
            scale_x = -scale_y
            
        # Transform all points
        transformed = []
        for lat, lon in points:
            x = (float(lon) - min_lon) * scale_x
            y = (float(lat) - min_lat) * scale_y + self.height_px  # Offset to bottom of SVG
            transformed.append((x, y))
            
        return transformed

    def render(self, data: Dict, output_file: str, show_street_names=False) -> str:
        """
        Render the map data to an SVG file
        
        Args:
            data: Dictionary containing 'ways' and 'bounds' information
                 ways: List of tuples (points, highway_type, name)
                 bounds: Dictionary with min/max lat/lon values
            output_file: Path to save the SVG file
            show_street_names: Optional flag to show street names
            
        Returns:
            Path to the created SVG file
        """
        dwg = svgwrite.Drawing(output_file, 
                             size=(f"{self.width_inches}in", f"{self.height_inches}in"),
                             viewBox=(f"0 0 {self.width_px} {self.height_px}"))
        
        # Style definitions
        styles = {
            'motorway': {'stroke': '#333333', 'stroke-width': 4},
            'trunk': {'stroke': '#333333', 'stroke-width': 3.5},
            'primary': {'stroke': '#666666', 'stroke-width': 3},
            'secondary': {'stroke': '#888888', 'stroke-width': 2.5},
            'tertiary': {'stroke': '#888888', 'stroke-width': 2},
            'residential': {'stroke': '#AAAAAA', 'stroke-width': 1.5},
            'unclassified': {'stroke': '#AAAAAA', 'stroke-width': 1},
            'service': {'stroke': '#AAAAAA', 'stroke-width': 1},
        }
        
        # Create a group for roads
        roads_group = dwg.g(id='roads')
        dwg.add(roads_group)
        
        # Create a group for street names if enabled
        if show_street_names:
            text_group = dwg.g(id='street-names', 
                             style='font-family: Arial, sans-serif; font-size: 4px; fill: #666666')
            dwg.add(text_group)
            
            # Keep track of street names already added
            used_street_names = set()
        
        # Draw each way
        for points, highway_type, name in data['ways']:
            if not points:
                continue
                
            # Transform coordinates
            transformed_points = self.transform_coordinates(points, data['bounds'])
            
            # Create path
            style = styles.get(highway_type, styles['unclassified'])
            path = dwg.path(d=f"M {transformed_points[0][0]},{transformed_points[0][1]}")
            for x, y in transformed_points[1:]:
                path.push(f"L {x},{y}")
                
            path.update({'stroke': style['stroke'],
                        'stroke-width': style['stroke-width'],
                        'fill': 'none',
                        'stroke-linecap': 'round',
                        'stroke-linejoin': 'round'})
            roads_group.add(path)
            
            # Add street name if enabled and name exists and hasn't been used yet
            if show_street_names and name and name not in used_street_names:
                # Calculate middle point of the road for text placement
                mid_idx = len(transformed_points) // 2
                mid_x = transformed_points[mid_idx][0]
                mid_y = transformed_points[mid_idx][1]
                
                # Calculate angle for text rotation
                if mid_idx > 0:
                    dx = transformed_points[mid_idx][0] - transformed_points[mid_idx-1][0]
                    dy = transformed_points[mid_idx][1] - transformed_points[mid_idx-1][1]
                    angle = math.degrees(math.atan2(dy, dx))
                    # Adjust angle to keep text readable
                    if angle > 90:
                        angle -= 180
                    elif angle < -90:
                        angle += 180
                else:
                    angle = 0
                
                text = dwg.text(name, insert=(mid_x, mid_y),
                              transform=f'rotate({angle} {mid_x} {mid_y})',
                              style='font-size: 4px; fill: #666666')
                text_group.add(text)
                used_street_names.add(name)
        
        # Save and close the SVG file
        dwg.save()
        return output_file
        
    def fetch_map_data(self, area_name: str, bounds: Dict[str, float]) -> Dict:
        """
        Fetch map data from OpenStreetMap API
        
        Args:
            area_name: Name of the area (e.g., "Austin")
            bounds: Dictionary with min_lat, max_lat, min_lon, max_lon
            
        Returns:
            Dictionary containing ways and bounds information
        """
        api = overpy.Overpass()
        
        # Construct query
        query = f"""
            area["name"="{area_name}"]["admin_level"="8"]->.a;
            (way["highway"](area.a)
                ({bounds['min_lat']},{bounds['min_lon']},
                 {bounds['max_lat']},{bounds['max_lon']});
            );
            out body;
            >;
            out skel qt;
        """
        
        result = api.query(query)
        
        # Process the results
        ways = []
        for way in result.ways:
            points = [(node.lat, node.lon) for node in way.nodes]
            highway_type = way.tags.get('highway', 'unclassified')
            name = way.tags.get('name', '')
            ways.append((points, highway_type, name))
            
        return {
            'ways': ways,
            'bounds': bounds
        }

    def convert_to_format(self, svg_path: str, output_format: str) -> Optional[str]:
        """Convert SVG to the specified format"""
        output_path = svg_path.rsplit('.', 1)[0] + '.' + output_format.lower()
        
        try:
            if output_format.lower() in ['png', 'pdf']:
                if not CAIRO_AVAILABLE:
                    print(f"Warning: CairoSVG not available. Cannot convert to {output_format}")
                    return None
                    
                if output_format.lower() == 'png':
                    cairosvg.svg2png(url=svg_path, write_to=output_path, dpi=self.dpi)
                else:  # PDF
                    cairosvg.svg2pdf(url=svg_path, write_to=output_path)
            
            elif output_format.lower() in ['ai', 'eps', 'dxf']:
                inkscape_path = self._get_inkscape_path()
                if not inkscape_path:
                    print(f"Warning: Inkscape not found. Cannot convert to {output_format}")
                    return None
                
                try:
                    # Build command based on format
                    cmd = [inkscape_path, svg_path, f'--export-filename={output_path}']
                    
                    if output_format.lower() == 'ai':
                        # Use PostScript format for AI files
                        cmd.extend(['--export-type=ps'])
                        temp_ps = output_path.rsplit('.', 1)[0] + '.ps'
                        cmd[2] = f'--export-filename={temp_ps}'
                    elif output_format.lower() == 'eps':
                        cmd.extend(['--export-type=eps'])
                    else:  # DXF
                        cmd.extend(['--export-type=dxf'])
                    
                    # Run Inkscape
                    result = subprocess.run(
                        cmd,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.stderr:
                        print(f"Inkscape output: {result.stderr}")
                    
                    # If this was an AI file, rename the PS file
                    if output_format.lower() == 'ai' and os.path.exists(temp_ps):
                        os.rename(temp_ps, output_path)
                        
                except subprocess.CalledProcessError as e:
                    print(f"Inkscape error: {e.stderr if e.stderr else str(e)}")
                    return None
                finally:
                    # Clean up temporary PS file if it exists
                    if output_format.lower() == 'ai' and os.path.exists(temp_ps):
                        try:
                            os.remove(temp_ps)
                        except:
                            pass
            
            return output_path if os.path.exists(output_path) else None
            
        except Exception as e:
            print(f"Error converting to {output_format}: {str(e)}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)  # Clean up partial file
                except:
                    pass
            return None

    def _get_inkscape_path(self):
        """Get the path to Inkscape executable based on the operating system"""
        if not self.inkscape_path:
            if os.name == 'nt':  # Windows
                program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
                inkscape_path = os.path.join(program_files, 'Inkscape', 'bin', 'inkscape.exe')
                if not os.path.exists(inkscape_path):
                    # Try x86 program files
                    program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
                    inkscape_path = os.path.join(program_files_x86, 'Inkscape', 'bin', 'inkscape.exe')
                    if os.path.exists(inkscape_path):
                        self.inkscape_path = inkscape_path
                else:
                    self.inkscape_path = inkscape_path
            else:  # Linux/Mac
                try:
                    subprocess.run(['inkscape', '--version'], check=True, capture_output=True)
                    self.inkscape_path = 'inkscape'
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self.inkscape_path = None
        
        return self.inkscape_path
