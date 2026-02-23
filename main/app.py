import tkinter as tk
from gui import AnnuvinGUI

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Annuvin AI Project")
    app = AnnuvinGUI(root)
    root.mainloop()