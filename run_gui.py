import tkinter as tk
from gui import MapGeneratorGUI

def main():
    root = tk.Tk()
    app = MapGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
