import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import osmium
import json
from collections import defaultdict
import threading
import os

class ChunkHandler(osmium.SimpleHandler):
    def __init__(self, callback=None):
        super(ChunkHandler, self).__init__()
        self.callback = callback
        self.reset_counts()
        
    def reset_counts(self):
        self.node_count = 0
        self.way_count = 0
        self.relation_count = 0
        self.tag_stats = defaultdict(int)
        self.sample_nodes = []
        self.sample_ways = []
        self.sample_relations = []
        
    def node(self, n):
        self.node_count += 1
        if len(n.tags) > 0:
            if len(self.sample_nodes) < 5:
                self.sample_nodes.append({
                    'id': n.id,
                    'lat': n.location.lat,
                    'lon': n.location.lon,
                    'tags': dict(n.tags)
                })
            for k, v in n.tags:
                self.tag_stats[f'node.{k}={v}'] += 1
        
        if self.callback and self.node_count % 100000 == 0:
            self.callback(f"Processed {self.node_count:,} nodes")

    def way(self, w):
        self.way_count += 1
        if len(w.tags) > 0:
            if len(self.sample_ways) < 5:
                self.sample_ways.append({
                    'id': w.id,
                    'nodes': [n.ref for n in w.nodes],
                    'tags': dict(w.tags)
                })
            for k, v in w.tags:
                self.tag_stats[f'way.{k}={v}'] += 1
        
        if self.callback and self.way_count % 10000 == 0:
            self.callback(f"Processed {self.way_count:,} ways")

    def relation(self, r):
        self.relation_count += 1
        if len(r.tags) > 0:
            if len(self.sample_relations) < 5:
                self.sample_relations.append({
                    'id': r.id,
                    'members': [(m.ref, m.type, m.role) for m in r.members],
                    'tags': dict(r.tags)
                })
            for k, v in r.tags:
                self.tag_stats[f'relation.{k}={v}'] += 1
        
        if self.callback and self.relation_count % 1000 == 0:
            self.callback(f"Processed {self.relation_count:,} relations")

class SimpleOSMViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple OSM PBF Viewer")
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
        
        def process_file():
            try:
                self.update_status("Starting file processing...")
                self.append_text(f"Processing file: {filename}")
                
                handler = ChunkHandler(callback=lambda msg: self.root.after(0, self.update_status, msg))
                
                # Process the file
                handler.apply_file(filename)
                
                # Display results
                self.root.after(0, self.display_results, handler)
                
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
        self.update_status("Ready")
    
    def display_results(self, handler):
        # Display counts
        self.append_text("\nFile Statistics:")
        self.append_text(f"Total Nodes: {handler.node_count:,}")
        self.append_text(f"Total Ways: {handler.way_count:,}")
        self.append_text(f"Total Relations: {handler.relation_count:,}")
        
        # Display top tags
        self.append_text("\nMost Common Tags (top 20):")
        sorted_tags = sorted(handler.tag_stats.items(), key=lambda x: x[1], reverse=True)[:20]
        for tag, count in sorted_tags:
            self.append_text(f"{tag}: {count:,}")
        
        # Display samples
        if handler.sample_nodes:
            self.append_text("\nSample Nodes:")
            for node in handler.sample_nodes:
                self.append_text(json.dumps(node, indent=2))
        
        if handler.sample_ways:
            self.append_text("\nSample Ways:")
            for way in handler.sample_ways:
                self.append_text(json.dumps(way, indent=2))
        
        if handler.sample_relations:
            self.append_text("\nSample Relations:")
            for relation in handler.sample_relations:
                self.append_text(json.dumps(relation, indent=2))

def main():
    root = tk.Tk()
    app = SimpleOSMViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
