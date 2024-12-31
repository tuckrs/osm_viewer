# City Map Art Generator - Project Requirements

## Project Overview
The City Map Art Generator creates beautiful, minimalist city map art suitable for selling on Etsy. The tool transforms OpenStreetMap data into clean, artistic SVG files that can be printed as wall art, used on merchandise, or sold as digital downloads.

## Current Implementation Status

### Core Features Implemented
1. **City Location**
   - Automatic city center detection using geocoding
   - Radius-based map generation
   - Support for any global location
   - Coordinate transformation system
   - Bounds calculation from center point

2. **Map Generation**
   - Clean, minimalist SVG output
   - Automatic road hierarchy styling
   - Proper scaling and dimensions
   - Custom paper sizes and DPI settings
   - SVG validation and testing

3. **User Interfaces**
   - Native GUI (Tkinter)
     ```bash
     python gui.py
     ```
     Features:
     - City name input with geocoding
     - Radius control (0.5 to 10 km)
     - Paper size selection
     - Output filename customization
     - Status updates
     - Error handling
     - Option to add street names
   
   - Command-line interface
     ```bash
     python interactive_map.py
     ```
     Three-step process:
     1. Enter city name (e.g., "Austin, TX")
     2. Specify radius in miles
     3. Choose output filename

4. **Default Styling**
   - Motorway: Bold dark gray (#333333)
   - Primary roads: Medium gray (#666666)
   - Secondary roads: Light gray (#888888)
   - Residential streets: Very light gray (#AAAAAA)
   - All roads with appropriate line weights

## Business Requirements

### Target Market
- Home decor enthusiasts
- City pride / local art collectors
- People seeking personalized gifts
- Interior designers
- Urban planning enthusiasts

### Product Offerings
1. **City Maps**
   - Any global city or location
   - Customizable view radius:
     - 1-2 km: Detailed downtown/neighborhood views
     - 3-5 km: District/area views
     - 5-10 km: Wider city views
   - City outlines should be used as a reference for the outside boundary of the map

2. **Style Variations**
   - Minimalist black and white (implemented)
   - Modern color schemes (planned)
   - Vintage/retro looks (planned)
   - Custom color options (planned)

3. **Size Options**
   - Standard frame sizes (8x10", 11x14", 16x20", 18x24", 24x36")
   - A-series paper sizes (A4, A3, A2)
   - Square formats for Instagram-friendly content

## Technical Details

### Dependencies
#### Python Packages
- tkinter
- numpy
- svgwrite
- geopy
- cairosvg
- Pillow (PIL)

#### Development Dependencies
- pytest

#### System Dependencies
- GTK3 Runtime (required for Cairo on Windows)
  - Windows: Download and install from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
  - Linux: `sudo apt-get install libcairo2-dev`
  - Mac: `brew install cairo`

#### External Dependencies
- Inkscape (required for AI, EPS, and DXF export)
  - Windows: Install from https://inkscape.org/
  - Linux: `sudo apt-get install inkscape`
  - Mac: `brew install inkscape`

#### Optional Extensions
- Inkscape Better DXF Output extension (for DXF export)
  - Can be installed through Inkscape's Extension Manager

### Installation

1. Install system dependencies:
   - Windows: Install GTK3 Runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
   - Linux: `sudo apt-get install libcairo2-dev`
   - Mac: `brew install cairo`

2. Install Python dependencies:
   ```bash
   pip install numpy svgwrite geopy cairosvg Pillow pytest
   ```

3. Install Inkscape from https://inkscape.org/

4. For DXF export support:
   - Open Inkscape
   - Go to Extensions > Extension Manager
   - Search for "Better DXF Output"
   - Install the extension

### Notes
- The application requires Python 3.6 or higher
- Some export formats (AI, EPS, DXF) require Inkscape to be installed
- PNG and PDF export require Cairo (included in GTK3 Runtime)
- For best results with DXF export, install the Better DXF Output extension for Inkscape

### Development
- Run tests with: `python run_tests.py`
- This will verify critical tests are present and then run the test suite

## Quality Standards

### Visual Quality
- Consistent line weights
- Clean intersections
- Balanced composition
- Professional appearance

### Technical Quality
- Scalable vector graphics
- Print-ready files
- Efficient file sizes
- Cross-platform compatibility

## Future Enhancements
1. **Additional Features**
   - Landmarks and points of interest
   - Neighborhood boundaries
   - Water features
   - Parks and green spaces

2. **Business Expansion**
   - Custom framing options
   - Bulk order processing
   - Wholesale capabilities
   - International cities

3. **Automation**
   - Automated listing creation
   - Batch processing
   - Order fulfillment integration
   - Customer preview generation

## Implementation Priority
1. Core map generation with basic styles (COMPLETED)
2. Quality control and testing (COMPLETED)
3. Interactive interface (COMPLETED)
4. Additional style variations (IN PROGRESS)
5. Marketing materials (PLANNED)
6. Advanced customization features (PLANNED)

## Usage Examples
```python
# Example 1: Downtown Austin (0.6 mile radius)
python interactive_map.py
> Enter city name: Austin, TX
> Enter radius in miles: 0.6
> Enter output filename: austin_downtown.svg

# Example 2: Manhattan District (1.9 mile radius)
python interactive_map.py
> Enter city name: Manhattan, NY
> Enter radius in miles: 1.9
> Enter output filename: manhattan_district.svg
```
