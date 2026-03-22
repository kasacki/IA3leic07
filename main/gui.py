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
        self.position_history = []  # last N state snapshots for repetition detection

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
                self._record_position()
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

        diff        = self.game.p1_difficulty  if curr_p == 1 else self.game.p2_difficulty
        time_limit  = getattr(self.game, "p1_time_limit"  if curr_p == 1 else "p2_time_limit",  None)
        depth_limit = getattr(self.game, "p1_depth_limit" if curr_p == 1 else "p2_depth_limit", None)
        ai_engine = AnnuvinAI(self.game, difficulty=diff, time_limit=time_limit,
                              depth_limit=depth_limit, position_history=list(self.position_history))
        move = ai_engine.decide_move()
        
        if move:
            start, end = move
            self.game.execute_move(start, end)
            self._record_position()
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

    def _record_position(self):
        """Snapshot the current board state into history. Keep last 6 entries."""
        snapshot = (
            frozenset(self.game.pieces[1]),
            frozenset(self.game.pieces[2]),
            self.game.current_player
        )
        self.position_history.append(snapshot)
        if len(self.position_history) > 6:
            self.position_history.pop(0)

    def reset_game(self):
        self.game = AnnuvinGame()
        self.selected_hex = None
        self.position_history = []
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
        self.on_launch_callback = on_launch_callback
        self.root.title("Annuvin Configuration")
        self.root.configure(bg="#D2B48C")
        self.setup_ui()
        # Size the window to fit content after widgets are placed
        self.root.update_idletasks()
        self.root.resizable(False, False)

    def setup_ui(self):
        ttk.Label(
            self.root, text="ANNUVIN", font=("Arial", 20, "bold"), background="#D2B48C"
        ).pack(pady=(18, 2))
        ttk.Label(
            self.root, text="Game Settings", font=("Arial", 10), background="#D2B48C"
        ).pack(pady=(0, 14))

        # --- Player cards ---
        self._build_player_card(player=1)
        self._build_player_card(player=2)

        # --- Launch button ---
        tk.Button(
            self.root, text="START GAME", command=self.launch,
            bg="black", fg="white", font=("Arial", 11, "bold"),
            padx=20, pady=6, relief="flat", cursor="hand2"
        ).pack(pady=20)

    # ------------------------------------------------------------------
    # Build one player configuration card
    # ------------------------------------------------------------------
    def _build_player_card(self, player):
        label   = "Black (Player 1)" if player == 1 else "White (Player 2)"
        bg      = "#C4A882"   # slightly darker tan for the card

        card = tk.Frame(self.root, bg=bg, bd=1, relief="groove")
        card.pack(fill="x", padx=30, pady=6)

        # Card title
        ttk.Label(card, text=label, font=("Arial", 10, "bold"),
                  background=bg).grid(row=0, column=0, columnspan=3,
                                      sticky="w", padx=10, pady=(8, 4))

        # --- Human / AI toggle ---
        type_var = tk.StringVar(value="Human")
        ttk.Label(card, text="Type:", background=bg).grid(
            row=1, column=0, sticky="w", padx=10, pady=4)

        type_frame = tk.Frame(card, bg=bg)
        type_frame.grid(row=1, column=1, columnspan=2, sticky="w", pady=4)

        for val in ("Human", "AI"):
            tk.Radiobutton(
                type_frame, text=val, variable=type_var, value=val,
                bg=bg, activebackground=bg,
                command=lambda p=player: self._on_type_change(p)
            ).pack(side="left", padx=4)

        # --- Difficulty dropdown (locked when Human) ---
        ttk.Label(card, text="Difficulty:", background=bg).grid(
            row=2, column=0, sticky="w", padx=10, pady=4)

        diff_var = ttk.Combobox(
            card, values=["Beginner", "Medium", "Hard", "Custom"],
            state="disabled", width=10
        )
        diff_var.set("Beginner")
        diff_var.grid(row=2, column=1, sticky="w", padx=6, pady=4)

        # --- Custom controls: time or depth slider (only when Custom selected) ---
        custom_frame = tk.Frame(card, bg=bg)
        custom_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 8))

        # Radio toggle: Time vs Depth
        custom_mode_var = tk.StringVar(value="time")

        tk.Radiobutton(
            custom_frame, text="Time (s)", variable=custom_mode_var, value="time",
            bg=bg, activebackground=bg, state="disabled",
            command=lambda p=player: self._refresh_custom(p)
        ).grid(row=0, column=0, sticky="w")

        tk.Radiobutton(
            custom_frame, text="Depth", variable=custom_mode_var, value="depth",
            bg=bg, activebackground=bg, state="disabled",
            command=lambda p=player: self._refresh_custom(p)
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        time_slider = tk.Scale(
            custom_frame, from_=1, to=15, resolution=1,
            orient="horizontal", bg=bg, length=180,
            highlightthickness=0, state="disabled", label="seconds"
        )
        time_slider.set(3)
        time_slider.grid(row=1, column=0, columnspan=3, sticky="w")

        depth_slider = tk.Scale(
            custom_frame, from_=1, to=8, resolution=1,
            orient="horizontal", bg=bg, length=180,
            highlightthickness=0, state="disabled", label="half-moves"
        )
        depth_slider.set(3)
        depth_slider.grid(row=1, column=0, columnspan=3, sticky="w")
        depth_slider.grid_remove()  # hidden by default

        # Store references
        if player == 1:
            self.p1_type_var      = type_var
            self.p1_diff          = diff_var
            self.p1_custom_frame  = custom_frame
            self.p1_custom_mode   = custom_mode_var
            self.p1_time_slider   = time_slider
            self.p1_depth_slider  = depth_slider
            diff_var.bind("<<ComboboxSelected>>", lambda e: self._refresh_custom(1))
        else:
            self.p2_type_var      = type_var
            self.p2_diff          = diff_var
            self.p2_custom_frame  = custom_frame
            self.p2_custom_mode   = custom_mode_var
            self.p2_time_slider   = time_slider
            self.p2_depth_slider  = depth_slider
            diff_var.bind("<<ComboboxSelected>>", lambda e: self._refresh_custom(2))

    # ------------------------------------------------------------------
    # React to Human ↔ AI toggle
    # ------------------------------------------------------------------
    def _on_type_change(self, player):
        if player == 1:
            is_ai = self.p1_type_var.get() == "AI"
            self.p1_diff.config(state="readonly" if is_ai else "disabled")
            if not is_ai:
                self.p1_diff.set("Beginner")
        else:
            is_ai = self.p2_type_var.get() == "AI"
            self.p2_diff.config(state="readonly" if is_ai else "disabled")
            if not is_ai:
                self.p2_diff.set("Beginner")
        self._refresh_custom(player)

    def _refresh_custom(self, player):
        if player == 1:
            is_custom = self.p1_type_var.get() == "AI" and self.p1_diff.get() == "Custom"
            mode      = self.p1_custom_mode.get()
            frame     = self.p1_custom_frame
            t_sl      = self.p1_time_slider
            d_sl      = self.p1_depth_slider
        else:
            is_custom = self.p2_type_var.get() == "AI" and self.p2_diff.get() == "Custom"
            mode      = self.p2_custom_mode.get()
            frame     = self.p2_custom_frame
            t_sl      = self.p2_time_slider
            d_sl      = self.p2_depth_slider

        # Enable/disable the radio buttons inside the custom frame
        for widget in frame.winfo_children():
            if isinstance(widget, tk.Radiobutton):
                widget.config(state="normal" if is_custom else "disabled")

        # Show the active slider, hide the other
        if mode == "time":
            t_sl.grid()
            d_sl.grid_remove()
        else:
            d_sl.grid()
            t_sl.grid_remove()

        t_sl.config(state="normal" if (is_custom and mode == "time")  else "disabled")
        d_sl.config(state="normal" if (is_custom and mode == "depth") else "disabled")

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------
    def launch(self):
        p1_is_ai = self.p1_type_var.get() == "AI"
        p2_is_ai = self.p2_type_var.get() == "AI"

        if p1_is_ai and p2_is_ai:
            mode = "AVAI"
        elif p2_is_ai:
            mode = "PVAI"
        else:
            mode = "PVP"

        def get_custom(is_ai, diff, mode_var, t_sl, d_sl):
            if not is_ai or diff.get() != "Custom":
                return None, None
            if mode_var.get() == "time":
                return t_sl.get(), None
            else:
                return None, d_sl.get()

        p1_time, p1_depth = get_custom(p1_is_ai, self.p1_diff, self.p1_custom_mode,
                                        self.p1_time_slider, self.p1_depth_slider)
        p2_time, p2_depth = get_custom(p2_is_ai, self.p2_diff, self.p2_custom_mode,
                                        self.p2_time_slider, self.p2_depth_slider)
        settings = {
            "mode":           mode,
            "p1_type":        self.p1_type_var.get(),
            "p2_type":        self.p2_type_var.get(),
            "p1_diff":        self.p1_diff.get(),
            "p2_diff":        self.p2_diff.get(),
            "p1_time_limit":  p1_time,
            "p1_depth_limit": p1_depth,
            "p2_time_limit":  p2_time,
            "p2_depth_limit": p2_depth,
        }
        self.root.destroy()
        self.on_launch_callback(settings)