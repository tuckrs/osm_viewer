import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import osmium
import json
from collections import defaultdict
import threading
import os

class ProgressHandler(osmium.SimpleHandler):
    def __init__(self, progress_var, status_var):
        super(ProgressHandler, self).__init__()
        self.nodes = []
        self.ways = []
        self.relations = []
        self.node_count = 0
        self.way_count = 0
        self.relation_count = 0
        self.tags_count = defaultdict(int)
        self.progress_var = progress_var
        self.status_var = status_var
        self.processed_bytes = 0
        self.total_bytes = 0
        
    def set_total_bytes(self, total_bytes):
        self.total_bytes = total_bytes
        
    def update_progress(self, location):
        if self.total_bytes > 0:
            progress = min(100, int((location.position * 100) / self.total_bytes))
            self.progress_var.set(progress)
            self.status_var.set(f"Processing... {progress}% complete")

    def node(self, n):
        self.node_count += 1
        self.update_progress(n)
        if len(n.tags) > 0:
            if len(self.nodes) < 1000:  # Limit stored nodes
                self.nodes.append({
                    'id': n.id,
                    'type': 'node',
                    'lat': n.location.lat,
                    'lon': n.location.lon,
                    'tags': dict(n.tags)
                })
            for key in n.tags:
                self.tags_count[f"node.{key}"] += 1

    def way(self, w):
        self.way_count += 1
        self.update_progress(w)
        if len(w.tags) > 0:
            if len(self.ways) < 1000:  # Limit stored ways
                self.ways.append({
                    'id': w.id,
                    'type': 'way',
                    'nodes': [n.ref for n in w.nodes],
                    'tags': dict(w.tags)
                })
            for key in w.tags:
                self.tags_count[f"way.{key}"] += 1

    def relation(self, r):
        self.relation_count += 1
        self.update_progress(r)
        if len(r.tags) > 0:
            if len(self.relations) < 1000:  # Limit stored relations
                self.relations.append({
                    'id': r.id,
                    'type': 'relation',
                    'members': [(m.ref, m.type, m.role) for m in r.members],
                    'tags': dict(r.tags)
                })
            for key in r.tags:
                self.tags_count[f"relation.{key}"] += 1

class OSMViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("OSM PBF Viewer")
        self.root.geometry("800x600")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create buttons frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Create buttons
        ttk.Button(self.button_frame, text="Load PBF File", command=self.load_file).pack(side=tk.LEFT, padx=5)
        
        # Create progress bar
        self.progress_var = tk.IntVar()
        self.progress = ttk.Progressbar(self.button_frame, length=300, mode='determinate', 
                                      variable=self.progress_var)
        self.progress.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.button_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Stats tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statistics")
        
        # Data view tab
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="Data View")
        
        # Create text widgets with scrollbars
        # Stats text widget
        stats_scroll = ttk.Scrollbar(self.stats_frame)
        stats_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.stats_text = tk.Text(self.stats_frame, height=20, width=80, yscrollcommand=stats_scroll.set)
        self.stats_text.grid(row=0, column=0, pady=5)
        stats_scroll.config(command=self.stats_text.yview)
        
        # Data text widget
        data_scroll = ttk.Scrollbar(self.data_frame)
        data_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.data_text = tk.Text(self.data_frame, height=20, width=80, yscrollcommand=data_scroll.set)
        self.data_text.grid(row=0, column=0, pady=5)
        data_scroll.config(command=self.data_text.yview)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        self.stats_frame.columnconfigure(0, weight=1)
        self.data_frame.columnconfigure(0, weight=1)
    
    def load_file(self):
        filename = filedialog.askopenfilename(
            title="Select PBF File",
            filetypes=[("PBF files", "*.pbf"), ("All files", "*.*")]
        )
        if filename:
            self.process_file_async(filename)
    
    def process_file_async(self, filename):
        # Clear previous data
        self.stats_text.delete(1.0, tk.END)
        self.data_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        
        def process():
            try:
                # Create handler with progress tracking
                handler = ProgressHandler(self.progress_var, self.status_var)
                
                # Get file size for progress tracking
                file_size = os.path.getsize(filename)
                handler.set_total_bytes(file_size)
                
                # Process file
                handler.apply_file(filename)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_ui(handler))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self.status_var.set("Ready"))
        
        # Start processing in separate thread
        self.status_var.set("Processing file...")
        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()
    
    def update_ui(self, handler):
        # Display statistics
        stats = f"""File Statistics:
        Total Nodes: {handler.node_count:,}
        Total Ways: {handler.way_count:,}
        Total Relations: {handler.relation_count:,}
        
        Nodes with Tags: {len(handler.nodes):,}
        Ways with Tags: {len(handler.ways):,}
        Relations with Tags: {len(handler.relations):,}
        
        Most Common Tags:
        """
        
        # Sort tags by frequency
        sorted_tags = sorted(handler.tags_count.items(), key=lambda x: x[1], reverse=True)
        for tag, count in sorted_tags[:20]:  # Show top 20 tags
            stats += f"{tag}: {count:,}\n"
        
        self.stats_text.insert(tk.END, stats)
        
        # Display sample data
        data_sample = "Sample Data (showing up to 5 items of each type):\n\n"
        if handler.nodes:
            data_sample += "Sample Nodes:\n"
            for node in handler.nodes[:5]:
                data_sample += json.dumps(node, indent=2) + "\n\n"
        
        if handler.ways:
            data_sample += "Sample Ways:\n"
            for way in handler.ways[:5]:
                data_sample += json.dumps(way, indent=2) + "\n\n"
        
        self.data_text.insert(tk.END, data_sample)

def main():
    root = tk.Tk()
    app = OSMViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
