import pytest
import os
from svg_renderer import SvgRenderer
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch
import sys
import requests
import overpy
import tkinter as tk
from tkinter import ttk
import math
import numpy as np

def test_svg_renderer_initialization():
    """Test basic renderer initialization with default settings"""
    renderer = SvgRenderer()
    assert renderer.width_inches == 11
    assert renderer.height_inches == 14
    assert renderer.dpi == 300

def test_osm_api_connection():
    """Test that we can connect to the OSM API"""
    api = overpy.Overpass()
    # Query for a small area (Austin, TX downtown)
    result = api.query("""
        area["name"="Austin"]["admin_level"="8"]->.a;
        (way["highway"](area.a)(30.267,-97.743,30.268,-97.742);
        );
        out body;
        >;
        out skel qt;
    """)
    assert len(result.ways) > 0

def test_coordinate_transformation():
    """Test coordinate transformation from lat/lon to SVG coordinates"""
    renderer = SvgRenderer()
    test_points = [(30.267, -97.743), (30.268, -97.742)]
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    transformed = renderer.transform_coordinates(test_points, bounds)
    assert len(transformed) == 2
    assert all(isinstance(p[0], float) and isinstance(p[1], float) 
              for p in transformed)

def test_svg_creation():
    """Test creating an SVG file from OSM data"""
    renderer = SvgRenderer()
    api = overpy.Overpass()
    
    # Get some test data
    result = api.query("""
        area["name"="Austin"]["admin_level"="8"]->.a;
        (way["highway"](area.a)(30.267,-97.743,30.268,-97.742);
        );
        out body;
        >;
        out skel qt;
    """)
    
    # Create test data structure
    test_data = {
        'ways': [([(node.lat, node.lon) for node in way.nodes],
                 way.tags.get('highway', 'unclassified'),
                 way.tags.get('name', ''))  
                for way in result.ways],
        'bounds': {
            'min_lat': 30.267,
            'max_lat': 30.268,
            'min_lon': -97.743,
            'max_lon': -97.742
        }
    }
    
    svg_output = renderer.render(test_data, "test_output.svg")
    
    # Verify file exists and has content
    assert os.path.exists(svg_output)
    assert os.path.getsize(svg_output) > 0
    
    # Verify SVG structure
    tree = ET.parse("test_output.svg")
    root = tree.getroot()
    assert root.tag.endswith('svg')
    assert 'viewBox' in root.attrib
    paths = root.findall('.//{*}path')
    assert len(paths) > 0

def test_generate_minimal_city_map():
    """Test generating a minimal city map with basic styling"""
    renderer = SvgRenderer()
    
    # Test area: Small section of downtown Austin
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    output_file = "test_austin_minimal.svg"
    svg_path = renderer.create_minimal_map("Austin", bounds, output_file)
    
    # Verify file was created
    assert os.path.exists(svg_path)
    
    # Parse SVG and verify structure
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Check SVG attributes
    assert root.tag.endswith('svg')
    assert 'viewBox' in root.attrib
    
    # Verify we have paths (roads)
    paths = root.findall('.//{*}path')
    assert len(paths) > 0
    
    # Check styling
    for path in paths:
        assert 'stroke' in path.attrib
        assert 'stroke-width' in path.attrib
        assert 'fill' in path.attrib
        assert path.attrib['fill'] == 'none'  # Roads should have no fill

def test_map_styling():
    """Test that roads are styled according to their type"""
    renderer = SvgRenderer()
    
    # Create a test map
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    output_file = "test_styling.svg"
    svg_path = renderer.create_minimal_map("Austin", bounds, output_file,
                                         style={
                                             'primary': {'stroke': '#FF0000', 'stroke-width': 3},
                                             'secondary': {'stroke': '#00FF00', 'stroke-width': 2},
                                             'residential': {'stroke': '#0000FF', 'stroke-width': 1}
                                         })
    
    # Parse SVG and check styles
    tree = ET.parse(svg_path)
    root = tree.getroot()
    paths = root.findall('.//{*}path')
    
    # Verify we have different styles
    styles = set()
    for path in paths:
        style = (path.attrib['stroke'], path.attrib['stroke-width'])
        styles.add(style)
    
    # Should have at least 2 different styles (different road types)
    assert len(styles) >= 2

