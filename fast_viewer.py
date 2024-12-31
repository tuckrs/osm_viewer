import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import osmium
import json
import threading
import os
import folium
import webbrowser
import tempfile
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

class FastHandler(osmium.SimpleHandler):
    def __init__(self, target_lat, target_lon, radius_km=10, callback=None):
        super(FastHandler, self).__init__()
        self.target_lat = target_lat
        self.target_lon = target_lon
        # Convert km to rough lat/lon degrees (1 degree ≈ 111km at equator)
        self.search_radius = radius_km / 111.0
        self.callback = callback
        self.reset_data()
        
    def reset_data(self):
        self.nearby_roads = []
        self.nearby_golf_courses = []
        self.processed_nodes = 0
        
    def node(self, n):
        self.processed_nodes += 1
        if self.processed_nodes % 1000000 == 0 and self.callback:  # Status update every million nodes
            self.callback(f"Processed {self.processed_nodes:,} nodes...")

    def way(self, w):
        tags = dict(w.tags)
        nodes = [(n.lat, n.lon) for n in w.nodes]
        
        if len(nodes) < 2:
            return

        # Only process ways near the target coordinates
        if not self._is_near_target(nodes):
            return

        # Check for golf courses
        if 'leisure' in tags and tags['leisure'] == 'golf_course':
            golf_data = {
                'type': 'golf_course',
                'name': tags.get('name', 'Unknown Golf Course'),
                'nodes': nodes,
                'tags': tags
            }
            self.nearby_golf_courses.append(golf_data)
            if self.callback:
                self.callback(f"Found golf course: {golf_data['name']}")

        # Check for major roads
        if 'highway' in tags and tags['highway'] in [
            'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
            'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'
        ]:
            road_data = {
                'type': 'road',
                'name': tags.get('name', 'Unnamed Road'),
                'highway_type': tags['highway'],
                'nodes': nodes,
                'tags': tags
            }
            self.nearby_roads.append(road_data)
            if self.callback:
                self.callback(f"Found road: {road_data['name']}")

    def _is_near_target(self, nodes):
        for lat, lon in nodes:
            if (abs(lat - self.target_lat) <= self.search_radius and 
                abs(lon - self.target_lon) <= self.search_radius):
                return True
        return False

class FastViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Fast Map Viewer")
        self.root.geometry("800x600")
        
        # Initialize geocoder
        self.geolocator = Nominatim(user_agent="osm_viewer")
        
        # Create main container
        main_container = ttk.Frame(root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Create input frame
        input_frame = ttk.Frame(main_container)
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Location entry
        ttk.Label(input_frame, text="Location:").pack(side="left", padx=(0, 5))
        self.location_var = tk.StringVar()
        self.location_entry = ttk.Entry(input_frame, textvariable=self.location_var, width=40)
        self.location_entry.pack(side="left", padx=(0, 10))
        
        # Radius entry
        ttk.Label(input_frame, text="Radius (km):").pack(side="left", padx=(0, 5))
        self.radius_var = tk.StringVar(value="10")
        self.radius_entry = ttk.Entry(input_frame, textvariable=self.radius_var, width=5)
        self.radius_entry.pack(side="left", padx=(0, 10))
        
        # File button
        self.load_btn = ttk.Button(input_frame, text="Load PBF & Search", command=self.load_file)
        self.load_btn.pack(side="left", padx=(0, 10))
        
        # Map button
        self.map_btn = ttk.Button(input_frame, text="View Map", command=self.show_map)
        self.map_btn.pack(side="left", padx=(0, 10))
        self.map_btn.state(['disabled'])
        
        # Status label
        self.status_var = tk.StringVar(value="Enter a location and radius")
        status_label = ttk.Label(input_frame, textvariable=self.status_var)
        status_label.pack(side="left", fill="x", expand=True)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(main_container)
        text_frame.grid(row=1, column=0, sticky="nsew")
        
        self.text = tk.Text(text_frame, wrap="word", width=80, height=40)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        
        self.text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure grid weights
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.processing = False
        self.handler = None
        self.location_coords = None
    
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def append_text(self, text):
        self.text.insert("end", text + "\n")
        self.text.see("end")
        self.root.update_idletasks()
    
    def geocode_location(self, location):
        try:
            # Add explicit country bias for better results
            location_with_country = f"{location}, United States"
            result = self.geolocator.geocode(location_with_country)
            if result is None:
                # Try without country bias
                result = self.geolocator.geocode(location)
            return result
        except GeocoderTimedOut:
            time.sleep(1)  # Wait a second and try again
            return self.geocode_location(location)
    
    def load_file(self):
        if self.processing:
            return
            
        location = self.location_var.get().strip()
        if not location:
            messagebox.showwarning("Warning", "Please enter a location first")
            return
            
        try:
            radius = float(self.radius_var.get())
            if radius <= 0 or radius > 50:
                messagebox.showwarning("Warning", "Radius must be between 0 and 50 km")
                return
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid radius in kilometers")
            return
        
        # First get the coordinates
        self.update_status("Looking up location coordinates...")
        result = self.geocode_location(location)
        if not result:
            messagebox.showerror("Error", f"Could not find coordinates for '{location}'")
            self.update_status("Location not found")
            return
            
        self.location_coords = (result.latitude, result.longitude)
        self.append_text(f"Found coordinates for {result.address}:")
        self.append_text(f"Latitude: {result.latitude}, Longitude: {result.longitude}")
        
        filename = filedialog.askopenfilename(
            title="Select PBF File",
            filetypes=[("PBF files", "*.pbf"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        self.processing = True
        self.load_btn.state(['disabled'])
        self.map_btn.state(['disabled'])
        
        def process_file():
            try:
                self.update_status(f"Processing area around {location}...")
                self.append_text(f"\nProcessing file: {filename}")
                self.append_text(f"Searching within {radius}km radius")
                
                self.handler = FastHandler(
                    self.location_coords[0], 
                    self.location_coords[1],
                    radius,
                    callback=lambda msg: self.root.after(0, self.update_status, msg)
                )
                
                # Process the file
                self.handler.apply_file(filename)
                
                # Display results
                self.root.after(0, self.display_results)
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Error", str(e))
            finally:
                self.root.after(0, self.cleanup)
        
        thread = threading.Thread(target=process_file)
        thread.daemon = True
        thread.start()
    
    def cleanup(self):
        self.processing = False
        self.load_btn.state(['!disabled'])
        if self.handler and (self.handler.nearby_roads or self.handler.nearby_golf_courses):
            self.map_btn.state(['!disabled'])
        self.update_status("Ready")
    
    def display_results(self):
        if not self.handler:
            return
            
        # Display nearby features
        self.append_text(f"\nFeatures found within {self.radius_var.get()}km radius:")
        self.append_text(f"Golf Courses: {len(self.handler.nearby_golf_courses)}")
        self.append_text(f"Major Roads: {len(self.handler.nearby_roads)}")
        
        # List golf courses
        if self.handler.nearby_golf_courses:
            self.append_text("\nGolf Courses:")
            for course in self.handler.nearby_golf_courses:
                self.append_text(f"- {course['name']}")
        
        # List major roads
        if self.handler.nearby_roads:
            self.append_text("\nMajor Roads:")
            seen_roads = set()
            for road in self.handler.nearby_roads:
                if road['name'] not in seen_roads:
                    self.append_text(f"- {road['name']} ({road['highway_type']})")
                    seen_roads.add(road['name'])
    
    def show_map(self):
        if not self.handler or not self.location_coords:
            return
            
        # Create map centered on location
        m = folium.Map(
            location=self.location_coords,
            zoom_start=13
        )
        
        # Add location marker
        location_group = folium.FeatureGroup(name="Search Location")
        folium.CircleMarker(
            location=self.location_coords,
            radius=8,
            popup="Search Center",
            color='red',
            fill=True
        ).add_to(location_group)
        
        # Add search radius circle
        folium.Circle(
            location=self.location_coords,
            radius=float(self.radius_var.get()) * 1000,  # Convert km to meters
            color='red',
            fill=False,
            weight=2
        ).add_to(location_group)
        location_group.add_to(m)
        
        # Add golf courses
        if self.handler.nearby_golf_courses:
            golf_group = folium.FeatureGroup(name="Golf Courses")
            for course in self.handler.nearby_golf_courses:
                folium.Polygon(
                    locations=course['nodes'],
                    popup=course['name'],
                    color='green',
                    fill=True,
                    fill_color='green'
                ).add_to(golf_group)
            golf_group.add_to(m)
        
        # Add roads with different colors based on type
        road_colors = {
            'motorway': 'red',
            'trunk': 'orange',
            'primary': 'yellow',
            'secondary': 'blue',
            'tertiary': 'purple',
            'motorway_link': 'red',
            'trunk_link': 'orange',
            'primary_link': 'yellow',
            'secondary_link': 'blue',
            'tertiary_link': 'purple'
        }
        
        road_groups = {}
        for road_type in road_colors.keys():
            road_groups[road_type] = folium.FeatureGroup(name=f"Roads - {road_type}")
        
        for road in self.handler.nearby_roads:
            road_type = road['highway_type']
            if road_type in road_colors:
                color = road_colors[road_type]
                folium.PolyLine(
                    locations=road['nodes'],
                    popup=road['name'],
                    color=color,
                    weight=2 if '_link' in road_type else 4
                ).add_to(road_groups[road_type])
        
        for group in road_groups.values():
            group.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Save and open map
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            m.save(tmp.name)
            webbrowser.open('file://' + tmp.name)

def main():
    root = tk.Tk()
    app = FastViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
