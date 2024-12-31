import streamlit as st
from svg_renderer import SvgRenderer
from geopy.geocoders import Nominatim
import time
import io
import base64

def get_svg_download_link(svg_path, filename):
    """Generate a download link for the SVG file"""
    with open(svg_path, 'r') as f:
        svg_content = f.read()
    b64 = base64.b64encode(svg_content.encode()).decode()
    return f'<a href="data:image/svg+xml;base64,{b64}" download="{filename}">Download SVG File</a>'

def main():
    st.set_page_config(
        page_title="City Map Art Generator",
        page_icon="🗺️",
        layout="wide"
    )

    st.title("City Map Art Generator")
    st.markdown("""
    Create beautiful, minimalist city map art suitable for printing and framing.
    """)

    # Create two columns for input and preview
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Map Settings")
        
        # City input
        city = st.text_input(
            "City Name",
            placeholder="e.g., Austin, TX",
            help="Enter the name of the city you want to create a map for"
        )

        # Radius input
        radius = st.slider(
            "Radius (km)",
            min_value=0.5,
            max_value=10.0,
            value=1.0,
            step=0.5,
            help="Choose the radius around the city center (1-2km for downtown, 5-10km for wider area)"
        )

        # Style options
        st.subheader("Style Options")
        style_preset = st.selectbox(
            "Color Scheme",
            ["Minimalist", "High Contrast", "Blueprint"],
            help="Choose the visual style for your map"
        )

        # Paper size options
        paper_sizes = {
            "8x10 inches": (8, 10),
            "11x14 inches": (11, 14),
            "16x20 inches": (16, 20),
            "18x24 inches": (18, 24),
            "24x36 inches": (24, 36),
            "A4": (8.27, 11.69),
            "A3": (11.69, 16.54),
        }
        
        size = st.selectbox(
            "Paper Size",
            list(paper_sizes.keys()),
            help="Choose the output dimensions"
        )

        # Generate button
        generate = st.button("Generate Map", type="primary")

    with col2:
        st.subheader("Preview")
        preview_container = st.empty()

        if generate and city:
            try:
                with st.spinner("Generating your map..."):
                    # Initialize renderer with selected paper size
                    width, height = paper_sizes[size]
                    renderer = SvgRenderer(width_inches=width, height_inches=height)

                    # Get city location
                    geolocator = Nominatim(user_agent="city_map_art_generator")
                    location = geolocator.geocode(city)

                    if location:
                        # Calculate bounds
                        lat_offset = radius / 111.0
                        lon_offset = radius / (111.0 * abs(np.cos(np.radians(location.latitude))))
                        
                        bounds = {
                            'min_lat': location.latitude - lat_offset,
                            'max_lat': location.latitude + lat_offset,
                            'min_lon': location.longitude - lon_offset,
                            'max_lon': location.longitude + lon_offset
                        }

                        # Generate map
                        output_file = f"{city.lower().replace(' ', '_')}.svg"
                        svg_path = renderer.create_minimal_map(city, bounds, output_file)

                        # Display preview
                        with open(svg_path, 'r') as f:
                            svg_content = f.read()
                            preview_container.markdown(svg_content, unsafe_allow_html=True)

                        # Create download link
                        st.markdown(
                            get_svg_download_link(svg_path, output_file),
                            unsafe_allow_html=True
                        )

                        # Display map details
                        st.success(f"""
                        Map generated successfully!
                        - Center: {location.latitude:.4f}°N, {location.longitude:.4f}°E
                        - Radius: {radius}km
                        - Size: {width}x{height} inches
                        """)

                    else:
                        st.error(f"Could not find location: {city}")

            except Exception as e:
                st.error(f"Error generating map: {str(e)}")

if __name__ == "__main__":
    main()