def test_map_dimensions():
    """Test that the map respects specified dimensions"""
    width = 8
    height = 10
    dpi = 300
    
    renderer = SvgRenderer(width_inches=width, height_inches=height, dpi=dpi)
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    output_file = "test_dimensions.svg"
    svg_path = renderer.create_minimal_map("Austin", bounds, output_file)
    
    # Parse SVG and check dimensions
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Check size attributes
    assert root.attrib['width'] == f"{width}in"
    assert root.attrib['height'] == f"{height}in"
    
    # Check viewBox
    viewbox = root.attrib['viewBox'].split()
    assert len(viewbox) == 4
    assert float(viewbox[2]) == width * dpi  # width in pixels
    assert float(viewbox[3]) == height * dpi  # height in pixels

def test_default_road_styles():
    """Test that default road styles match requirements"""
    renderer = SvgRenderer()
    
    # Create test data with different road types
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    # Create test ways with different road types
    ways = [
        ([(30.267, -97.743), (30.268, -97.742)], 'motorway', 'Test Highway'),
        ([(30.267, -97.743), (30.268, -97.742)], 'primary', 'Test Primary'),
        ([(30.267, -97.743), (30.268, -97.742)], 'secondary', 'Test Secondary'),
        ([(30.267, -97.743), (30.268, -97.742)], 'residential', 'Test Residential'),
    ]
    
    data = {
        'bounds': bounds,
        'ways': ways
    }
    
    output_file = "test_road_styles.svg"
    svg_path = renderer.render(data, output_file)
    
    # Parse SVG and check styles
    tree = ET.parse(svg_path)
    root = tree.getroot()
    paths = root.findall('.//{*}path')
    
    # Collect all used colors
    colors = set()
    for path in paths:
        if 'stroke' in path.attrib:
            colors.add(path.attrib['stroke'].upper())
    
    # Verify required colors are present
    required_colors = {
        '#333333',  # Motorway
        '#666666',  # Primary roads
        '#888888',  # Secondary roads
        '#AAAAAA'   # Residential streets
    }
    
    assert required_colors.issubset(colors), "Not all required road colors are present"

def test_street_names_rendering():
    """Test that street names are properly rendered when enabled"""
    renderer = SvgRenderer()
    
    # Create a test map with street names enabled
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    output_file = "test_street_names.svg"
    svg_path = renderer.create_minimal_map("Austin", bounds, output_file, show_street_names=True)
    
    # Parse SVG and check for text elements
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Check for street names group
    text_group = root.find(".//*[@id='street-names']")
    assert text_group is not None, "Street names group not found"
    
    # Check text styling
    style = text_group.get('style')
    assert 'font-family: Arial, sans-serif' in style, "Font family not set correctly"
    assert 'font-size: 4px' in style, "Font size not set correctly"
    assert 'fill: #666666' in style, "Text color not set correctly"
    
    # Check individual text elements
    text_elements = root.findall('.//{*}text')
    for text in text_elements:
        # Verify text properties
        assert text.get('transform') is not None, "Text rotation not applied"
        assert 'font-size: 4px' in text.get('style', ''), "Text size not set to 4px"
        assert text.text, "Text element has no content"

def test_street_name_rendering_quality():
    """Test the quality of street name rendering:
    1. Each street name appears only once
    2. Street names don't overlap with roads
    3. Street name text size is 4px
    """
    renderer = SvgRenderer()
    
    # Create a test map with street names enabled
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    output_file = "test_street_name_quality.svg"
    svg_path = renderer.create_minimal_map("Austin", bounds, output_file, show_street_names=True)
    
    # Parse SVG
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # 1. Test each street name appears only once
    text_elements = root.findall('.//{*}text')
    street_names = [text.text for text in text_elements if text.text]
    unique_names = set(street_names)
    assert len(street_names) == len(unique_names), "Duplicate street names found"
    
    # 2. Test street names don't overlap with roads
    roads_group = root.find(".//*[@id='roads']")
    text_group = root.find(".//*[@id='street-names']")
    assert roads_group is not None and text_group is not None
    
    # Get all road paths and text elements
    road_paths = roads_group.findall('.//{*}path')
    text_elements = text_group.findall('.//{*}text')
    
    # For each text element, check its position
    for text in text_elements:
        # Extract text position from transform attribute
        transform = text.get('transform', '')
        if transform and 'rotate' in transform:
            # Parse rotation and center point from transform
            # Format is: rotate(angle x y)
            parts = transform.replace('rotate(', '').replace(')', '').split()
            if len(parts) >= 3:
                center_x = float(parts[1])
                center_y = float(parts[2])
                
                # Verify text is positioned above or below the road
                # by checking that it's at least half the font size away
                min_distance = 2  # Half the font size
                for path in road_paths:
                    path_d = path.get('d', '')
                    if 'M' in path_d:
                        # Get first point of path
                        first_point = path_d.split('M')[1].split('L')[0].strip().split()
                        if len(first_point) >= 2:
                            road_x = float(first_point[0])
                            road_y = float(first_point[1])
                            
                            # Check vertical distance
                            distance = abs(center_y - road_y)
                            assert distance >= min_distance, \
                                f"Text '{text.text}' is too close to road (distance: {distance})"
    
    # 3. Test street name text size is 4px
    for text in text_elements:
        style = text.get('style', '')
        assert 'font-size: 4px' in style, f"Text size is not 4px for '{text.text}'"

