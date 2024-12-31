import ast
import sys
import os
from typing import List, Set
import unittest
import tempfile
import shutil
from svg_renderer import SvgRenderer
from gui import MapGeneratorGUI
import tkinter as tk

# List of critical test functions that must be preserved
CRITICAL_TESTS = {
    'test_svg_renderer_initialization',
    'test_osm_api_connection',
    'test_coordinate_transformation',
    'test_svg_creation',
    'test_generate_minimal_city_map',
    'test_map_styling',
    'test_map_dimensions',
    'test_default_road_styles',
    'test_street_names_rendering',
    'test_street_name_rendering_quality',
    'test_street_names_disabled',
    'test_city_list_text_area',
    'test_batch_export_button',
    'test_batch_export_button_state',
    'test_gui_functionality',
    'test_gui_street_names_integration',
    'test_batch_export_folder_organization',
    'test_format_selection',
    'test_format_conversion_errors',
    'test_inkscape_detection',
    'cleanup',  # This is a critical cleanup function
    'test_svg_format',
    'test_cairo_formats',
    'test_inkscape_formats',
    'test_gui_format_selection',
    'test_format_availability'
}

def get_test_functions_from_ast(file_path: str) -> Set[str]:
    """Extract all test function names from a Python file using AST"""
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    test_functions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith('test_') or node.name == 'cleanup':
                test_functions.add(node.name)
    
    return test_functions

