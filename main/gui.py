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
        # Math for flat-topped hexagons
        x = self.size * (3/2 * q) + 300
        y = self.size * (math.sqrt(3)/2 * q + math.sqrt(3) * r) + 250
        return x, y

    def pixel_to_hex(self, x, y):
        x, y = x - 300, y - 250
        q = (2/3 * x) / self.size
        r = (-1/3 * x + math.sqrt(3)/3 * y) / self.size
        # Rounding to nearest hex
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
                if abs(q + r) <= 3:
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
            angle = math.radians(60 * i)
            points.extend([x + self.size * math.cos(angle), y + self.size * math.sin(angle)])
        self.canvas.create_polygon(points, fill=fill, outline="black")

    def handle_click(self, event):
        coords = self.pixel_to_hex(event.x, event.y)
        
        if self.selected_hex is None:
            if coords in self.game.pieces[self.game.current_player]:
                self.selected_hex = coords
        else:
            if self.game.is_valid_move(self.selected_hex, coords):
                self.game.execute_move(self.selected_hex, coords)
                dist = self.game.get_max_distance(self.game.current_player)
                p_name = "White" if self.game.current_player == 1 else "Black"
                self.status_label.config(text=f"{p_name}'s Turn (Move distance: {dist})")
            self.selected_hex = None
        
        self.draw_board()