def test_street_names_disabled():
    """Test that street names are not present when disabled"""
    renderer = SvgRenderer()
    
    bounds = {
        'min_lat': 30.267,
        'max_lat': 30.268,
        'min_lon': -97.743,
        'max_lon': -97.742
    }
    
    output_file = "test_no_street_names.svg"
    svg_path = renderer.create_minimal_map("Austin", bounds, output_file, show_street_names=False)
    
    # Parse SVG and verify no text elements
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Check that street names group doesn't exist
    text_group = root.find(".//*[@id='street-names']")
    assert text_group is None, "Street names group found when disabled"
    
    # Check no text elements exist
    text_elements = root.findall('.//{*}text')
    assert len(text_elements) == 0, "Text elements found when street names disabled"

@patch('tkinter.Tk')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
def test_city_list_text_area(mock_bool_var, mock_double_var, mock_string_var, mock_tk):
    """Test the text area for entering multiple cities:
    1. Can add multiple cities
    2. Can read cities back correctly
    3. Handles empty lines and whitespace
    4. Preserves city order
    """
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock
    import tkinter as tk
    
    # Setup mock Tk and variables
    root = mock_tk.return_value
    root.title = MagicMock()
    root.grid = MagicMock()
    root.columnconfigure = MagicMock()
    root.rowconfigure = MagicMock()
    
    # Setup mock variables
    mock_str_instance = MagicMock()
    mock_str_instance.get.return_value = "Austin, TX"
    mock_string_var.return_value = mock_str_instance
    
    mock_double_instance = MagicMock()
    mock_double_instance.get.return_value = 0.6
    mock_double_var.return_value = mock_double_instance
    
    mock_bool_instance = MagicMock()
    mock_bool_instance.get.return_value = False
    mock_bool_var.return_value = mock_bool_instance
    
    # Create GUI instance
    app = MapGeneratorGUI(root)
    
    # Mock the text widget
    app.cities_text = MagicMock()
    app.cities_text.get.return_value = ""
    
    # Test empty initial state
    assert app.cities_text.get("1.0", tk.END).strip() == "", "Text area should be empty initially"
    
    # Test adding single city
    app.cities_text.get.return_value = "Austin, TX\n"
    assert app.cities_text.get("1.0", tk.END).strip() == "Austin, TX", "Single city not stored correctly"
    
    # Test multiple cities
    test_cities = ["Austin, TX", "Seattle, WA", "Portland, OR"]
    app.cities_text.get.return_value = "\n".join(test_cities) + "\n"
    stored_cities = app.cities_text.get("1.0", tk.END).strip().split("\n")
    assert stored_cities == test_cities, "Cities not stored in correct order"
    
    # Test handling of empty lines and whitespace
    messy_input = "\n  Austin, TX  \n\n  Seattle, WA\n  \n  Portland, OR  \n"
    app.cities_text.get.return_value = messy_input
    cities = [city.strip() for city in app.cities_text.get("1.0", tk.END).strip().split('\n') if city.strip()]
    expected_cities = ["Austin, TX", "Seattle, WA", "Portland, OR"]
    assert cities == expected_cities, "Failed to handle whitespace and empty lines correctly"

