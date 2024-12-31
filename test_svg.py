import svgwrite
import os

def test_svg():
    # Create a simple SVG
    dwg = svgwrite.Drawing('test.svg', size=('100px', '100px'))
    dwg.add(dwg.rect(insert=(0, 0), size=('50px', '50px'), fill='blue'))
    dwg.save()
    
    # Verify file exists and contains SVG content
    assert os.path.exists('test.svg')
    with open('test.svg', 'r') as f:
        content = f.read()
        assert '<svg' in content
        assert '<rect' in content
    
    # Clean up
    os.remove('test.svg')
    print("SVG test passed!")

if __name__ == '__main__':
    test_svg()
