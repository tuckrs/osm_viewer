import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import osmium
import json
from collections import defaultdict
import threading
import os
import folium
import webbrowser
from shapely.geometry import Point, LineString
import tempfile

class MapHandler(osmium.SimpleHandler):
    def __init__(self, callback=None):
        super(MapHandler, self).__init__()
        self.callback = callback
        self.reset_data()
        
    def reset_data(self):
        # Store cities/towns
        self.cities = []
        # Store golf courses
        self.golf_courses = []
        # Store major roads
        self.major_roads = []
        # Store bounds
        self.bounds = {
            'min_lat': float('inf'),
            'max_lat': float('-inf'),
            'min_lon': float('inf'),
            'max_lon': float('-inf')
        }
        
    def update_bounds(self, lat, lon):
        self.bounds['min_lat'] = min(self.bounds['min_lat'], lat)
        self.bounds['max_lat'] = max(self.bounds['max_lat'], lat)
        self.bounds['min_lon'] = min(self.bounds['min_lon'], lon)
        self.bounds['max_lon'] = max(self.bounds['max_lon'], lon)

    def node(self, n):
        tags = dict(n.tags)
        if 'place' in tags and tags['place'] in ['city', 'town']:
            city_data = {
                'type': 'city',
                'name': tags.get('name', 'Unknown'),
                'lat': n.location.lat,
                'lon': n.location.lon,
                'population': tags.get('population', 'Unknown'),
                'tags': tags
            }
            self.cities.append(city_data)
            self.update_bounds(n.location.lat, n.location.lon)
            if self.callback:
                self.callback(f"Found city: {city_data['name']}")

    def way(self, w):
        tags = dict(w.tags)
        nodes = [(n.lat, n.lon) for n in w.nodes]
        
        if len(nodes) < 2:
            return

        # Check for golf courses
        if 'leisure' in tags and tags['leisure'] == 'golf_course':
            golf_data = {
                'type': 'golf_course',
                'name': tags.get('name', 'Unknown Golf Course'),
                'nodes': nodes,
                'tags': tags
            }
            self.golf_courses.append(golf_data)
            for lat, lon in nodes:
                self.update_bounds(lat, lon)
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
            self.major_roads.append(road_data)
            for lat, lon in nodes:
                self.update_bounds(lat, lon)
            if self.callback:
                self.callback(f"Found road: {road_data['name']}")

class MapViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("OSM Map Viewer")
        self.root.geometry("1000x800")
        
        # Create main container
        main_container = ttk.Frame(root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Create top frame for controls
        control_frame = ttk.Frame(main_container)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Add load button
        self.load_btn = ttk.Button(control_frame, text="Load PBF File", command=self.load_file)
        self.load_btn.pack(side="left", padx=(0, 10))
        
        # Add view map button
        self.map_btn = ttk.Button(control_frame, text="View Map", command=self.show_map)
        self.map_btn.pack(side="left", padx=(0, 10))
        self.map_btn.state(['disabled'])
        
        # Add status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(control_frame, textvariable=self.status_var)
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
    
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def append_text(self, text):
        self.text.insert("end", text + "\n")
        self.text.see("end")
        self.root.update_idletasks()
    
    def load_file(self):
        if self.processing:
            return
        
        filename = filedialog.askopenfilename(
            title="Select PBF File",
            filetypes=[("PBF files", "*.pbf"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        self.text.delete(1.0, "end")
        self.processing = True
        self.load_btn.state(['disabled'])
        self.map_btn.state(['disabled'])
        
        def process_file():
            try:
                self.update_status("Starting file processing...")
                self.append_text(f"Processing file: {filename}")
                
                self.handler = MapHandler(callback=lambda msg: self.root.after(0, self.update_status, msg))
                
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
        if self.handler and (self.handler.cities or self.handler.golf_courses or self.handler.major_roads):
            self.map_btn.state(['!disabled'])
        self.update_status("Ready")
    
    def display_results(self):
        if not self.handler:
            return
            
        # Display counts
        self.append_text("\nData Summary:")
        self.append_text(f"Cities/Towns found: {len(self.handler.cities)}")
        self.append_text(f"Golf Courses found: {len(self.handler.golf_courses)}")
        self.append_text(f"Major Roads found: {len(self.handler.major_roads)}")
        
        # Display cities
        if self.handler.cities:
            self.append_text("\nCities/Towns:")
            for city in self.handler.cities:
                self.append_text(f"- {city['name']} (Population: {city['population']})")
        
        # Display golf courses
        if self.handler.golf_courses:
            self.append_text("\nGolf Courses:")
            for course in self.handler.golf_courses:
                self.append_text(f"- {course['name']}")
        
        # Display some major roads
        if self.handler.major_roads:
            self.append_text("\nSample Major Roads:")
            road_types = defaultdict(int)
            for road in self.handler.major_roads:
                road_types[road['highway_type']] += 1
            
            self.append_text("\nRoad Types Summary:")
            for road_type, count in road_types.items():
                self.append_text(f"- {road_type}: {count} roads")
    
    def show_map(self):
        if not self.handler:
            return
            
        # Calculate map center
        center_lat = (self.handler.bounds['min_lat'] + self.handler.bounds['max_lat']) / 2
        center_lon = (self.handler.bounds['min_lon'] + self.handler.bounds['max_lon']) / 2
        
        # Create map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
        
        # Add cities
        city_group = folium.FeatureGroup(name="Cities/Towns")
        for city in self.handler.cities:
            folium.CircleMarker(
                location=[city['lat'], city['lon']],
                radius=8,
                popup=f"{city['name']} (Pop: {city['population']})",
                color='red',
                fill=True
            ).add_to(city_group)
        city_group.add_to(m)
        
        # Add golf courses
        golf_group = folium.FeatureGroup(name="Golf Courses")
        for course in self.handler.golf_courses:
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
        
        for road in self.handler.major_roads:
            road_type = road['highway_type']
            color = road_colors.get(road_type, 'gray')
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
    app = MapViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