@patch('tkinter.Tk')
@patch('tkinter.ttk.Frame')
@patch('tkinter.ttk.Button')
@patch('tkinter.Text')
@patch('tkinter.ttk.Notebook')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
def test_batch_export_button(mock_bool_var, mock_double_var, mock_string_var, mock_notebook, mock_text, mock_button, mock_frame, mock_tk):
    """Test the batch export button functionality:
    1. Button exists and is clickable
    2. Button triggers batch export
    3. Button is disabled during export
    4. Button is re-enabled after export
    """
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock
    
    # Setup mock Tk and variables
    root = mock_tk.return_value
    root.title = MagicMock()
    root.grid = MagicMock()
    root.columnconfigure = MagicMock()
    root.rowconfigure = MagicMock()
    
    # Setup mock button
    mock_button_instance = MagicMock()
    mock_button.return_value = mock_button_instance
    
    # Setup mock variables
    mock_str_instance = MagicMock()
    mock_str_instance.get.return_value = "Austin, TX"
    mock_string_var.return_value = mock_str_instance
    
    mock_double_instance = MagicMock()
    mock_double_instance.get.return_value = 0.6
    mock_double_var.return_value = mock_double_instance
    
    mock_bool_instance = MagicMock()
    mock_bool_instance.get.return_value = False
    mock_bool_var.return_value = mock_bool_instance
    
    # Initialize GUI
    app = MapGeneratorGUI(root)
    
    # Verify button was created with correct text and command
    mock_button.assert_any_call(
        mock_frame.return_value,
        text="Generate Maps",
        command=app.generate_batch_maps
    )
    
    # Verify button is disabled by default
    mock_button_instance.state.assert_called_with(['disabled'])
    
    # Simulate button click
    mock_button_instance.invoke()
    
    # Verify generate_batch_maps was called
    assert mock_button_instance.invoke.called, "Button click should trigger generate_batch_maps"

@patch('tkinter.Tk')
@patch('tkinter.ttk.Frame')
@patch('tkinter.ttk.Button')
@patch('tkinter.Text')
@patch('tkinter.ttk.Notebook')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
def test_batch_export_button_state(mock_bool_var, mock_double_var, mock_string_var, mock_notebook, mock_text, mock_button, mock_frame, mock_tk):
    """Test the batch export button state changes:
    1. Button is disabled when no cities are entered
    2. Button is enabled when cities are entered
    3. Button shows processing state during export
    """
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock
    
    # Setup mock Tk and variables
    root = mock_tk.return_value
    root.title = MagicMock()
    root.grid = MagicMock()
    root.columnconfigure = MagicMock()
    root.rowconfigure = MagicMock()
    
    # Setup mock button and text
    mock_button_instance = MagicMock()
    mock_button.return_value = mock_button_instance
    mock_text_instance = MagicMock()
    mock_text.return_value = mock_text_instance
    
    # Setup mock variables
    mock_str_instance = MagicMock()
    mock_str_instance.get.return_value = "Austin, TX"
    mock_string_var.return_value = mock_str_instance
    
    mock_double_instance = MagicMock()
    mock_double_instance.get.return_value = 0.6
    mock_double_var.return_value = mock_double_instance
    
    mock_bool_instance = MagicMock()
    mock_bool_instance.get.return_value = False
    mock_bool_var.return_value = mock_bool_instance
    
    # Initialize GUI
    app = MapGeneratorGUI(root)
    
    # Initially button should be disabled (no cities)
    mock_button_instance.state.assert_called_with(['disabled'])
    
    # Simulate entering a city
    mock_text_instance.get.return_value = "Austin, TX\n"
    app._on_text_change(None)  # Simulate text change event
    
    # Button should be enabled
    mock_button_instance.state.assert_called_with(['!disabled'])
    
    # Simulate clearing cities
    mock_text_instance.get.return_value = "\n"
    app._on_text_change(None)  # Simulate text change event
    
    # Button should be disabled again
    mock_button_instance.state.assert_called_with(['disabled'])

@patch('tkinter.Tk')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
def test_gui_functionality(mock_bool_var, mock_double_var, mock_string_var, mock_tk):
    """Test GUI functionality with mocked tkinter"""
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock
    
    # Create mock root with required attributes
    root = mock_tk.return_value
    root.title = MagicMock()
    root.grid = MagicMock()
    root.columnconfigure = MagicMock()
    root.rowconfigure = MagicMock()
    
    # Mock variable instances
    mock_string_var_instance = MagicMock()
    mock_string_var_instance.get.return_value = "Austin, TX"
    mock_string_var.return_value = mock_string_var_instance
    
    mock_double_var_instance = MagicMock()
    mock_double_var_instance.get.return_value = 0.6
    mock_double_var.return_value = mock_double_var_instance
    
    mock_bool_var_instance = MagicMock()
    mock_bool_var_instance.get.return_value = False
    mock_bool_var.return_value = mock_bool_var_instance
    
    # Create GUI instance
    gui = MapGeneratorGUI(root)
    
    # Verify GUI initialization
    assert root.title.called, "Window title not set"
    assert root.columnconfigure.called, "Root columnconfigure not set"
    assert root.rowconfigure.called, "Root rowconfigure not set"
    
    # Verify variable initialization
    assert mock_string_var.called, "StringVar not created"
    assert mock_double_var.called, "DoubleVar not created"
    assert mock_bool_var.called, "BooleanVar not created"
    
    # Test variable access
    assert gui.city_var.get() == "Austin, TX", "City variable not accessible"
    assert gui.radius_var.get() == 0.6, "Radius variable not accessible"
    assert not gui.show_names_var.get(), "Show names variable not accessible"

