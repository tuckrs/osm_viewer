import folium
from streamlit_folium import st_folium
import osmium
import geopandas as gpd
from shapely.geometry import Point, LineString
import os

class OSMHandler(osmium.SimpleHandler):
    def __init__(self):
        super(OSMHandler, self).__init__()
        self.nodes = []
        self.ways = []
        self.relations = []
        self.node_count = 0
        self.way_count = 0
        self.relation_count = 0
        self.bounds = {'min_lat': float('inf'), 'max_lat': float('-inf'),
                      'min_lon': float('inf'), 'max_lon': float('-inf')}

    def node(self, n):
        self.node_count += 1
        # Update bounds
        self.bounds['min_lat'] = min(self.bounds['min_lat'], n.location.lat)
        self.bounds['max_lat'] = max(self.bounds['max_lat'], n.location.lat)
        self.bounds['min_lon'] = min(self.bounds['min_lon'], n.location.lon)
        self.bounds['max_lon'] = max(self.bounds['max_lon'], n.location.lon)
        
        # Store only nodes with tags to save memory
        if len(n.tags) > 0:
            self.nodes.append({
                'id': n.id,
                'type': 'node',
                'lat': n.location.lat,
                'lon': n.location.lon,
                'tags': dict(n.tags)
            })

    def way(self, w):
        self.way_count += 1
        if len(w.tags) > 0:  # Store only ways with tags
            self.ways.append({
                'id': w.id,
                'type': 'way',
                'nodes': [n.ref for n in w.nodes],
                'tags': dict(w.tags)
            })

    def relation(self, r):
        self.relation_count += 1
        if len(r.tags) > 0:  # Store only relations with tags
            self.relations.append({
                'id': r.id,
                'type': 'relation',
                'members': [(m.ref, m.type, m.role) for m in r.members],
                'tags': dict(r.tags)
            })

def load_pbf_file(file_path):
    handler = OSMHandler()
    handler.apply_file(file_path)
    return handler

def main():
    st.set_page_config(layout="wide")
    st.title("OpenStreetMap PBF Viewer")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a .osm.pbf file", type=['pbf'])
    
    if uploaded_file:
        # Save uploaded file temporarily
        temp_path = "temp.osm.pbf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # Load and process PBF file
            handler = load_pbf_file(temp_path)
            
            # Display statistics in a clean format
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Nodes", handler.node_count)
            with col2:
                st.metric("Total Ways", handler.way_count)
            with col3:
                st.metric("Total Relations", handler.relation_count)
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["Map View", "Data Explorer", "Search"])
            
            with tab1:
                # Map settings
                st.subheader("Map Settings")
                col1, col2 = st.columns(2)
                with col1:
                    show_nodes = st.checkbox("Show Nodes", value=True)
                    node_limit = st.slider("Number of nodes to display", 100, 5000, 1000)
                with col2:
                    show_ways = st.checkbox("Show Ways", value=True)
                    way_limit = st.slider("Number of ways to display", 100, 2000, 500)
                
                # Create map centered on the data bounds
                center_lat = (handler.bounds['min_lat'] + handler.bounds['max_lat']) / 2
                center_lon = (handler.bounds['min_lon'] + handler.bounds['max_lon']) / 2
                
                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=13
                )
                
                # Add layer control
                feature_groups = {
                    'nodes': folium.FeatureGroup(name="Nodes"),
                    'ways': folium.FeatureGroup(name="Ways")
                }
                
                if show_nodes and handler.nodes:
                    for node in handler.nodes[:node_limit]:
                        folium.CircleMarker(
                            location=[node['lat'], node['lon']],
                            radius=3,
                            popup=f"Node ID: {node['id']}<br>Tags: {node['tags']}",
                            color='red',
                            fill=True
                        ).add_to(feature_groups['nodes'])
                    
                feature_groups['nodes'].add_to(m)
                
                if show_ways and handler.ways:
                    # Add ways (simplified for performance)
                    for way in handler.ways[:way_limit]:
                        if 'highway' in way['tags']:
                            color = 'blue'
                        elif 'building' in way['tags']:
                            color = 'gray'
                        else:
                            color = 'green'
                            
                        popup = f"Way ID: {way['id']}<br>Tags: {way['tags']}"
                        folium.PolyLine(
                            locations=[[node['lat'], node['lon']] for node in handler.nodes if node['id'] in way['nodes']],
                            color=color,
                            popup=popup,
                            weight=2
                        ).add_to(feature_groups['ways'])
                    
                feature_groups['ways'].add_to(m)
                
                # Add layer control
                folium.LayerControl().add_to(m)
                
                # Display map
                st_folium(m, width=800)
            
            with tab2:
                st.subheader("Data Explorer")
                data_type = st.selectbox("Select data type", ["Nodes", "Ways", "Relations"])
                
                # Add filtering options
                st.subheader("Filters")
                tag_filter = st.text_input("Filter by tag (e.g., highway=residential)")
                
                # Pagination
                items_per_page = st.select_slider("Items per page", options=[10, 25, 50, 100], value=25)
                
                data = []
                if data_type == "Nodes":
                    data = handler.nodes
                elif data_type == "Ways":
                    data = handler.ways
                else:
                    data = handler.relations
                
                # Apply filters
                if tag_filter:
                    key, *value = tag_filter.split('=')
                    value = '='.join(value) if value else None
                    if value:
                        data = [item for item in data if key in item['tags'] and item['tags'][key] == value]
                    else:
                        data = [item for item in data if key in item['tags']]
                
                # Pagination
                total_pages = len(data) // items_per_page + (1 if len(data) % items_per_page > 0 else 0)
                page = st.selectbox("Page", range(1, total_pages + 1)) if total_pages > 0 else 1
                
                start_idx = (page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                
                st.write(f"Showing {start_idx + 1} to {min(end_idx, len(data))} of {len(data)} items")
                st.json(data[start_idx:end_idx])
            
            with tab3:
                st.subheader("Search")
                search_query = st.text_input("Search by tags or ID")
                if search_query:
                    results = []
                    try:
                        # Try to search by ID first
                        id_search = int(search_query)
                        results.extend([n for n in handler.nodes if n['id'] == id_search])
                        results.extend([w for w in handler.ways if w['id'] == id_search])
                        results.extend([r for r in handler.relations if r['id'] == id_search])
                    except ValueError:
                        # Search by tags
                        for item in handler.nodes + handler.ways + handler.relations:
                            if any(search_query.lower() in str(v).lower() for v in item['tags'].values()):
                                results.append(item)
                    
                    st.write(f"Found {len(results)} results:")
                    st.json(results[:10])  # Show first 10 results
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    main()
