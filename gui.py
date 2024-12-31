import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from svg_renderer import SvgRenderer, CAIRO_AVAILABLE
from geopy.geocoders import Nominatim
import time
import os

class MapGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("City Map Art Generator")
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Initialize variables
        self.city_var = tk.StringVar(value="")
        self.radius_var = tk.DoubleVar(value=0.6)
        self.show_names_var = tk.BooleanVar(value=False)
        self.filename_var = tk.StringVar(value="map")
        self.status_var = tk.StringVar(value="Ready")
        
        # Check format availability
        self.renderer = SvgRenderer()
        self.formats = self._check_format_availability()
        self.format_vars = {fmt: tk.BooleanVar(value=True if fmt == "SVG (*.svg)" else False) 
                          for fmt in self.formats}
        
        # Initialize geocoder
        self.geocoder = Nominatim(user_agent="city_map_art_generator")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Single Map Tab
        single_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(single_frame, text="Single Map")
        
        # Batch Export Tab
        batch_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(batch_frame, text="Batch Export")
        
        # Set up single map frame
        self._setup_single_map_frame(single_frame)
        
        # Set up batch export frame
        self._setup_batch_export_frame(batch_frame)
        
        # Check dependencies and show warnings
        self._check_dependencies()

    def _check_dependencies(self):
        """Check for required dependencies and show warnings if missing"""
        warnings = []
        
        if not CAIRO_AVAILABLE:
            warnings.append("CairoSVG is not available. PNG and PDF export will be disabled.")
        
        try:
            SvgRenderer()._get_inkscape_path()
        except Exception:
            warnings.append("Inkscape is not installed. AI, EPS, and DXF export will be disabled.")
        
        if warnings:
            messagebox.showwarning(
                "Missing Dependencies",
                "\n\n".join(warnings) + "\n\nPlease check requirements.md for installation instructions."
            )

    def _check_format_availability(self):
        """Check which formats are available based on installed dependencies"""
        formats = {"SVG (*.svg)": {"ext": ".svg", "available": True, "reason": "Native format"}}
        
        # Check CairoSVG availability
        try:
            import cairosvg
            formats.update({
                "PNG Image (*.png)": {"ext": ".png", "available": True, "reason": "Using CairoSVG"},
                "PDF Document (*.pdf)": {"ext": ".pdf", "available": True, "reason": "Using CairoSVG"}
            })
        except ImportError:
            formats.update({
                "PNG Image (*.png)": {"ext": ".png", "available": False, "reason": "Requires CairoSVG"},
                "PDF Document (*.pdf)": {"ext": ".pdf", "available": False, "reason": "Requires CairoSVG"}
            })
        
        # Check Inkscape availability
        try:
            if self.renderer._get_inkscape_path():
                formats.update({
                    "Adobe Illustrator (*.ai)": {"ext": ".ai", "available": True, "reason": "Using Inkscape"},
                    "AutoCAD DXF (*.dxf)": {"ext": ".dxf", "available": True, "reason": "Using Inkscape"},
                    "Encapsulated PostScript (*.eps)": {"ext": ".eps", "available": True, "reason": "Using Inkscape"}
                })
        except Exception:
            formats.update({
                "Adobe Illustrator (*.ai)": {"ext": ".ai", "available": False, "reason": "Requires Inkscape"},
                "AutoCAD DXF (*.dxf)": {"ext": ".dxf", "available": False, "reason": "Requires Inkscape"},
                "Encapsulated PostScript (*.eps)": {"ext": ".eps", "available": False, "reason": "Requires Inkscape"}
            })
        
        return formats

    def _show_format_info(self):
        """Show information about available formats and required dependencies"""
        info = "Available Formats:\n\n"
        unavailable = "\nUnavailable Formats:\n\n"
        
        for fmt, details in self.formats.items():
            if details["available"]:
                info += f"✓ {fmt}\n   {details['reason']}\n"
            else:
                unavailable += f"✗ {fmt}\n   {details['reason']}\n"
        
        messagebox.showinfo("Format Information", info + unavailable)

    def _setup_single_map_frame(self, frame):
        """Set up the single map generation frame"""
        # City input
        ttk.Label(frame, text="City Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.city_var, width=40).grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Radius input
        ttk.Label(frame, text="Radius (miles):").grid(row=1, column=0, sticky=tk.W, pady=5)
        radius_spin = ttk.Spinbox(frame, from_=0.3, to=6.2, increment=0.1, textvariable=self.radius_var, width=10)
        radius_spin.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Paper size
        ttk.Label(frame, text="Paper Size:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.sizes = {
            "8x10 inches": (8, 10),
            "11x14 inches": (11, 14),
            "16x20 inches": (16, 20),
            "18x24 inches": (18, 24),
            "24x36 inches": (24, 36),
            "A4": (8.27, 11.69),
            "A3": (11.69, 16.54),
        }
        self.size_var = tk.StringVar(value="11x14 inches")
        size_combo = ttk.Combobox(frame, textvariable=self.size_var, values=list(self.sizes.keys()), state="readonly", width=15)
        size_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Street names option
        ttk.Checkbutton(frame, text="Show Street Names", variable=self.show_names_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Format selection
        self._create_format_frame(frame)
        
        # Output filename (without extension)
        ttk.Label(frame, text="Output Filename:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.filename_var, width=40).grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Generate button
        ttk.Button(frame, text="Generate Map", command=self.generate_map).grid(row=5, column=0, columnspan=3, pady=20)
        
        # Status label
        ttk.Label(frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, pady=5)

    def _create_format_frame(self, parent):
        """Create the format selection frame with checkboxes and info button"""
        format_frame = ttk.LabelFrame(parent, text="Output Formats", padding="5")
        format_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Create a sub-frame for the checkboxes with scrollbar if needed
        checkbox_frame = ttk.Frame(format_frame)
        checkbox_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        # Add checkboxes for each available format
        for i, (fmt, details) in enumerate(self.formats.items()):
            if details["available"]:
                ttk.Checkbutton(checkbox_frame, text=fmt, variable=self.format_vars[fmt]).grid(
                    row=i//2, column=i%2, sticky=tk.W, padx=5, pady=2
                )
        
        # Info button
        info_button = ttk.Button(format_frame, text="ℹ", width=3, command=self._show_format_info)
        info_button.grid(row=0, column=1, padx=5)
        
        # Select All / None buttons
        button_frame = ttk.Frame(format_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="Select All", command=self._select_all_formats).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Select None", command=self._select_no_formats).grid(row=0, column=1, padx=5)
        
        return format_frame
    
    def _select_all_formats(self):
        """Select all available formats"""
        for fmt, details in self.formats.items():
            if details["available"]:
                self.format_vars[fmt].set(True)
    
    def _select_no_formats(self):
        """Deselect all formats"""
        for fmt in self.formats:
            self.format_vars[fmt].set(False)

    def _setup_batch_export_frame(self, frame):
        """Set up the batch export frame"""
        # Instructions
        ttk.Label(frame, text="Enter one city per line:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Text area for cities
        self.cities_text = tk.Text(frame, width=40, height=10)
        self.cities_text.grid(row=1, column=0, columnspan=3, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.cities_text.yview)
        scrollbar.grid(row=1, column=3, sticky=(tk.N, tk.S))
        self.cities_text.configure(yscrollcommand=scrollbar.set)
        
        # Export options frame
        options_frame = ttk.LabelFrame(frame, text="Export Options", padding="5")
        options_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        # Format selection
        self._create_format_frame(options_frame)
        
        # Radius input for batch
        ttk.Label(options_frame, text="Radius (miles):").grid(row=1, column=0, sticky=tk.W, pady=5)
        radius_spin = ttk.Spinbox(options_frame, from_=0.3, to=6.2, increment=0.1, textvariable=self.radius_var, width=10)
        radius_spin.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Street names option for batch
        ttk.Checkbutton(options_frame, text="Show Street Names", variable=self.show_names_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Generate button
        self.batch_button = ttk.Button(frame, text="Generate Maps", command=self.generate_batch_maps)
        self.batch_button.grid(row=3, column=0, columnspan=4, pady=20)
        
        # Status label
        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=4, pady=5)

    def _on_text_change(self, event):
        """Handle text changes in the cities text area"""
        # Reset the modified flag
        self.cities_text.edit_modified(False)
        
        # Enable button if there are cities, disable if empty
        text_content = self.cities_text.get("1.0", tk.END).strip()
        if text_content:
            self.batch_button.state(['!disabled'])  # Enable
        else:
            self.batch_button.state(['disabled'])  # Disable

    def generate_map(self):
        """Generate the map based on current settings"""
        try:
            # Get city and validate
            city = self.city_var.get().strip()
            if not city:
                messagebox.showerror("Error", "Please enter a city name")
                return
            
            # Get location from geocoder
            self.status_var.set("Looking up city location...")
            self.root.update()
            location = self.geocoder.geocode(city)
            if not location:
                messagebox.showerror("Error", "City not found")
                self.status_var.set("Error: City not found")
                return
            
            # Calculate bounding box
            radius = self.radius_var.get()
            lat_offset = (radius * 1.60934) / 111.0  # Convert miles to km, then to degrees
            lon_offset = lat_offset / np.cos(np.radians(location.latitude))
            
            bounds = {
                'min_lat': location.latitude - lat_offset,
                'max_lat': location.latitude + lat_offset,
                'min_lon': location.longitude - lon_offset,
                'max_lon': location.longitude + lon_offset
            }
            
            # Get selected format
            selected_formats = [(fmt, details["ext"]) for fmt, details in self.formats.items() 
                              if details["available"] and self.format_vars[fmt].get()]
            
            if not selected_formats:
                messagebox.showerror("Error", "Please select at least one output format")
                return
            
            # Create output directory if it doesn't exist
            os.makedirs("generated_maps", exist_ok=True)
            
            # Generate map in selected format
            self.status_var.set("Generating map...")
            self.root.update()
            
            # Always generate SVG first
            svg_filename = os.path.join("generated_maps", f"{self.filename_var.get()}.svg")
            renderer = SvgRenderer()
            svg_path = renderer.create_minimal_map(
                city,
                bounds,
                svg_filename,
                show_street_names=bool(self.show_names_var.get())
            )
            
            # Convert to other selected formats
            for format_name, extension in selected_formats:
                if extension != '.svg':  # Skip SVG as it's already generated
                    self.status_var.set(f"Converting to {format_name}...")
                    self.root.update()
                    
                    result = renderer.convert_to_format(svg_path, extension.lstrip("."))
                    if not result:
                        messagebox.showwarning("Warning", f"Failed to convert to {format_name}")
            
            self.status_var.set("Map generated successfully!")
            messagebox.showinfo("Success", f"Map has been generated and saved in the 'generated_maps' folder")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Ready")

    def generate_batch_maps(self):
        """Generate maps for all cities in the batch list"""
        try:
            # Get list of cities
            cities = [city.strip() for city in self.cities_text.get("1.0", tk.END).strip().split('\n') if city.strip()]
            if not cities:
                messagebox.showerror("Error", "No cities entered")
                return
            
            # Get selected formats
            selected_formats = [(fmt, details["ext"]) for fmt, details in self.formats.items() 
                              if details["available"] and self.format_vars[fmt].get()]
            
            if not selected_formats:
                messagebox.showerror("Error", "Please select at least one output format")
                return
            
            # Create main output directory if it doesn't exist
            base_output_dir = os.path.join(os.getcwd(), "generated_maps")
            os.makedirs(base_output_dir, exist_ok=True)
            
            # Disable button during processing
            self.batch_button.state(['disabled'])
            self.status_var.set("Processing cities...")
            self.root.update()
            
            # Process each city
            success_count = 0
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            for i, city in enumerate(cities, 1):
                try:
                    # Update status
                    self.status_var.set(f"Processing {city} ({i}/{len(cities)})...")
                    self.root.update()
                    
                    # Get location from geocoder
                    location = self.geocoder.geocode(city)
                    if not location:
                        messagebox.showwarning("Warning", f"City not found: {city}")
                        continue
                    
                    # Create city-specific directory
                    safe_city_name = city.replace(' ', '_').replace(',', '').replace('/', '_').replace('\\', '_')
                    city_dir = os.path.join(base_output_dir, safe_city_name)
                    os.makedirs(city_dir, exist_ok=True)
                    
                    # Calculate bounding box
                    radius = self.radius_var.get()
                    lat_offset = (radius * 1.60934) / 111.0  # Convert miles to km, then to degrees
                    lon_offset = lat_offset / np.cos(np.radians(location.latitude))
                    
                    bounds = {
                        'min_lat': location.latitude - lat_offset,
                        'max_lat': location.latitude + lat_offset,
                        'min_lon': location.longitude - lon_offset,
                        'max_lon': location.longitude + lon_offset
                    }
                    
                    # Generate maps in all selected formats
                    renderer = SvgRenderer()
                    base_filename = f"{safe_city_name}_{timestamp}"
                    
                    # Always generate SVG first
                    svg_filename = os.path.join(city_dir, f"{base_filename}.svg")
                    svg_path = renderer.create_minimal_map(
                        city,
                        bounds,
                        svg_filename,
                        show_street_names=bool(self.show_names_var.get())
                    )
                    
                    # Convert to other selected formats
                    for format_name, extension in selected_formats:
                        if extension != '.svg':  # Skip SVG as it's already generated
                            self.status_var.set(f"Converting {city} to {format_name}...")
                            self.root.update()
                            
                            result = renderer.convert_to_format(svg_path, extension.lstrip("."))
                            if not result:
                                messagebox.showwarning("Warning", f"Failed to convert {city} to {format_name}")
                    
                    success_count += 1
                    
                    # Brief pause to avoid overwhelming the geocoding service
                    time.sleep(1)
                    
                except Exception as e:
                    messagebox.showwarning("Warning", f"Error processing {city}: {str(e)}")
            
            # Re-enable button and update status
            self.batch_button.state(['!disabled'])
            if success_count > 0:
                self.status_var.set(f"Successfully generated {success_count} map(s) in 'generated_maps' folder")
                messagebox.showinfo("Success", 
                                  f"Successfully generated {success_count} map(s).\n"
                                  f"Each city has its own folder in 'generated_maps' with the selected formats.")
            else:
                self.status_var.set("No maps were generated")
                messagebox.showerror("Error", "No maps were generated")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error generating maps")
            self.batch_button.state(['!disabled'])

def main():
    root = tk.Tk()
    app = MapGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