@patch('tkinter.Tk')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
@patch('geopy.geocoders.Nominatim')
@patch('numpy.cos')
@patch('numpy.radians')
def test_gui_street_names_integration(mock_radians, mock_cos, mock_geocoder, mock_bool_var, mock_double_var, mock_string_var, mock_tk):
    """Test that GUI properly handles street name toggle for both single and batch export"""
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock, call
    import numpy as np
    
    # Create mock root with required attributes
    root = mock_tk.return_value
    root.title = MagicMock()
    root.grid = MagicMock()
    root.columnconfigure = MagicMock()
    root.rowconfigure = MagicMock()
    root.update = MagicMock()
    
    # Mock variable instances
    mock_city_var_instance = MagicMock()
    mock_city_var_instance.get.return_value = "Austin, TX"
    
    mock_filename_var_instance = MagicMock()
    mock_filename_var_instance.get.return_value = "test_gui_map.svg"
    
    mock_status_var_instance = MagicMock()
    mock_status_var_instance.get.return_value = "Ready"
    
    mock_size_var_instance = MagicMock()
    mock_size_var_instance.get.return_value = "11x14 inches"
    
    mock_string_var.side_effect = [
        mock_city_var_instance,      # city_var
        mock_filename_var_instance,  # filename_var
        mock_status_var_instance,    # status_var
        mock_size_var_instance       # size_var
    ]
    
    mock_double_var_instance = MagicMock()
    mock_double_var_instance.get.return_value = 0.6
    mock_double_var.return_value = mock_double_var_instance
    
    mock_bool_var_instance = MagicMock()
    mock_bool_var_instance.get.return_value = True
    mock_bool_var.return_value = mock_bool_var_instance
    
    # Mock geocoder
    mock_location = MagicMock()
    mock_location.latitude = 30.2672
    mock_location.longitude = -97.7431
    mock_geocoder_instance = MagicMock()
    mock_geocoder_instance.geocode.return_value = mock_location
    mock_geocoder.return_value = mock_geocoder_instance
        
    # Mock numpy functions with realistic values
    mock_radians.side_effect = lambda x: 0.528 if x == 30.2672 else np.radians(x)
    mock_cos.side_effect = lambda x: 0.866 if x == 0.528 else np.cos(x)
        
    # Create GUI instance
    gui = MapGeneratorGUI(root)
    
    # Set up other variables
    gui.city_var = mock_city_var_instance
    gui.filename_var = mock_filename_var_instance
    gui.status_var = mock_status_var_instance
    gui.size_var = mock_size_var_instance
    gui.radius_var = mock_double_var_instance
    gui.show_names_var = mock_bool_var_instance
    gui.geocoder = mock_geocoder_instance
    
    # Test generate_map with street names enabled (single export)
    with patch('tkinter.messagebox.showinfo') as mock_showinfo:
        with patch('gui.SvgRenderer') as mock_renderer:
            mock_renderer_instance = mock_renderer.return_value
            mock_renderer_instance.create_minimal_map.return_value = "test_gui_map.svg"
            
            gui.generate_map()
            
            # Verify the map was generated
            assert mock_renderer_instance.create_minimal_map.call_count > 0, "create_minimal_map was not called"
            
            # Get the actual call arguments
            actual_call = mock_renderer_instance.create_minimal_map.call_args
            actual_bbox = actual_call[0][1]  # args[1] is the bbox dict
            
            # Calculate expected coordinates
            radius_miles = 0.6
            lat_offset = (radius_miles * 1.60934) / 111.0  # Convert miles to km, then to degrees
            lon_offset = lat_offset / 0.866  # Adjust for latitude using pre-calculated cos value
            
            expected_bbox = {
                'min_lat': 30.2672 - lat_offset,
                'max_lat': 30.2672 + lat_offset,
                'min_lon': -97.7431 - lon_offset,
                'max_lon': -97.7431 + lon_offset
            }
            
            # Compare each coordinate value with a reasonable tolerance for floating-point math
            tolerance = 1e-6  # Use a more reasonable tolerance for geographic coordinates
            for key in ['min_lat', 'max_lat', 'min_lon', 'max_lon']:
                assert abs(actual_bbox[key] - expected_bbox[key]) < tolerance, f"{key} mismatch: expected {expected_bbox[key]}, got {actual_bbox[key]}"
            
            # Verify other arguments
            assert actual_call[0][0] == "Austin, TX", "City name mismatch"
            assert actual_call[0][2] == "test_gui_map.svg", "Filename mismatch"
            assert actual_call[1]['show_street_names'] is True, "show_street_names mismatch"
            
            # Test batch export with street names enabled
            gui.cities_text = MagicMock()
            gui.cities_text.get.return_value = "Austin, TX\nSeattle, WA\n"
            gui.batch_button = MagicMock()
            
            gui.generate_batch_maps()
            
            # Verify create_minimal_map was called for each city
            assert mock_renderer_instance.create_minimal_map.call_count >= 2, "Should be called at least twice for batch export"
            
            # Get all calls and verify they use the same bbox calculation
            all_calls = mock_renderer_instance.create_minimal_map.call_args_list
            for call_args in all_calls[-2:]:  # Check last two calls (batch export)
                actual_bbox = call_args[0][1]
                for key in ['min_lat', 'max_lat', 'min_lon', 'max_lon']:
                    assert abs(actual_bbox[key] - expected_bbox[key]) < tolerance, f"{key} mismatch in batch: expected {expected_bbox[key]}, got {actual_bbox[key]}"
                assert call_args[1]['show_street_names'] is True, "show_street_names mismatch in batch"

