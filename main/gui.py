from tkinter import messagebox
import tkinter as tk
import math
from logic import AnnuvinGame

class AnnuvinGUI:
    def __init__(self, root):
        self.game = AnnuvinGame()
        self.root = root
        self.size = 35  # Size of one hex side
        self.selected_hex = None

        # UI Elements
        self.status_label = tk.Label(root, text="White's Turn (Move distance: 1)", font=("Arial", 12))
        self.status_label.pack()

        self.canvas = tk.Canvas(root, width=600, height=500, bg="white")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)
        
        self.draw_board()

    def hex_to_pixel(self, q, r):
        # Math for Pointy-Topped hexagons
        x = self.size * (math.sqrt(3) * q + math.sqrt(3)/2 * r) + 300
        y = self.size * (3/2 * r) + 250
        return x, y

    def pixel_to_hex(self, x, y):
        x, y = x - 300, y - 250
        q = (math.sqrt(3)/3 * x - 1/3 * y) / self.size
        r = (2/3 * y) / self.size
        
        # Rounding to nearest hex (Axial)
        rq, rr = round(q), round(r)
        rs = round(-q - r)
        if abs(rq - q) > abs(rr - r) and abs(rq - q) > abs(rs - (-q-r)):
            rq = -rr - rs
        elif abs(rr - r) > abs(rs - (-q-r)):
            rr = -rq - rs
        return int(rq), int(rr)

    def draw_board(self):
        self.canvas.delete("all")
        # Draw the empty grid
        for q in range(-3, 4):
            for r in range(-3, 4):
                if abs(q) <= 3 and abs(r) <= 3 and abs(q + r) <= 3:
                    x, y = self.hex_to_pixel(q, r)
                    color = "yellow" if (q, r) == self.selected_hex else "white"
                    self.draw_hexagon(x, y, color)
                    
                    # Draw pieces
                    if (q, r) in self.game.pieces[1]:
                        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="blue") # Player 1
                    elif (q, r) in self.game.pieces[2]:
                        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="red")  # Player 2

    def draw_hexagon(self, x, y, fill):
        points = []
        for i in range(6):
            # 30 degree offset for Pointy-Top
            angle = math.radians(60 * i - 30) 
            points.extend([x + self.size * math.cos(angle), y + self.size * math.sin(angle)])
        self.canvas.create_polygon(points, fill=fill, outline="black")
        
    def handle_click(self, event):
        coords = self.pixel_to_hex(event.x, event.y)
        
        # 1. Selection Phase
        if self.selected_hex is None:
            # Check if the clicked hex actually contains a piece belonging to current_player
            if coords in self.game.pieces[self.game.current_player]:
                self.selected_hex = coords
                print(f"Selected YOUR piece at {coords}")
            else:
                print(f"Empty hex or enemy piece at {coords} - ignoring.")
        
        # 2. Movement Phase
        else:
            # If you click the SAME piece again, deselect it (cancel move)
            if coords == self.selected_hex:
                self.selected_hex = None
                print("Selection cancelled.")
            # Try to move
            elif self.game.is_valid_move(self.selected_hex, coords):
                print(f"Moving from {self.selected_hex} to {coords}")
                self.game.execute_move(self.selected_hex, coords)
                
                # 1. Redraw the board immediately
                self.draw_board() 
                # 2. Force the window to process the drawing commands right now
                self.root.update_idletasks() 
                
                # Winner Check
                winner = self.game.check_winner()
                if winner:
                    p_name = "Blue" if winner == 1 else "Red"
                    messagebox.showinfo("Game Over", f"Player {p_name} has won!")
                else:
                    p_name = "White" if self.game.current_player == 1 else "Black"
                    dist = self.game.get_max_distance(self.game.current_player)
                    self.status_label.config(text=f"{p_name}'s Turn (Move distance: {dist})")
                
                self.selected_hex = None # Clear after move
            else:
                print("Invalid move target.")
                self.selected_hex = None # Clear so user can try selecting again
        
        self.draw_board()