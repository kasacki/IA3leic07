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
        self.hint_move = None   # (start, end) highlighted on the board

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
        hint_start = self.hint_move[0] if self.hint_move else None
        hint_end   = self.hint_move[1] if self.hint_move else None

        for q in range(-3, 4):
            for r in range(-3, 4):
                if abs(q) <= 3 and abs(r) <= 3 and abs(q + r) <= 3:
                    x, y = self.hex_to_pixel(q, r)
                    coord = (q, r)

                    if coord == self.selected_hex:
                        color = "#F0E68C"        # yellow: selected piece
                    elif coord == hint_start:
                        color = "#90EE90"        # green: hint origin
                    elif coord == hint_end:
                        color = "#87CEEB"        # blue: hint destination
                    else:
                        color = "white"

                    self.draw_hexagon(x, y, color)

                    if coord in self.game.pieces[1]:   # Black
                        self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="black", outline="black")
                    elif coord in self.game.pieces[2]: # White
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
        time_limit = getattr(self.game, "time_limit", None)
        ai_engine = AnnuvinAI(self.game, difficulty=diff, time_limit=time_limit)
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
        """Use a shallow Minimax search to suggest the best move."""
        cp = self.game.current_player
        current_type = self.game.player1_type if cp == 1 else self.game.player2_type
        if current_type == "AI":
            messagebox.showinfo("Hint", "It's the AI's turn — no hint needed!")
            return

        ai = AnnuvinAI(self.game, difficulty="Hard")
        move = ai.get_minimax_move(depth=2, eval_fn=ai._evaluate_hard)
        if move:
            start, end = move
            self.hint_move = move
            self.draw_board()   # redraws with hint highlight
            messagebox.showinfo(
                "Hint",
                f"Suggested move:\n  From {start}  →  To {end}"
            )
            self.hint_move = None
            self.draw_board()   # clear highlight after dialog closes
        else:
            messagebox.showinfo("Hint", "No moves available!")

import tkinter as tk
from tkinter import ttk, messagebox

class AnnuvinLauncher:
    def __init__(self, root, on_launch_callback):
        self.root = root
        self.on_launch_callback = on_launch_callback # Store the function
        self.root.title("Annuvin Configuration")
        self.root.geometry("370x520")
        self.root.configure(bg="#D2B48C")

        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self.root, text="ANNUVIN GAME SETTINGS", font=("Arial", 14, "bold"), background="#D2B48C").pack(pady=10)

        # --- Game Mode Selection ---
        ttk.Label(self.root, text="Select Mode:", background="#D2B48C").pack()
        self.mode_var = tk.StringVar(value="PVP")
        modes = [("Person vs Person", "PVP"), ("Person vs AI", "PVAI"), ("AI vs AI", "AVAI")]
        for text, mode in modes:
            tk.Radiobutton(self.root, text=text, variable=self.mode_var, value=mode,
                           bg="#D2B48C", command=self.toggle_ai_options).pack(anchor="w", padx=50)

        # --- AI Configuration Frame ---
        self.ai_frame = tk.Frame(self.root, bg="#D2B48C")
        self.ai_frame.pack(pady=10)

        # Header row
        ttk.Label(self.ai_frame, text="Player",     background="#D2B48C", width=10).grid(row=0, column=0)
        ttk.Label(self.ai_frame, text="Type",       background="#D2B48C", width=10).grid(row=0, column=1)
        ttk.Label(self.ai_frame, text="Difficulty", background="#D2B48C", width=10).grid(row=0, column=2)

        # Player 1 (Black)
        ttk.Label(self.ai_frame, text="Black (P1):", background="#D2B48C").grid(row=1, column=0, pady=4)
        self.p1_type = ttk.Combobox(self.ai_frame, values=["Human", "AI"], state="readonly", width=9)
        self.p1_type.set("Human")
        self.p1_type.grid(row=1, column=1, padx=5)
        self.p1_diff = ttk.Combobox(self.ai_frame, values=["Beginner", "Medium", "Hard"], state="readonly", width=9)
        self.p1_diff.set("Beginner")
        self.p1_diff.grid(row=1, column=2)

        # Player 2 (White)
        ttk.Label(self.ai_frame, text="White (P2):", background="#D2B48C").grid(row=2, column=0, pady=4)
        self.p2_type = ttk.Combobox(self.ai_frame, values=["Human", "AI"], state="readonly", width=9)
        self.p2_type.set("Human")
        self.p2_type.grid(row=2, column=1, padx=5)
        self.p2_diff = ttk.Combobox(self.ai_frame, values=["Beginner", "Medium", "Hard"], state="readonly", width=9)
        self.p2_diff.set("Beginner")
        self.p2_diff.grid(row=2, column=2)

        # --- Think-time slider ---
        time_frame = tk.Frame(self.root, bg="#D2B48C")
        time_frame.pack(pady=8, fill="x", padx=30)

        ttk.Label(time_frame, text="AI Think Time:", background="#D2B48C").pack(side="left")
        self.use_time_limit = tk.BooleanVar(value=False)
        tk.Checkbutton(time_frame, text="Enable", variable=self.use_time_limit,
                       bg="#D2B48C", command=self._toggle_slider).pack(side="left", padx=6)

        slider_frame = tk.Frame(self.root, bg="#D2B48C")
        slider_frame.pack(fill="x", padx=30)

        self.time_slider = tk.Scale(
            slider_frame, from_=1, to=10, resolution=1,
            orient="horizontal", label="Seconds per move",
            bg="#D2B48C", length=200, state="disabled"
        )
        self.time_slider.set(3)
        self.time_slider.pack()

        ttk.Label(self.root,
                  text="(When enabled, overrides difficulty depth\nand uses iterative deepening instead)",
                  background="#D2B48C", font=("Arial", 8), foreground="#555555").pack()

        # Launch Button
        tk.Button(self.root, text="START GAME", command=self.launch,
                  bg="black", fg="white", font=("Arial", 10, "bold")).pack(pady=15)

    def _toggle_slider(self):
        state = "normal" if self.use_time_limit.get() else "disabled"
        self.time_slider.config(state=state)

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
        time_limit = self.time_slider.get() if self.use_time_limit.get() else None
        settings = {
            "mode":       self.mode_var.get(),
            "p1_type":    self.p1_type.get(),
            "p2_type":    self.p2_type.get(),
            "p1_diff":    self.p1_diff.get(),
            "p2_diff":    self.p2_diff.get(),
            "time_limit": time_limit,
        }
        self.root.destroy()
        self.on_launch_callback(settings)