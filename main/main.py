import tkinter as tk
from tkinter import messagebox

class AnnuvinGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Annuvin AI Project")
        
        # --- Config Variables ---
        self.game_mode = tk.StringVar(value="Human vs Computer")
        self.p2_type = tk.StringVar(value="Minimax")
        self.difficulty = tk.IntVar(value=3) # Depth
        
        self.setup_menu()
        self.canvas = tk.Canvas(root, width=600, height=500, bg="white")
        self.canvas.pack(pady=20)
        self.draw_board()

    def setup_menu(self):
        menu_frame = tk.Frame(self.root)
        menu_frame.pack(side="top", fill="x")
        
        tk.Label(menu_frame, text="Mode:").pack(side="left")
        tk.OptionMenu(menu_frame, self.game_mode, "H vs H", "H vs C", "C vs C").pack(side="left")
        
        tk.Label(menu_frame, text=" AI Algo:").pack(side="left")
        tk.OptionMenu(menu_frame, self.p2_type, "Minimax", "MCTS").pack(side="left")
        
        tk.Button(menu_frame, text="New Game", command=self.reset_game).pack(side="right")
        tk.Button(menu_frame, text="Get Hint", command=self.suggest_hint).pack(side="right")

    def draw_board(self):
        self.canvas.delete("all")
        # Logic to draw hexagons based on Axial coordinates
        # (Simplified: Just drawing a placeholder center)
        self.canvas.create_text(300, 250, text="[Hexagonal Grid Renders Here]")

    def reset_game(self):
        messagebox.showinfo("Game", f"Starting {self.game_mode.get()}...")

    def suggest_hint(self):
        # This is where you will call your Minimax with depth 1 or 2
        messagebox.showinfo("Hint", "The AI suggests moving Piece A to Hex B")

if __name__ == "__main__":
    root = tk.Tk()
    app = AnnuvinGUI(root)
    root.mainloop()