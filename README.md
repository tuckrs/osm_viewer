# OpenStreetMap PBF Viewer

A simple web application to view and explore OpenStreetMap PBF (Protocol Buffer Format) files.

## Features

- Upload and parse .osm.pbf files
- View basic statistics about the data
- Interactive map visualization of nodes
- Browse sample data from nodes, ways, and relations
- Built with Streamlit for an easy-to-use interface

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run main.py
```

## Usage

1. Launch the application using the command above
2. Use the file uploader to select your .osm.pbf file
3. The application will display:
   - Basic statistics about the file
   - An interactive map showing nodes
   - Sample data that you can explore

## Dependencies

- osmium-tool: For reading PBF files
- folium: For map visualization
- streamlit: For the web interface
- geopandas: For geographic data handling
- protobuf: For parsing PBF format

## Notes

- Large PBF files may take some time to process
- The map view is limited to 1000 nodes for performance reasons
- Temporary files are automatically cleaned up after processing
