import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import osmium
import json
import threading
import os
import folium
import webbrowser
import tempfile

class CityHandler(osmium.SimpleHandler):
    def __init__(self, target_city, callback=None):
        super(CityHandler, self).__init__()
        self.target_city = target_city.lower()
        self.callback = callback
        self.reset_data()
        
    def reset_data(self):
        self.city_found = False
        self.city_data = None
        self.nearby_roads = []
        self.nearby_golf_courses = []
        self.search_radius = 0.1  # Approximately 11km
        
    def node(self, n):
        tags = dict(n.tags)
        if not self.city_found and 'place' in tags and tags['place'] in ['city', 'town']:
            name = tags.get('name', '').lower()
            if self.target_city in name:
                self.city_found = True
                self.city_data = {
                    'type': 'city',
                    'name': tags.get('name', 'Unknown'),
                    'lat': n.location.lat,
                    'lon': n.location.lon,
                    'population': tags.get('population', 'Unknown'),
                    'tags': tags
                }
                if self.callback:
                    self.callback(f"Found city: {self.city_data['name']}")

    def way(self, w):
        if not self.city_found:
            return
            
        tags = dict(w.tags)
        nodes = [(n.lat, n.lon) for n in w.nodes]
        
        if len(nodes) < 2:
            return

        # Only process ways near the found city
        if not self._is_near_city(nodes):
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
                self.callback(f"Found nearby golf course: {golf_data['name']}")

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
                self.callback(f"Found nearby road: {road_data['name']}")

    def _is_near_city(self, nodes):
        if not self.city_data:
            return False
        
        city_lat, city_lon = self.city_data['lat'], self.city_data['lon']
        for lat, lon in nodes:
            if (abs(lat - city_lat) <= self.search_radius and 
                abs(lon - city_lon) <= self.search_radius):
                return True
        return False

class CityViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("City Map Viewer")
        self.root.geometry("800x600")
        
        # Create main container
        main_container = ttk.Frame(root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Create input frame
        input_frame = ttk.Frame(main_container)
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # City entry
        ttk.Label(input_frame, text="City name:").pack(side="left", padx=(0, 5))
        self.city_var = tk.StringVar()
        self.city_entry = ttk.Entry(input_frame, textvariable=self.city_var)
        self.city_entry.pack(side="left", padx=(0, 10))
        
        # File button
        self.load_btn = ttk.Button(input_frame, text="Load PBF & Search", command=self.load_file)
        self.load_btn.pack(side="left", padx=(0, 10))
        
        # Map button
        self.map_btn = ttk.Button(input_frame, text="View Map", command=self.show_map)
        self.map_btn.pack(side="left", padx=(0, 10))
        self.map_btn.state(['disabled'])
        
        # Status label
        self.status_var = tk.StringVar(value="Enter a city name and load a PBF file")
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
            
        city_name = self.city_var.get().strip()
        if not city_name:
            messagebox.showwarning("Warning", "Please enter a city name first")
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
                self.update_status(f"Searching for {city_name}...")
                self.append_text(f"Processing file: {filename}")
                
                self.handler = CityHandler(city_name, callback=lambda msg: self.root.after(0, self.update_status, msg))
                
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
        if self.handler and self.handler.city_found:
            self.map_btn.state(['!disabled'])
        self.update_status("Ready")
    
    def display_results(self):
        if not self.handler:
            return
            
        if not self.handler.city_found:
            self.append_text(f"\nCity not found!")
            return
            
        # Display city info
        city = self.handler.city_data
        self.append_text(f"\nFound City: {city['name']}")
        self.append_text(f"Population: {city['population']}")
        self.append_text(f"Location: {city['lat']}, {city['lon']}")
        
        # Display nearby features
        self.append_text(f"\nNearby Features:")
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
        if not self.handler or not self.handler.city_found:
            return
            
        # Create map centered on city
        m = folium.Map(
            location=[self.handler.city_data['lat'], self.handler.city_data['lon']],
            zoom_start=13
        )
        
        # Add city marker
        city_group = folium.FeatureGroup(name="City")
        folium.CircleMarker(
            location=[self.handler.city_data['lat'], self.handler.city_data['lon']],
            radius=8,
            popup=f"{self.handler.city_data['name']} (Pop: {self.handler.city_data['population']})",
            color='red',
            fill=True
        ).add_to(city_group)
        city_group.add_to(m)
        
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
    app = CityViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
