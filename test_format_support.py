import unittest
import os
import subprocess
from svg_renderer import SvgRenderer
from gui import MapGeneratorGUI
import tempfile
import shutil
import tkinter as tk
import struct

class TestFormatSupport(unittest.TestCase):
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
                subprocess.run(['inkscape', '--version'], check=True, capture_output=True)
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

if __name__ == '__main__':
    unittest.main()