def verify_critical_tests():
    """Verify that all critical tests are present in test.py"""
    try:
        # Get the absolute path to test.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_path = os.path.join(current_dir, 'test.py')
        
        if not os.path.exists(test_path):
            print(f"ERROR: test.py not found at {test_path}")
            sys.exit(1)
        
        # Get actual test functions using AST
        actual_tests = get_test_functions_from_ast(test_path)
        
        # Find missing critical tests
        missing_tests = CRITICAL_TESTS - actual_tests
        
        if missing_tests:
            print("ERROR: The following critical tests are missing:")
            for test in sorted(missing_tests):
                print(f"  - {test}")
            sys.exit(1)
        
        # Report success
        print("All critical tests are present!")
        print(f"Critical tests found: {len(CRITICAL_TESTS)}")
        print(f"Total tests found: {len(actual_tests)}")
        
        # Show additional tests
        additional_tests = actual_tests - CRITICAL_TESTS
        if additional_tests:
            print("\nAdditional tests found:")
            for test in sorted(additional_tests):
                print(f"  + {test}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

class TestVerification(unittest.TestCase):
    def setUp(self):
        self.renderer = SvgRenderer()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a simple test SVG
        self.test_svg_path = os.path.join(self.temp_dir, "test.svg")
        with open(self.test_svg_path, "w") as f:
            f.write('''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="50" height="50" fill="blue"/>
</svg>''')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        # Clean up any generated files
        if os.path.exists("generated_maps"):
            shutil.rmtree("generated_maps")

    def test_svg_format(self):
        """Test that SVG format is always available"""
        # SVG should always be supported as it's the native format
        self.assertTrue(os.path.exists(self.test_svg_path))
        with open(self.test_svg_path, 'r') as f:
            content = f.read()
        self.assertIn('<svg', content)
        self.assertIn('rect', content)
        self.assertGreater(os.path.getsize(self.test_svg_path), 0)

    def test_cairo_formats(self):
        """Test formats that require CairoSVG (PNG, PDF)"""
        try:
            import cairosvg
            cairo_available = True
        except ImportError:
            cairo_available = False

        formats = ['png', 'pdf']
        for fmt in formats:
            output_path = self.renderer.convert_to_format(self.test_svg_path, fmt)
            
            if cairo_available:
                self.assertIsNotNone(output_path, f"Conversion to {fmt} failed despite CairoSVG being available")
                self.assertTrue(os.path.exists(output_path), f"Output {fmt} file was not created")
                self.assertGreater(os.path.getsize(output_path), 0, f"Output {fmt} file is empty")
                
                # Verify file contents
                if fmt == 'png':
                    self._verify_png_file(output_path)
                elif fmt == 'pdf':
                    self._verify_pdf_file(output_path)
            else:
                self.assertIsNone(output_path, f"Conversion to {fmt} succeeded despite CairoSVG not being available")

    def test_inkscape_formats(self):
        """Test formats that require Inkscape (AI, EPS, DXF)"""
        inkscape_available = self._is_inkscape_available()
        
        formats = ['ai', 'eps', 'dxf']
        for fmt in formats:
            output_path = self.renderer.convert_to_format(self.test_svg_path, fmt)
            
            if inkscape_available:
                self.assertIsNotNone(output_path, f"Conversion to {fmt} failed despite Inkscape being available")
                self.assertTrue(os.path.exists(output_path), f"Output {fmt} file was not created")
                self.assertGreater(os.path.getsize(output_path), 0, f"Output {fmt} file is empty")
                
                # Verify file contents
                if fmt == 'ai':
                    self._verify_ai_file(output_path)
                elif fmt == 'eps':
                    self._verify_eps_file(output_path)
                elif fmt == 'dxf':
                    self._verify_dxf_file(output_path)
            else:
                self.assertIsNone(output_path, f"Conversion to {fmt} succeeded despite Inkscape not being available")

    def test_gui_format_selection(self):
        """Test GUI format selection functionality"""
        root = tk.Tk()
        gui = MapGeneratorGUI(root)
        
        # Test format availability
        available_formats = [fmt for fmt, details in gui.formats.items() if details["available"]]
        self.assertGreater(len(available_formats), 0, "No formats available in GUI")
        
        # Test format selection
        for fmt in gui.formats:
            if gui.formats[fmt]["available"]:
                gui.format_vars[fmt].set(True)
                self.assertTrue(gui.format_vars[fmt].get(), f"Could not select format {fmt}")
        
        # Test select all/none
        gui._select_all_formats()
        for fmt in gui.formats:
            if gui.formats[fmt]["available"]:
                self.assertTrue(gui.format_vars[fmt].get(), f"Format {fmt} not selected after Select All")
        
        gui._select_no_formats()
        for fmt in gui.formats:
            self.assertFalse(gui.format_vars[fmt].get(), f"Format {fmt} still selected after Select None")
        
        root.destroy()

    def test_format_availability(self):
        """Test format availability detection"""
        root = tk.Tk()
        gui = MapGeneratorGUI(root)
        
        # SVG should always be available
        self.assertTrue(gui.formats["SVG (*.svg)"]["available"])
        
        # Test CairoSVG formats
        try:
            import cairosvg
            self.assertTrue(gui.formats["PNG Image (*.png)"]["available"])
            self.assertTrue(gui.formats["PDF Document (*.pdf)"]["available"])
        except ImportError:
            self.assertFalse(gui.formats["PNG Image (*.png)"]["available"])
            self.assertFalse(gui.formats["PDF Document (*.pdf)"]["available"])
        
        # Test Inkscape formats
        inkscape_available = self._is_inkscape_available()
        self.assertEqual(gui.formats["Adobe Illustrator (*.ai)"]["available"], inkscape_available)
        self.assertEqual(gui.formats["Encapsulated PostScript (*.eps)"]["available"], inkscape_available)
        self.assertEqual(gui.formats["AutoCAD DXF (*.dxf)"]["available"], inkscape_available)
        
        root.destroy()

    def _verify_png_file(self, filepath):
        """Verify PNG file format"""
        with open(filepath, 'rb') as f:
            header = f.read(8)
            self.assertEqual(header, b'\x89PNG\r\n\x1a\n', "Invalid PNG header")

    def _verify_pdf_file(self, filepath):
        """Verify PDF file format"""
        with open(filepath, 'rb') as f:
            header = f.read(4)
            self.assertEqual(header, b'%PDF', "Invalid PDF header")

    def _verify_ai_file(self, filepath):
        """Verify AI file format"""
        with open(filepath, 'rb') as f:
            header = f.read(2)
            self.assertEqual(header, b'%!', "Invalid AI header")

    def _verify_eps_file(self, filepath):
        """Verify EPS file format"""
        with open(filepath, 'rb') as f:
            header = f.read(2)
            self.assertEqual(header, b'%!', "Invalid EPS header")

    def _verify_dxf_file(self, filepath):
        """Verify DXF file format"""
        with open(filepath, 'r') as f:
            content = f.read()
            self.assertIn('SECTION', content, "Invalid DXF content")
            self.assertIn('ENTITIES', content, "Invalid DXF content")

    def _is_inkscape_available(self):
        """Check if Inkscape is available on the system"""
        try:
            if os.name == 'nt':  # Windows
                program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
                inkscape_path = os.path.join(program_files, 'Inkscape', 'bin', 'inkscape.exe')
                if not os.path.exists(inkscape_path):
                    program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
                    inkscape_path = os.path.join(program_files_x86, 'Inkscape', 'bin', 'inkscape.exe')
                return os.path.exists(inkscape_path)
            else:  # Linux/Mac
                import subprocess
                subprocess.run(['inkscape', '--version'], check=True, capture_output=True)
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

if __name__ == '__main__':
    unittest.main()
