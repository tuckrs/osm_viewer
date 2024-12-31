from flask import Flask, render_template_string, request
import osmium
import folium
from shapely.geometry import Point, LineString

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>OSM Viewer</title>
    <style>
        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>OpenStreetMap PBF Viewer</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pbf">
            <input type="submit" value="Upload">
        </form>
        {% if map_html %}
            {{ map_html | safe }}
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file uploaded'
        
        file = request.files['file']
        if file.filename == '':
            return 'No file selected'
        
        if file and file.filename.endswith('.pbf'):
            # Save the uploaded file
            file.save('temp.osm.pbf')
            
            # Create a map centered on a default location
            m = folium.Map(location=[30.2672, -97.7431], zoom_start=12)
            
            # Return the template with the map
            return render_template_string(HTML_TEMPLATE, 
                                       map_html=m._repr_html_())
    
    return render_template_string(HTML_TEMPLATE, map_html=None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8550, debug=True)