@patch('tkinter.Tk')
@patch('tkinter.ttk.Frame')
@patch('tkinter.ttk.Button')
@patch('tkinter.Text')
@patch('tkinter.ttk.Notebook')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
@patch('numpy.cos')
@patch('numpy.radians')
@patch('geopy.geocoders.Nominatim')
@patch('svg_renderer.SvgRenderer')
def test_batch_export_folder_organization(mock_renderer_class, mock_geocoder, mock_radians, mock_cos, mock_bool_var, mock_double_var, mock_string_var, mock_notebook, mock_text, mock_button, mock_frame, mock_tk):
    """Test that batch export creates proper folder structure:
    1. Creates city-specific folders
    2. Places files in correct folders
    3. Includes timestamps in filenames
    4. Handles special characters in city names
    """
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock
    import tkinter as tk
    import os
    import time
    
    # Setup mock renderer
    mock_renderer = MagicMock()
    def mock_create_map(city, bounds, filename, show_street_names):
        # Actually create an empty file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write("Mock SVG content")
        return filename
    mock_renderer.create_minimal_map = mock_create_map
    
    mock_renderer_class.return_value = mock_renderer
    
    # Setup mock geocoder
    mock_geocoder_instance = MagicMock()
    mock_geocoder.return_value = mock_geocoder_instance
    
    # Setup mock location responses
    class MockLocation:
        def __init__(self, lat, lon):
            self.latitude = lat
            self.longitude = lon
    
    locations = {
        "Austin, TX": MockLocation(30.2672, -97.7431),
        "New York, NY": MockLocation(40.7128, -74.0060),
        "San Francisco/CA": MockLocation(37.7749, -122.4194)
    }
    
    def mock_geocode(city):
        return locations.get(city)
    
    mock_geocoder_instance.geocode = mock_geocode
    
    # Setup other mocks
    mock_cos.return_value = 1.0
    mock_radians.return_value = 0.5
    
    root = mock_tk.return_value
    root.title = MagicMock()
    
    # Initialize GUI
    app = MapGeneratorGUI(root)
    
    # Mock the text widget and variables
    app.cities_text = MagicMock()
    app.cities_text.get.return_value = "Austin, TX\nNew York, NY\nSan Francisco/CA\n"
    
    # Mock radius and show_names variables
    mock_radius = MagicMock()
    mock_radius.get.return_value = 1.0
    app.radius_var = mock_radius
    
    mock_show_names = MagicMock()
    mock_show_names.get.return_value = True
    app.show_names_var = mock_show_names
    
    # Set a fixed timestamp for testing
    current_time = "20231230_134745"
    with patch('time.strftime', return_value=current_time):
        # Generate maps
        app.generate_batch_maps()
    
    # Verify base directory was created
    base_dir = os.path.join(os.getcwd(), "generated_maps")
    assert os.path.exists(base_dir), "Base output directory not created"
    
    # Verify city directories and files
    expected_structure = {
        "Austin_TX": f"Austin_TX_{current_time}.svg",
        "New_York_NY": f"New_York_NY_{current_time}.svg",
        "San_Francisco_CA": f"San_Francisco_CA_{current_time}.svg"
    }
    
    for city_dir, filename in expected_structure.items():
        dir_path = os.path.join(base_dir, city_dir)
        assert os.path.exists(dir_path), f"Directory not created for {city_dir}"
        
        file_path = os.path.join(dir_path, filename)
        assert os.path.exists(file_path), f"SVG file not created in {city_dir}"
        
        # Verify file has content (any SVG content is acceptable)
        with open(file_path, 'r') as f:
            content = f.read()
            assert content.startswith('<?xml'), f"File does not contain SVG content in {city_dir}"
            assert '<svg' in content, f"File does not contain SVG content in {city_dir}"

