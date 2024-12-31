import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import json
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import svgwrite
import tempfile
import webbrowser
import os
from datetime import datetime

class MapMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("SVG Map Maker")
        self.root.geometry("1000x800")
        
        # Initialize geocoder
        self.geolocator = Nominatim(user_agent="svg_map_maker")
        
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
        self.radius_var = tk.StringVar(value="5")
        self.radius_entry = ttk.Entry(input_frame, textvariable=self.radius_var, width=5)
        self.radius_entry.pack(side="left", padx=(0, 10))
        
        # Style options
        self.style_var = tk.StringVar(value="minimal")
        ttk.Label(input_frame, text="Style:").pack(side="left", padx=(0, 5))
        style_combo = ttk.Combobox(input_frame, textvariable=self.style_var, width=15)
        style_combo['values'] = ('minimal', 'detailed', 'artistic')
        style_combo.pack(side="left", padx=(0, 10))
        
        # Generate button
        self.generate_btn = ttk.Button(input_frame, text="Generate SVG", command=self.generate_map)
        self.generate_btn.pack(side="left", padx=(0, 10))
        
        # Preview button
        self.preview_btn = ttk.Button(input_frame, text="Preview", command=self.preview_map)
        self.preview_btn.pack(side="left", padx=(0, 10))
        self.preview_btn.state(['disabled'])
        
        # Status label
        self.status_var = tk.StringVar(value="Enter a location to generate an SVG map")
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
        self.current_svg = None
        self.map_data = None
        self.location_info = None
    
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def append_text(self, text):
        self.text.insert("end", text + "\n")
        self.text.see("end")
        self.root.update_idletasks()
    
    def geocode_location(self, location):
        try:
            location_with_country = f"{location}, United States"
            result = self.geolocator.geocode(location_with_country)
            if result is None:
                result = self.geolocator.geocode(location)
            return result
        except GeocoderTimedOut:
            time.sleep(1)
            return self.geocode_location(location)
    
    def get_map_data(self, lat, lon, radius_km):
        # Convert radius to meters
        radius_m = radius_km * 1000
        
        # Overpass API query
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Query for roads, buildings, water features, and parks
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential)$"]
            (around:{radius_m},{lat},{lon});
          way["building"]
            (around:{radius_m},{lat},{lon});
          way["natural"="water"]
            (around:{radius_m},{lat},{lon});
          way["leisure"="park"]
            (around:{radius_m},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
        
        response = requests.post(overpass_url, data={"data": query})
        return response.json()
    
    def create_svg(self, style="minimal"):
        if not self.map_data or not self.location_info:
            return None
            
        # Create SVG with a good size for print
        dwg = svgwrite.Drawing(size=("11in", "14in"), profile='full')
        
        # Add metadata
        dwg.add(dwg.desc(f"Map of {self.location_info.address}"))
        dwg.add(dwg.metadata("""
            <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                     xmlns:dc="http://purl.org/dc/elements/1.1/">
                <rdf:Description>
                    <dc:creator>SVG Map Maker</dc:creator>
                    <dc:date>{datetime.now().isoformat()}</dc:date>
                    <dc:rights>Map data © OpenStreetMap contributors</dc:rights>
                </rdf:Description>
            </rdf:RDF>
        """))
        
        # Style definitions based on selected style
        styles = {
            'minimal': {
                'road': {'stroke': '#333333', 'stroke-width': 1},
                'building': {'fill': '#CCCCCC', 'stroke': 'none'},
                'water': {'fill': '#A5BFDD', 'stroke': 'none'},
                'park': {'fill': '#B8D6B8', 'stroke': 'none'}
            },
            'detailed': {
                'road': {'stroke': '#000000', 'stroke-width': 1.5},
                'building': {'fill': '#BC9B7A', 'stroke': '#8B7355'},
                'water': {'fill': '#A5BFDD', 'stroke': '#7FA1C7'},
                'park': {'fill': '#B8D6B8', 'stroke': '#98B698'}
            },
            'artistic': {
                'road': {'stroke': '#2F4F4F', 'stroke-width': 2},
                'building': {'fill': '#DEB887', 'stroke': '#8B7355'},
                'water': {'fill': '#B0E0E6', 'stroke': '#87CEEB'},
                'park': {'fill': '#90EE90', 'stroke': '#228B22'}
            }
        }
        
        current_style = styles[style]
        
        # Process and add elements
        # TODO: Transform coordinates and add SVG elements
        # This is where we'll add the actual map rendering code
        
        return dwg
    
    def generate_map(self):
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
        
        self.processing = True
        self.generate_btn.state(['disabled'])
        self.preview_btn.state(['disabled'])
        self.text.delete(1.0, "end")
        
        try:
            # Get coordinates
            self.update_status("Looking up location coordinates...")
            self.location_info = self.geocode_location(location)
            if not self.location_info:
                raise Exception(f"Could not find coordinates for '{location}'")
                
            self.append_text(f"Found location: {self.location_info.address}")
            self.append_text(f"Coordinates: {self.location_info.latitude}, {self.location_info.longitude}")
            
            # Get map data
            self.update_status("Fetching map data...")
            self.map_data = self.get_map_data(
                self.location_info.latitude,
                self.location_info.longitude,
                radius
            )
            
            # Create SVG
            self.update_status("Generating SVG...")
            self.current_svg = self.create_svg(self.style_var.get())
            
            # Save SVG
            filename = f"map_{location.replace(' ', '_')}_{self.style_var.get()}.svg"
            self.current_svg.saveas(filename)
            
            self.append_text(f"\nSVG map saved as: {filename}")
            self.preview_btn.state(['!disabled'])
            self.update_status("Ready")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.update_status("Error occurred")
        finally:
            self.processing = False
            self.generate_btn.state(['!disabled'])
    
    def preview_map(self):
        if not self.current_svg:
            return
            
        # Save to temporary file and open in browser
        with tempfile.NamedTemporaryFile(delete=False, suffix='.svg') as tmp:
            self.current_svg.save(tmp.name)
            webbrowser.open('file://' + tmp.name)

def main():
    root = tk.Tk()
    app = MapMaker(root)
    root.mainloop()

if __name__ == "__main__":
    main()
