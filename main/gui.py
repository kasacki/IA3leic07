import tkinter as tk
import math
from logic import AnnuvinGame
from tkinter import messagebox
import ast

class AnnuvinGUI:
    def __init__(self, root):
        self.game = AnnuvinGame()
        self.root = root
        self.size = 35  
        self.selected_hex = None

        # --- Menu Bar ---
        self.menubar = tk.Menu(root)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="New Game", command=self.reset_game)
        self.filemenu.add_command(label="Save Game", command=self.save_game)
        self.filemenu.add_command(label="Load Game", command=self.load_game)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=root.quit)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        
        self.menubar.add_command(label="Get Hint", command=self.suggest_hint)
        root.config(menu=self.menubar)

        # --- UI Styling (Tan Colors) ---
        root.configure(bg="#D2B48C")
        p_name = "Black" if self.game.current_player == 1 else "White"
        self.status_label = tk.Label(root, text=f"{p_name}'s Turn (Move: 1)", 
                                     font=("Arial", 12), bg="#D2B48C")
        self.status_label.pack(fill="x")

        self.canvas = tk.Canvas(root, width=600, height=500, bg="#D2B48C", highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)
        
        self.draw_board()

    def hex_to_pixel(self, q, r):
        # Pointy-Topped Math
        x = self.size * (math.sqrt(3) * q + math.sqrt(3)/2 * r) + 300
        y = self.size * (3/2 * r) + 250
        return x, y

    def pixel_to_hex(self, x, y):
        x, y = x - 300, y - 250
        q = (math.sqrt(3)/3 * x - 1/3 * y) / self.size
        r = (2/3 * y) / self.size
        rq, rr = round(q), round(r)
        rs = round(-q - r)
        if abs(rq - q) > abs(rr - r) and abs(rq - q) > abs(rs - (-q-r)):
            rq = -rr - rs
        elif abs(rr - r) > abs(rs - (-q-r)):
            rr = -rq - rs
        return int(rq), int(rr)

    def draw_hexagon(self, x, y, fill):
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30) 
            points.extend([x + self.size * math.cos(angle), y + self.size * math.sin(angle)])
        self.canvas.create_polygon(points, fill=fill, outline="black")

    def draw_board(self):
        self.canvas.delete("all")
        for q in range(-3, 4):
            for r in range(-3, 4):
                if abs(q) <= 3 and abs(r) <= 3 and abs(q + r) <= 3:
                    x, y = self.hex_to_pixel(q, r)
                    color = "#F0E68C" if (q, r) == self.selected_hex else "white"
                    self.draw_hexagon(x, y, color)
                    
                    if (q, r) in self.game.pieces[1]: # Black
                        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="black", outline="black")
                    elif (q, r) in self.game.pieces[2]: # White
                        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="white", outline="grey")

    def handle_click(self, event):
        coords = self.pixel_to_hex(event.x, event.y)
        if self.selected_hex is None:
            if coords in self.game.pieces[self.game.current_player]:
                self.selected_hex = coords
        else:
            if self.game.is_valid_move(self.selected_hex, coords):
                self.game.execute_move(self.selected_hex, coords)
                self.draw_board()
                self.root.update_idletasks()
                
                winner = self.game.check_winner()
                if winner:
                    p_name = "Black" if winner == 1 else "White"
                    messagebox.showinfo("Game Over", f"Player {p_name} has won!")
                else:
                    p_name = "Black" if self.game.current_player == 1 else "White"
                    dist = self.game.get_max_distance(self.game.current_player)
                    self.status_label.config(text=f"{p_name}'s Turn (Move: {dist})")
            self.selected_hex = None
        self.draw_board()

    def reset_game(self):
        self.game = AnnuvinGame()
        self.selected_hex = None
        self.status_label.config(text="Black's Turn (Move: 1)")
        self.draw_board()

    def save_game(self):
        with open("savegame.txt", "w") as f:
            f.write(f"{self.game.current_player}\n")
            f.write(f"{self.game.pieces[1]}\n")
            f.write(f"{self.game.pieces[2]}\n")
        messagebox.showinfo("Save", "Game state saved to savegame.txt")

    def load_game(self):
        try:
            with open("savegame.txt", "r") as f:
                lines = f.readlines()
                self.game.current_player = int(lines[0].strip())
                self.game.pieces[1] = ast.literal_eval(lines[1].strip())
                self.game.pieces[2] = ast.literal_eval(lines[2].strip())
            self.draw_board()
            messagebox.showinfo("Load", "Game loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load: {e}")

    def suggest_hint(self):
        cp = self.game.current_player
        opp = 2 if cp == 1 else 1
        for start in self.game.pieces[cp]:
            for q in range(-3, 4):
                for r in range(-3, 4):
                    target = (q, r)
                    if abs(q+r) <= 3 and self.game.is_valid_move(start, target):
                        if target in self.game.pieces[opp]:
                            messagebox.showinfo("Hint", f"Capture at {target}!")
                            return
        messagebox.showinfo("Hint", "Move any piece forward!")