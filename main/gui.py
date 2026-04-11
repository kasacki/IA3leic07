import tkinter as tk
import math
import time
from logic import AnnuvinGame
from tkinter import ttk, messagebox
import ast
from engine import AnnuvinAI

class AnnuvinGUI:
    def __init__(self, root):
        self.game = AnnuvinGame()
        self.root = root
        self.size = 35
        self.selected_hex  = None
        self.hint_move     = None
        self.last_move     = None   # (start, end) of the most recent move for shadow
        self.position_history = []
        self.move_log      = []
        self.game_start_time = time.time()
        self._game_over    = False  # guard against double-log / double-popup

        # --- Menu Bar ---
        self.menubar  = tk.Menu(root)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="New Game",  command=self.reset_game)
        self.filemenu.add_command(label="Save Game", command=self.save_game)
        self.filemenu.add_command(label="Load Game", command=self.load_game)
        self.filemenu.add_command(label="Save Log",  command=lambda: self._save_log_manual())
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=root.quit)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.menubar.add_command(label="Get Hint", command=self.suggest_hint)
        root.config(menu=self.menubar)

        # --- UI ---
        root.configure(bg="#D2B48C")
        p_name = "Black" if self.game.current_player == 1 else "White"
        self.status_label = tk.Label(root, text=f"{p_name}'s Turn (Move: 1)",
                                     font=("Arial", 12), bg="#D2B48C")
        self.status_label.pack(fill="x")

        self.canvas = tk.Canvas(root, width=600, height=500,
                                bg="#D2B48C", highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        self.draw_board()
        self.root.after(1000, self.check_for_ai_turn)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def hex_to_pixel(self, q, r):
        x = self.size * (math.sqrt(3) * q + math.sqrt(3)/2 * r) + 300
        y = self.size * (3/2 * r) + 250
        return x, y

    def pixel_to_hex(self, x, y):
        x, y = x - 300, y - 250
        q = (math.sqrt(3)/3 * x - 1/3 * y) / self.size
        r = (2/3 * y) / self.size
        rq, rr = round(q), round(r)
        rs = round(-q - r)
        if abs(rq - q) > abs(rr - r) and abs(rq - q) > abs(rs - (-q - r)):
            rq = -rr - rs
        elif abs(rr - r) > abs(rs - (-q - r)):
            rr = -rq - rs
        return int(rq), int(rr)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw_hexagon(self, x, y, fill):
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            points.extend([x + self.size * math.cos(angle),
                           y + self.size * math.sin(angle)])
        self.canvas.create_polygon(points, fill=fill, outline="black")

    def draw_board(self):
        self.canvas.delete("all")

        hint_start  = self.hint_move[0] if self.hint_move else None
        hint_end    = self.hint_move[1] if self.hint_move else None
        last_start  = self.last_move[0] if self.last_move else None
        last_end    = self.last_move[1] if self.last_move else None

        for q in range(-3, 4):
            for r in range(-3, 4):
                if abs(q) <= 3 and abs(r) <= 3 and abs(q + r) <= 3:
                    x, y  = self.hex_to_pixel(q, r)
                    coord = (q, r)

                    if coord == self.selected_hex:
                        color = "#F0E68C"    # yellow  – selected piece
                    elif coord == hint_start:
                        color = "#90EE90"    # green   – hint origin
                    elif coord == hint_end:
                        color = "#87CEEB"    # blue    – hint destination
                    elif coord == last_start:
                        color = "#FFB347"    # amber   – last-move origin (shadow)
                    elif coord == last_end:
                        color = "#FFA07A"    # light-salmon – last-move destination
                    else:
                        color = "white"

                    self.draw_hexagon(x, y, color)

                    if coord in self.game.pieces[1]:    # Black
                        self.canvas.create_oval(x-15, y-15, x+15, y+15,
                                                fill="black", outline="black")
                    elif coord in self.game.pieces[2]:  # White
                        self.canvas.create_oval(x-15, y-15, x+15, y+15,
                                                fill="white", outline="grey")

    # ------------------------------------------------------------------
    # Human input
    # ------------------------------------------------------------------
    def handle_click(self, event):
        if self._game_over:
            return
        current_type = (self.game.player1_type if self.game.current_player == 1
                        else self.game.player2_type)
        if current_type == "AI":
            return

        coords = self.pixel_to_hex(event.x, event.y)

        if self.selected_hex is None:
            if coords in self.game.pieces[self.game.current_player]:
                self.selected_hex = coords
                self._move_start_time = time.time()
                self.draw_board()
        else:
            if coords == self.selected_hex:
                self.selected_hex = None
            elif self.game.is_valid_move(self.selected_hex, coords):
                elapsed = time.time() - getattr(self, "_move_start_time", time.time())
                curr_p  = self.game.current_player
                self._log_move(curr_p, self.selected_hex, coords, elapsed)
                self.last_move = (self.selected_hex, coords)
                self.game.execute_move(self.selected_hex, coords)
                self._record_position()
                self.selected_hex = None
                self.draw_board()
                self.root.update_idletasks()

                winner = self.game.check_winner()
                if winner is not None:
                    self._end_game(winner)
                else:
                    p_name = "Black" if self.game.current_player == 1 else "White"
                    dist   = self.game.get_max_distance(self.game.current_player)
                    self.status_label.config(text=f"{p_name}'s Turn (Move: {dist})")
                    self.check_for_ai_turn()
                return

            self.selected_hex = None
            self.draw_board()

    # ------------------------------------------------------------------
    # AI turn management
    # ------------------------------------------------------------------
    def check_for_ai_turn(self):
        if self._game_over:
            return
        current_type = (self.game.player1_type if self.game.current_player == 1
                        else self.game.player2_type)
        if current_type == "AI":
            self.root.after(600, self.execute_ai_turn)

    def execute_ai_turn(self):
        if self._game_over:
            return

        curr_p    = self.game.current_player
        curr_type = (self.game.player1_type if curr_p == 1
                     else self.game.player2_type)

        if curr_type != "AI":
            return

        diff        = (self.game.p1_difficulty  if curr_p == 1
                       else self.game.p2_difficulty)
        time_limit  = getattr(self.game,
                              "p1_time_limit"  if curr_p == 1 else "p2_time_limit",  None)
        depth_limit = getattr(self.game,
                              "p1_depth_limit" if curr_p == 1 else "p2_depth_limit", None)

        ai_engine = AnnuvinAI(self.game, difficulty=diff,
                              time_limit=time_limit, depth_limit=depth_limit,
                              position_history=list(self.position_history))

        t0      = time.time()
        move    = ai_engine.decide_move()
        elapsed = time.time() - t0

        if not move:
            return

        start, end = move
        self._log_move(curr_p, start, end, elapsed)
        self.last_move = (start, end)
        self.game.execute_move(start, end)
        self._record_position()
        self.draw_board()
        self.root.update_idletasks()

        winner = self.game.check_winner()
        if winner is not None:
            self._end_game(winner)
            return

        next_p    = self.game.current_player
        next_type = (self.game.player1_type if next_p == 1
                     else self.game.player2_type)
        p_name    = "Black" if next_p == 1 else "White"

        if next_type == "Human":
            dist = self.game.get_max_distance(next_p)
            self.status_label.config(
                text=f"{p_name}'s Turn (Your move! Distance: {dist})")
        else:
            self.status_label.config(text=f"{p_name}'s Turn (AI Thinking...)")
            self.check_for_ai_turn()

    # ------------------------------------------------------------------
    # Game-over handler (single point — no double log)
    # ------------------------------------------------------------------
    def _end_game(self, winner):
        if self._game_over:
            return
        self._game_over = True
        filename = self._save_log(winner)

        if winner == 0:
            msg = f"It's a draw!\n(No captures in 20 moves)\n\nLog saved to:\n{filename}"
        else:
            p_name  = "Black" if winner == 1 else "White"
            w_label = self._player_label(winner)
            msg = f"{p_name} ({w_label}) has won!\n\nLog saved to:\n{filename}"

        messagebox.showinfo("Game Over", msg)

    # ------------------------------------------------------------------
    # Player label helper
    # ------------------------------------------------------------------
    def _player_label(self, player_num):
        p_type = (self.game.player1_type if player_num == 1
                  else self.game.player2_type)
        if p_type == "Human":
            return "Human"
        diff = (self.game.p1_difficulty if player_num == 1
                else self.game.p2_difficulty)
        if diff == "Custom-MCTS":
            tlim = getattr(self.game,
                           "p1_time_limit" if player_num == 1 else "p2_time_limit", 3)
            return f"AI (Custom-MCTS, {tlim}s)"
        if diff == "Custom-ABC":
            depth = getattr(self.game,
                            "p1_depth_limit" if player_num == 1 else "p2_depth_limit", None)
            tlim  = getattr(self.game,
                            "p1_time_limit"  if player_num == 1 else "p2_time_limit",  None)
            if depth is not None:
                return f"AI (Custom-ABC, depth={depth})"
            elif tlim is not None:
                return f"AI (Custom-ABC, time={tlim}s)"
        return f"AI ({diff})"

    # ------------------------------------------------------------------
    # Move logging
    # ------------------------------------------------------------------
    def _log_move(self, player_num, start, end, elapsed):
        self.move_log.append({
            "move_num": len(self.move_log) + 1,
            "player":   player_num,
            "color":    "Black" if player_num == 1 else "White",
            "label":    self._player_label(player_num),
            "start":    start,
            "end":      end,
            "elapsed":  elapsed,
        })

    def _save_log(self, winner):
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"game_{timestamp}.txt"

        p1_label   = self._player_label(1)
        p2_label   = self._player_label(2)
        total_time = time.time() - self.game_start_time

        lines = ["=" * 50, "ANNUVIN GAME LOG", "=" * 50]
        lines.append(f"Date     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Black    : {p1_label}")
        lines.append(f"White    : {p2_label}")
        lines.append(f"Total time: {total_time:.1f}s")
        lines.append("")

        if winner == 0:
            lines.append(f"RESULT: Draw (no captures in 20 moves) after {len(self.move_log)} moves")
        elif winner:
            w_color = "Black" if winner == 1 else "White"
            w_label = self._player_label(winner)
            lines.append(f"RESULT: {w_color} ({w_label}) won in {len(self.move_log)} moves")
        else:
            lines.append("RESULT: Game ended (no winner)")

        lines.append("")
        lines.append("-" * 50)
        lines.append(f"{'#':<5} {'Player':<8} {'Type':<25} {'From':<12} {'To':<12} {'Time(s)'}")
        lines.append("-" * 50)

        for m in self.move_log:
            lines.append(
                f"{m['move_num']:<5} {m['color']:<8} {m['label']:<25} "
                f"{str(m['start']):<12} {str(m['end']):<12} {m['elapsed']:.3f}"
            )

        lines.append("-" * 50)
        for pnum, color in [(1, "Black"), (2, "White")]:
            pmoves = [m for m in self.move_log if m["player"] == pnum]
            if pmoves:
                times = [m["elapsed"] for m in pmoves]
                lines.append(
                    f"{color} ({self._player_label(pnum)}): "
                    f"{len(pmoves)} moves, "
                    f"avg {sum(times)/len(times):.3f}s/move, "
                    f"total {sum(times):.2f}s"
                )
        lines.append("=" * 50)

        with open(filename, "w") as f:
            f.write("\n".join(lines) + "\n")

        return filename

    def _save_log_manual(self):
        filename = self._save_log(winner=None)
        messagebox.showinfo("Log Saved", f"Game log saved to:\n{filename}")

    def _record_position(self):
        snapshot = (
            frozenset(self.game.pieces[1]),
            frozenset(self.game.pieces[2]),
            self.game.current_player
        )
        self.position_history.append(snapshot)
        if len(self.position_history) > 16:
            self.position_history.pop(0)

    # ------------------------------------------------------------------
    # Hint
    # ------------------------------------------------------------------
    def suggest_hint(self):
        cp = self.game.current_player
        if (self.game.player1_type if cp == 1 else self.game.player2_type) == "AI":
            messagebox.showinfo("Hint", "It's the AI's turn — no hint needed!")
            return

        ai   = AnnuvinAI(self.game, difficulty="Hard-ABC")
        move = ai.get_minimax_move(depth=2, eval_fn=ai._evaluate_hard)
        if move:
            start, end = move
            self.hint_move = move
            self.draw_board()
            messagebox.showinfo("Hint", f"Suggested move:\n  From {start}  →  To {end}")
            self.hint_move = None
            self.draw_board()
        else:
            messagebox.showinfo("Hint", "No moves available!")

    # ------------------------------------------------------------------
    # Game management
    # ------------------------------------------------------------------
    def reset_game(self):
        self.game             = AnnuvinGame()
        self.selected_hex     = None
        self.last_move        = None
        self.hint_move        = None
        self.position_history = []
        self.move_log         = []
        self.game_start_time  = time.time()
        self._game_over       = False
        self.status_label.config(text="Black's Turn (Move: 1)")
        self.draw_board()

    def save_game(self):
        with open("savegame.txt", "w") as f:
            f.write(f"{self.game.current_player}\n")
            f.write(f"{self.game.pieces[1]}\n")
            f.write(f"{self.game.pieces[2]}\n")
            f.write(f"{self.game.moves_since_capture}\n")
        messagebox.showinfo("Save", "Game state saved to savegame.txt")

    def load_game(self):
        try:
            with open("savegame.txt", "r") as f:
                lines = f.readlines()
            self.game.current_player       = int(lines[0].strip())
            self.game.pieces[1]            = ast.literal_eval(lines[1].strip())
            self.game.pieces[2]            = ast.literal_eval(lines[2].strip())
            self.game.moves_since_capture  = int(lines[3].strip()) if len(lines) > 3 else 0
            self.last_move  = None
            self._game_over = False
            self.draw_board()
            messagebox.showinfo("Load", "Game loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load: {e}")


# ==================================================================
# Launcher
# ==================================================================

class AnnuvinLauncher:
    # All available difficulty strings, in display order
    DIFFICULTIES = [
        "Beginner",
        "Medium-ABC",
        "Hard-ABC",
        "Medium-MCTS",
        "Hard-MCTS",
        "Custom-ABC",
        "Custom-MCTS",
    ]
    # Which difficulties need a time slider
    _TIME_DIFFS  = {"Medium-MCTS", "Hard-MCTS", "Custom-MCTS", "Custom-ABC"}
    # Which difficulties need a depth slider (Custom-ABC only when depth mode)
    _DEPTH_DIFFS = {"Custom-ABC"}

    def __init__(self, root, on_launch_callback):
        self.root               = root
        self.on_launch_callback = on_launch_callback
        self.root.title("Annuvin Configuration")
        self.root.configure(bg="#D2B48C")
        self.setup_ui()
        self.root.update_idletasks()
        self.root.resizable(False, False)

    def setup_ui(self):
        ttk.Label(self.root, text="ANNUVIN",
                  font=("Arial", 20, "bold"), background="#D2B48C").pack(pady=(18, 2))
        ttk.Label(self.root, text="Game Settings",
                  font=("Arial", 10), background="#D2B48C").pack(pady=(0, 14))

        self._build_player_card(player=1)
        self._build_player_card(player=2)

        tk.Button(
            self.root, text="START GAME", command=self.launch,
            bg="black", fg="white", font=("Arial", 11, "bold"),
            padx=20, pady=6, relief="flat", cursor="hand2"
        ).pack(pady=20)

    def _build_player_card(self, player):
        label = "Black (Player 1)" if player == 1 else "White (Player 2)"
        bg    = "#C4A882"

        card = tk.Frame(self.root, bg=bg, bd=1, relief="groove")
        card.pack(fill="x", padx=30, pady=6)

        ttk.Label(card, text=label, font=("Arial", 10, "bold"),
                  background=bg).grid(row=0, column=0, columnspan=3,
                                      sticky="w", padx=10, pady=(8, 4))

        # Human / AI toggle
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

        # Difficulty dropdown
        ttk.Label(card, text="Difficulty:", background=bg).grid(
            row=2, column=0, sticky="w", padx=10, pady=4)

        diff_var = ttk.Combobox(card, values=self.DIFFICULTIES,
                                state="disabled", width=14)
        diff_var.set("Beginner")
        diff_var.grid(row=2, column=1, sticky="w", padx=6, pady=4)

        # Custom controls frame (time / depth sliders)
        custom_frame = tk.Frame(card, bg=bg)
        custom_frame.grid(row=3, column=0, columnspan=3,
                          sticky="w", padx=10, pady=(2, 8))

        # Time-vs-depth radio (only relevant for Custom-ABC)
        custom_mode_var = tk.StringVar(value="time")
        rb_time = tk.Radiobutton(
            custom_frame, text="Time (s)", variable=custom_mode_var, value="time",
            bg=bg, activebackground=bg, state="disabled",
            command=lambda p=player: self._refresh_custom(p)
        )
        rb_time.grid(row=0, column=0, sticky="w")

        rb_depth = tk.Radiobutton(
            custom_frame, text="Depth", variable=custom_mode_var, value="depth",
            bg=bg, activebackground=bg, state="disabled",
            command=lambda p=player: self._refresh_custom(p)
        )
        rb_depth.grid(row=0, column=1, sticky="w", padx=(8, 0))

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
        depth_slider.grid_remove()

        # Store widget references per player
        if player == 1:
            self.p1_type_var     = type_var
            self.p1_diff         = diff_var
            self.p1_custom_frame = custom_frame
            self.p1_custom_mode  = custom_mode_var
            self.p1_rb_time      = rb_time
            self.p1_rb_depth     = rb_depth
            self.p1_time_slider  = time_slider
            self.p1_depth_slider = depth_slider
            diff_var.bind("<<ComboboxSelected>>", lambda e: self._refresh_custom(1))
        else:
            self.p2_type_var     = type_var
            self.p2_diff         = diff_var
            self.p2_custom_frame = custom_frame
            self.p2_custom_mode  = custom_mode_var
            self.p2_rb_time      = rb_time
            self.p2_rb_depth     = rb_depth
            self.p2_time_slider  = time_slider
            self.p2_depth_slider = depth_slider
            diff_var.bind("<<ComboboxSelected>>", lambda e: self._refresh_custom(2))

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
            diff_val   = self.p1_diff.get()
            is_ai      = self.p1_type_var.get() == "AI"
            mode       = self.p1_custom_mode.get()
            t_sl       = self.p1_time_slider
            d_sl       = self.p1_depth_slider
            rb_t       = self.p1_rb_time
            rb_d       = self.p1_rb_depth
        else:
            diff_val   = self.p2_diff.get()
            is_ai      = self.p2_type_var.get() == "AI"
            mode       = self.p2_custom_mode.get()
            t_sl       = self.p2_time_slider
            d_sl       = self.p2_depth_slider
            rb_t       = self.p2_rb_time
            rb_d       = self.p2_rb_depth

        # Determine what controls to show
        is_custom_abc  = is_ai and diff_val == "Custom-ABC"
        is_mcts_custom = is_ai and diff_val == "Custom-MCTS"
        # Medium/Hard MCTS also expose a time slider (read-only defaults)
        is_mcts_preset = is_ai and diff_val in ("Medium-MCTS", "Hard-MCTS")

        show_time  = is_custom_abc or is_mcts_custom
        show_radios = is_custom_abc   # only Custom-ABC gets the time/depth toggle

        # Radios
        rb_t.config(state="normal" if show_radios else "disabled")
        rb_d.config(state="normal" if show_radios else "disabled")

        # For Custom-ABC honour the radio; for MCTS variants always show time
        effective_mode = mode if is_custom_abc else "time"

        if effective_mode == "time" or is_mcts_custom or is_mcts_preset:
            t_sl.grid()
            d_sl.grid_remove()
        else:
            d_sl.grid()
            t_sl.grid_remove()

        t_sl.config(state="normal" if show_time else "disabled")
        d_sl.config(state="normal" if (is_custom_abc and mode == "depth") else "disabled")

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
        elif p1_is_ai:
            mode = "PVAI"
        else:
            mode = "PVP"

        def get_limits(is_ai, diff_combo, mode_var, t_sl, d_sl):
            if not is_ai:
                return None, None
            d = diff_combo.get()
            if d in ("Custom-MCTS", "Medium-MCTS", "Hard-MCTS"):
                return t_sl.get(), None
            if d == "Custom-ABC":
                if mode_var.get() == "time":
                    return t_sl.get(), None
                else:
                    return None, d_sl.get()
            return None, None

        p1_time, p1_depth = get_limits(p1_is_ai, self.p1_diff, self.p1_custom_mode,
                                        self.p1_time_slider, self.p1_depth_slider)
        p2_time, p2_depth = get_limits(p2_is_ai, self.p2_diff, self.p2_custom_mode,
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