@patch('tkinter.Tk')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
@patch('geopy.geocoders.Nominatim')
@patch('numpy.cos')
@patch('numpy.radians')
@patch('svg_renderer.SvgRenderer')
def test_format_selection(mock_renderer_class, mock_geocoder, mock_radians, mock_cos, mock_bool_var, mock_double_var, mock_string_var, mock_tk):
    """Test file format selection functionality:
    1. Single map format selection
    2. Batch export format selection
    3. Format conversion
    """
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock, patch
    import tkinter as tk
    import os
    import time
    
    # Setup mock renderer
    mock_renderer = MagicMock()
    def mock_create_map(city, bounds, filename, show_street_names):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write("<?xml version='1.0'?><svg></svg>")
        return filename
    mock_renderer.create_minimal_map = mock_create_map
    mock_renderer.convert_to_format = MagicMock(return_value="converted_file")
    mock_renderer_class.return_value = mock_renderer
    
    # Setup mock geocoder
    mock_geocoder_instance = MagicMock()
    mock_geocoder.return_value = mock_geocoder_instance
    mock_location = MagicMock()
    mock_location.latitude = 30.2672
    mock_location.longitude = -97.7431
    mock_geocoder_instance.geocode.return_value = mock_location
    
    # Initialize GUI
    root = mock_tk.return_value
    app = MapGeneratorGUI(root)
    
    # Test single map format selection
    app.city_var.set("Austin, TX")
    app.filename_var.set("test_map")
    
    # Test each format
    for format_name, extension in app.formats.items():
        app.format_var.set(format_name)
        app.generate_map()
        
        # Verify SVG was created
        svg_path = os.path.join("generated_maps", "test_map.svg")
        assert os.path.exists(svg_path), f"SVG not created for {format_name}"
        
        # Verify format conversion was called for non-SVG formats
        if extension != '.svg':
            mock_renderer.convert_to_format.assert_called_with(svg_path, extension)
    
    # Test batch export format selection
    app.cities_text.get.return_value = "Austin, TX\nNew York, NY"
    
    # Enable all formats
    for var in app.batch_format_vars.values():
        var.set(True)
    
    # Set timestamp for consistent filenames
    current_time = "20231230_134745"
    with patch('time.strftime', return_value=current_time):
        app.generate_batch_maps()
    
    # Verify files were created for each city and format
    cities = ["Austin_TX", "New_York_NY"]
    for city in cities:
        city_dir = os.path.join("generated_maps", city)
        assert os.path.exists(city_dir), f"Directory not created for {city}"
        
        # Check SVG creation
        svg_path = os.path.join(city_dir, f"{city}_{current_time}.svg")
        assert os.path.exists(svg_path), f"SVG not created for {city}"
        
        # Verify format conversions
        for format_name, extension in app.formats.items():
            if extension != '.svg':
                mock_renderer.convert_to_format.assert_any_call(
                    svg_path,
                    extension
                )

