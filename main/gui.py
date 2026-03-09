import tkinter as tk
import math
from logic import AnnuvinGame
from tkinter import ttk, messagebox
import ast
from engine import AnnuvinAI

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
        self.root.after(1000, self.check_for_ai_turn)

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
        # 1. Block click if it's the AI turn
        current_type = self.game.player1_type if self.game.current_player == 1 else self.game.player2_type
        if current_type == "AI":
            return

        coords = self.pixel_to_hex(event.x, event.y)
        
        # 2. SELECTION PHASE
        if self.selected_hex is None:
            if coords in self.game.pieces[self.game.current_player]:
                self.selected_hex = coords
                # UPDATE: Draw immediately so the "shadow" highlight appears
                self.draw_board() 
        
        # 3. MOVEMENT PHASE
        else:
            # Deselect if clicking the same piece again
            if coords == self.selected_hex:
                self.selected_hex = None
            elif self.game.is_valid_move(self.selected_hex, coords):
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
                    self.check_for_ai_turn()
            
            # Reset selection and refresh board to clear shadows
            self.selected_hex = None
            self.draw_board()

    def check_for_ai_turn(self):
        """Checks if the next player is an AI and schedules the move."""
        current_type = self.game.player1_type if self.game.current_player == 1 else self.game.player2_type
        if current_type == "AI":
            # Small delay so the human can see the previous move
            self.root.after(1000, self.execute_ai_turn)

    def execute_ai_turn(self):
        curr_p = self.game.current_player
        curr_type = self.game.player1_type if curr_p == 1 else self.game.player2_type
        
        # If the current player isn't an AI, STOP.
        if curr_type != "AI":
            return 

        diff = self.game.p1_difficulty if curr_p == 1 else self.game.p2_difficulty
        ai_engine = AnnuvinAI(self.game, difficulty=diff)
        move = ai_engine.decide_move()
        
        if move:
            start, end = move
            self.game.execute_move(start, end)
            self.draw_board()
            self.root.update_idletasks()
            
            winner = self.game.check_winner()
            if winner:
                p_name = "Black" if winner == 1 else "White"
                messagebox.showinfo("Game Over", f"AI ({p_name}) has won!")
                return # Stop everything

            # Turn has now switched in logic.py. Let's see who is next.
            next_p = self.game.current_player
            next_type = self.game.player1_type if next_p == 1 else self.game.player2_type
            p_name = "Black" if next_p == 1 else "White"
            
            # Update the label so the Human knows they can move
            if next_type == "Human":
                dist = self.game.get_max_distance(next_p)
                self.status_label.config(text=f"{p_name}'s Turn (Your move! Distance: {dist})")
            else:
                self.status_label.config(text=f"{p_name}'s Turn (AI Thinking...)")
                # Only trigger again if the NEXT player is also an AI
                self.check_for_ai_turn()

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

import tkinter as tk
from tkinter import ttk, messagebox

class AnnuvinLauncher:
    def __init__(self, root, on_launch_callback):
        self.root = root
        self.on_launch_callback = on_launch_callback # Store the function
        self.root.title("Annuvin Configuration")
        self.root.geometry("350x450")
        self.root.configure(bg="#D2B48C")

        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self.root, text="ANNUVIN GAME SETTINGS", font=("Arial", 14, "bold"), background="#D2B48C").pack(pady=10)

        # --- Game Mode Selection ---
        ttk.Label(self.root, text="Select Mode:", background="#D2B48C").pack()
        self.mode_var = tk.StringVar(value="PVP")
        modes = [("Person vs Person", "PVP"), ("Person vs AI", "PVAI"), ("AI vs AI", "AVAI")]
        for text, mode in modes:
            tk.Radiobutton(self.root, text=text, variable=self.mode_var, value=mode, bg="#D2B48C", command=self.toggle_ai_options).pack(anchor="w", padx=50)

        # --- AI Configuration Frame ---
        self.ai_frame = tk.Frame(self.root, bg="#D2B48C")
        self.ai_frame.pack(pady=10)

        # Player 1 (Black)
        ttk.Label(self.ai_frame, text="Black (P1):", background="#D2B48C").grid(row=0, column=0)
        self.p1_type = ttk.Combobox(self.ai_frame, values=["Human", "AI"], state="readonly", width=10)
        self.p1_type.set("Human")
        self.p1_type.grid(row=0, column=1, padx=5)

        self.p1_diff = ttk.Combobox(self.ai_frame, values=["Beginner", "Medium", "Hard"], state="readonly", width=10)
        self.p1_diff.set("Beginner")
        self.p1_diff.grid(row=0, column=2)

        # Player 2 (White)
        ttk.Label(self.ai_frame, text="White (P2):", background="#D2B48C").grid(row=1, column=0, pady=5)
        self.p2_type = ttk.Combobox(self.ai_frame, values=["Human", "AI"], state="readonly", width=10)
        self.p2_type.set("Human")
        self.p2_type.grid(row=1, column=1, padx=5)

        self.p2_diff = ttk.Combobox(self.ai_frame, values=["Beginner", "Medium", "Hard"], state="readonly", width=10)
        self.p2_diff.set("Beginner")
        self.p2_diff.grid(row=1, column=2)

        # Launch Button
        tk.Button(self.root, text="START GAME", command=self.launch, bg="black", fg="white", font=("Arial", 10, "bold")).pack(pady=20)

    def toggle_ai_options(self):
        """Auto-sets Human/AI types based on Mode selection."""
        mode = self.mode_var.get()
        if mode == "PVP":
            self.p1_type.set("Human"); self.p2_type.set("Human")
        elif mode == "PVAI":
            self.p1_type.set("Human"); self.p2_type.set("AI")
        elif mode == "AVAI":
            self.p1_type.set("AI"); self.p2_type.set("AI")

    def launch(self):
        # Package settings to pass to the game
        settings = {
            "mode": self.mode_var.get(),
            "p1_type": self.p1_type.get(),
            "p2_type": self.p2_type.get(),
            "p1_diff": self.p1_diff.get(),
            "p2_diff": self.p2_diff.get()
        }
        self.root.destroy() # Close launcher
        # We will call the game GUI next
        self.on_launch_callback(settings)