@patch('tkinter.Tk')
@patch('tkinter.ttk.Frame')
@patch('tkinter.ttk.Button')
@patch('tkinter.Text')
@patch('tkinter.ttk.Notebook')
@patch('tkinter.StringVar')
@patch('tkinter.DoubleVar')
@patch('tkinter.BooleanVar')
@patch('numpy.cos')
@patch('numpy.radians')
@patch('geopy.geocoders.Nominatim')
@patch('svg_renderer.SvgRenderer')
def test_format_conversion_errors(mock_renderer_class, mock_geocoder, mock_radians, mock_cos, mock_bool_var, mock_double_var, mock_string_var, mock_notebook, mock_text, mock_button, mock_frame, mock_tk):
    """Test error handling during format conversion:
    1. Missing Inkscape
    2. Conversion failures
    3. Error messages
    """
    from gui import MapGeneratorGUI
    from unittest.mock import MagicMock, patch
    import tkinter as tk
    import os
    import time
    
    # Setup mock renderer
    mock_renderer = MagicMock()
    def mock_create_map(city, bounds, filename, show_street_names):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write("<?xml version='1.0'?><svg></svg>")
        return filename
    mock_renderer.create_minimal_map = mock_create_map
    mock_renderer.convert_to_format = MagicMock(side_effect=Exception("Conversion failed"))
    mock_renderer_class.return_value = mock_renderer
    
    # Setup mock geocoder
    mock_geocoder_instance = MagicMock()
    mock_geocoder.return_value = mock_geocoder_instance
    mock_location = MagicMock()
    mock_location.latitude = 30.2672
    mock_location.longitude = -97.7431
    mock_geocoder_instance.geocode.return_value = mock_location
    
    # Initialize GUI
    root = mock_tk.return_value
    app = MapGeneratorGUI(root)
    
    # Test single map format conversion error
    app.city_var.set("Austin, TX")
    app.filename_var.set("test_map")
    app.format_var.set("Adobe Illustrator (*.ai)")
    
    # Mock messagebox to capture error messages
    with patch('tkinter.messagebox.showerror') as mock_error:
        app.generate_map()
        mock_error.assert_called_with("Error", "Error converting to .ai: Conversion failed")
    
    # Test batch export with conversion errors
    app.cities_text.get.return_value = "Austin, TX\nNew York, NY"
    
    # Enable all formats
    for var in app.batch_format_vars.values():
        var.set(True)
    
    # Set timestamp for consistent filenames
    current_time = "20231230_134745"
    with patch('time.strftime', return_value=current_time):
        with patch('tkinter.messagebox.showwarning') as mock_warning:
            app.generate_batch_maps()
            
            # Verify warnings were shown for conversion failures
            assert mock_warning.call_count > 0, "No warnings shown for conversion failures"
            for call in mock_warning.call_args_list:
                args = call[0]
                assert "Error converting" in args[1], "Incorrect warning message"

@patch('os.path.exists')
@patch('subprocess.run')
def test_inkscape_detection(mock_subprocess_run, mock_path_exists):
    """Test Inkscape path detection:
    1. Windows paths
    2. Linux/Mac paths
    3. Missing Inkscape handling
    """
    from svg_renderer import SvgRenderer
    
    renderer = SvgRenderer()
    
    # Test Windows path detection
    with patch('os.name', 'nt'):
        # Test Program Files path
        mock_path_exists.side_effect = lambda x: 'Program Files' in x
        path = renderer._get_inkscape_path()
        assert 'Program Files\\Inkscape\\bin\\inkscape.exe' in path
        
        # Test Program Files (x86) path
        mock_path_exists.side_effect = lambda x: 'Program Files (x86)' in x
        path = renderer._get_inkscape_path()
        assert 'Program Files (x86)\\Inkscape\\bin\\inkscape.exe' in path
    
    # Test Linux/Mac path
    with patch('os.name', 'posix'):
        path = renderer._get_inkscape_path()
        assert path == 'inkscape'

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test SVG files after tests"""
    yield
    
    # Clean up individual test files
    test_files = [
        "test_styling.svg",
        "test_dimensions.svg",
        "test_gui_output.svg",
        "test_output.svg",
        "test_road_styles.svg",
        "test_street_names.svg",
        "test_no_street_names.svg",
        "test_gui_map.svg",
        "test_street_name_quality.svg"
    ]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            
    # Clean up generated_maps directory and all its subdirectories
    base_output_dir = os.path.join(os.getcwd(), "generated_maps")
    if os.path.exists(base_output_dir):
        for root, dirs, files in os.walk(base_output_dir, topdown=False):
            for name in files:
                if name.endswith('.svg'):
                    try:
                        os.remove(os.path.join(root, name))
                    except OSError:
                        pass  # File might be locked or already deleted
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass  # Directory might not be empty or already deleted
        try:
            os.rmdir(base_output_dir)
        except OSError:
            pass  # Base directory might not be empty or already deleted
