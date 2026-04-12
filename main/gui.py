import tkinter as tk
import math
import time
import re
import ast
import wave
import struct
import tempfile
import os
import sys
import threading
from logic import AnnuvinGame
from tkinter import ttk, messagebox, filedialog
from engine import AnnuvinAI


# ==================================================================
# Cross-platform sound engine
# ==================================================================

class SoundEngine:
    """
    Generates a wooden-thock WAV at startup and plays it cross-platform.

    Priority:
      1. pygame.mixer  — best latency, works on all three platforms
      2. subprocess    — aplay (Linux), afplay (macOS), PowerShell (Windows)
      3. tkinter bell  — silent fallback (just a beep, better than nothing)

    The WAV is created once in a temp file and deleted on exit.
    """

    def __init__(self):
        self.muted   = False
        self.volume  = 0.7          # 0.0 – 1.0
        self._wav    = None         # path to temp WAV
        self._pygame = False
        self._sound  = None         # pygame.Sound object if available
        self._root   = None         # set later so bell() works

        self._wav = self._generate_wav()
        self._init_pygame()

    # ------------------------------------------------------------------
    # WAV generation (pure stdlib — no numpy, no external deps)
    # ------------------------------------------------------------------
    def _generate_wav(self):
        sample_rate = 44100
        duration    = 0.18
        n           = int(sample_rate * duration)

        samples = []
        for i in range(n):
            t     = i / sample_rate
            # Woody body: two exponentially-decaying tones
            body  = math.sin(2 * math.pi * 180 * t) * math.exp(-t * 45)
            body += math.sin(2 * math.pi * 320 * t) * math.exp(-t * 60) * 0.5
            # Sharp click transient
            click = math.sin(2 * math.pi * 900 * t) * math.exp(-t * 200) * 0.4
            val   = int((body + click) * 28000 * self.volume)
            samples.append(max(-32767, min(32767, val)))

        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{n}h", *samples))
        return path

    def _init_pygame(self):
        try:
            import pygame
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
            self._sound  = pygame.mixer.Sound(self._wav)
            self._sound.set_volume(self.volume)
            self._pygame = True
        except Exception:
            self._pygame = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_root(self, root):
        self._root = root

    def set_volume(self, vol):
        """vol: float 0.0–1.0"""
        self.volume = float(vol)
        if self._pygame and self._sound:
            self._sound.set_volume(self.volume)
        # Regenerate WAV at new volume for subprocess fallback
        if not self._pygame and self._wav:
            try:
                os.unlink(self._wav)
            except OSError:
                pass
            self._wav = self._generate_wav()

    def play(self):
        if self.muted or self.volume == 0:
            return
        if self._pygame and self._sound:
            self._sound.play()
        else:
            # Subprocess fallback — run in background so UI doesn't stall
            threading.Thread(target=self._play_subprocess, daemon=True).start()

    def _play_subprocess(self):
        if not self._wav or not os.path.exists(self._wav):
            return
        try:
            if sys.platform.startswith("linux"):
                os.system(f"aplay -q '{self._wav}' 2>/dev/null")
            elif sys.platform == "darwin":
                os.system(f"afplay '{self._wav}'")
            elif sys.platform == "win32":
                import ctypes
                ctypes.windll.winmm.PlaySoundW(self._wav, None, 0x20001)
        except Exception:
            if self._root:
                self._root.bell()

    def cleanup(self):
        if self._pygame:
            try:
                import pygame
                pygame.mixer.quit()
            except Exception:
                pass
        if self._wav and os.path.exists(self._wav):
            try:
                os.unlink(self._wav)
            except OSError:
                pass


# Singleton — created once at import time
_sound_engine = SoundEngine()


# ==================================================================
# Log / save-file parser  (handles both formats)
# ==================================================================

def parse_game_file(text):
    """
    Parse either a game-log file or a savegame.txt file.

    Returns a dict with:
      format        : "log" | "save"

    For "log":
      p1_label      : str  (e.g. "AI (Medium-ABC)")
      p2_label      : str
      moves         : list of (start_coord, end_coord) tuples

    For "save":
      current_player : int (1 or 2)
      pieces1        : list of (q,r) tuples
      pieces2        : list of (q,r) tuples
      moves_since_capture : int
    """
    text = text.strip()

    # ---- Game-log format ----
    if "ANNUVIN GAME LOG" in text:
        p1_label, p2_label = "Human", "Human"
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("Black    :") or s.startswith("Black:"):
                p1_label = s.split(":", 1)[1].strip()
            elif s.startswith("White    :") or s.startswith("White:"):
                p2_label = s.split(":", 1)[1].strip()

        moves = []
        in_table = False
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#") and "Player" in s:
                in_table = True
                continue
            if not in_table:
                continue
            if s.startswith("-") or not s:
                continue
            if s[0].isdigit():
                coords = re.findall(r"\(-?\d+,\s*-?\d+\)", s)
                if len(coords) >= 2:
                    moves.append((
                        ast.literal_eval(coords[0]),
                        ast.literal_eval(coords[1]),
                    ))

        return {
            "format":   "log",
            "p1_label": p1_label,
            "p2_label": p2_label,
            "moves":    moves,
        }

    # ---- Savegame format (4 plain lines) ----
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 3:
        try:
            current_player = int(lines[0])
            pieces1        = ast.literal_eval(lines[1])
            pieces2        = ast.literal_eval(lines[2])
            moves_since    = int(lines[3]) if len(lines) > 3 else 0
            return {
                "format":               "save",
                "current_player":       current_player,
                "pieces1":              pieces1,
                "pieces2":              pieces2,
                "moves_since_capture":  moves_since,
            }
        except Exception:
            pass

    raise ValueError("Unrecognised file format — expected a game log or savegame.txt")


def label_to_settings(label):
    """
    Convert a player label string (from a log header) to
    (player_type, difficulty) suitable for the launcher dropdowns.

    Examples:
      "Human"              -> ("Human", "Beginner")
      "AI (Medium-ABC)"    -> ("AI",    "Medium-ABC")
      "AI (Hard-MCTS)"     -> ("AI",    "Hard-MCTS")
      "AI (Custom-ABC, …)" -> ("AI",    "Custom-ABC")
    """
    KNOWN = [
        "Medium-ABC", "Hard-ABC",
        "Medium-MCTS", "Hard-MCTS",
        "Custom-ABC", "Custom-MCTS",
        "Beginner",
    ]
    label = label.strip()
    if not label.startswith("AI"):
        return ("Human", "Beginner")

    # Extract the content inside the first pair of parentheses
    inner = ""
    if "(" in label:
        inner = label[label.index("(") + 1:]
        if ")" in inner:
            inner = inner[: inner.index(")")]

    for k in KNOWN:
        if k.lower() in inner.lower() or k.lower() in label.lower():
            return ("AI", k)

    return ("AI", "Beginner")


# ==================================================================
# In-game GUI
# ==================================================================

class AnnuvinGUI:
    def __init__(self, root, on_new_game=None):
        self.game             = AnnuvinGame()
        self.root             = root
        self._on_new_game_cb  = on_new_game
        self.size             = 35
        self.selected_hex     = None
        self.hint_move        = None
        self.last_move        = None
        self.position_history = []
        self.move_log         = []
        self.game_start_time  = time.time()
        self._game_over       = False

        _sound_engine.set_root(root)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- Menu Bar ---
        self.menubar  = tk.Menu(root)

        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="New Game", command=self.reset_game)
        self.filemenu.add_command(label="Save Game", command=self.save_game)
        self.filemenu.add_command(label="Save Log",  command=self._save_log_manual)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self._on_close)
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

    def _on_close(self):
        _sound_engine.cleanup()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def hex_to_pixel(self, q, r):
        x = self.size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r) + 300
        y = self.size * (3 / 2 * r) + 250
        return x, y

    def pixel_to_hex(self, x, y):
        x, y = x - 300, y - 250
        q    = (math.sqrt(3) / 3 * x - 1 / 3 * y) / self.size
        r    = (2 / 3 * y) / self.size
        rq, rr = round(q), round(r)
        rs   = round(-q - r)
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

        hint_start = self.hint_move[0] if self.hint_move else None
        hint_end   = self.hint_move[1] if self.hint_move else None
        last_start = self.last_move[0]  if self.last_move  else None
        last_end   = self.last_move[1]  if self.last_move  else None

        for q in range(-3, 4):
            for r in range(-3, 4):
                if abs(q) <= 3 and abs(r) <= 3 and abs(q + r) <= 3:
                    x, y  = self.hex_to_pixel(q, r)
                    coord = (q, r)

                    if coord == self.selected_hex:
                        color = "#F0E68C"   # yellow       – selected
                    elif coord == hint_start:
                        color = "#90EE90"   # green        – hint origin
                    elif coord == hint_end:
                        color = "#87CEEB"   # sky-blue     – hint dest
                    elif coord == last_start:
                        color = "#FFB347"   # amber        – last-move origin
                    elif coord == last_end:
                        color = "#FFA07A"   # light-salmon – last-move dest
                    else:
                        color = "white"

                    self.draw_hexagon(x, y, color)

                    if coord in self.game.pieces[1]:
                        self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15,
                                                fill="black", outline="black")
                    elif coord in self.game.pieces[2]:
                        self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15,
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
                self.selected_hex     = coords
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
                _sound_engine.play()
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

        diff        = self.game.p1_difficulty  if curr_p == 1 else self.game.p2_difficulty
        time_limit  = getattr(self.game, "p1_time_limit"  if curr_p == 1 else "p2_time_limit",  None)
        depth_limit = getattr(self.game, "p1_depth_limit" if curr_p == 1 else "p2_depth_limit", None)

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
        _sound_engine.play()
        self.draw_board()
        self.root.update_idletasks()

        winner = self.game.check_winner()
        if winner is not None:
            self._end_game(winner)
            return

        next_p    = self.game.current_player
        next_type = (self.game.player1_type if next_p == 1 else self.game.player2_type)
        p_name    = "Black" if next_p == 1 else "White"

        if next_type == "Human":
            dist = self.game.get_max_distance(next_p)
            self.status_label.config(text=f"{p_name}'s Turn (Your move! Distance: {dist})")
        else:
            self.status_label.config(text=f"{p_name}'s Turn (AI Thinking...)")
            self.check_for_ai_turn()

    # ------------------------------------------------------------------
    # Game-over (single entry point — prevents double log)
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
    # Helpers
    # ------------------------------------------------------------------
    def _player_label(self, player_num):
        p_type = (self.game.player1_type if player_num == 1 else self.game.player2_type)
        if p_type == "Human":
            return "Human"
        diff = (self.game.p1_difficulty if player_num == 1 else self.game.p2_difficulty)
        if diff == "Custom-MCTS":
            tlim = getattr(self.game, "p1_time_limit" if player_num == 1 else "p2_time_limit", 3)
            return f"AI (Custom-MCTS, {tlim}s)"
        if diff == "Custom-ABC":
            depth = getattr(self.game, "p1_depth_limit" if player_num == 1 else "p2_depth_limit", None)
            tlim  = getattr(self.game, "p1_time_limit"  if player_num == 1 else "p2_time_limit",  None)
            if depth is not None:
                return f"AI (Custom-ABC, depth={depth})"
            elif tlim is not None:
                return f"AI (Custom-ABC, time={tlim}s)"
        return f"AI ({diff})"

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
        os.makedirs("Logs", exist_ok=True)
        timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename   = os.path.join("Logs", f"game_{timestamp}.txt")
        total_time = time.time() - self.game_start_time

        lines = ["=" * 50, "ANNUVIN GAME LOG", "=" * 50]
        lines.append(f"Date     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Black    : {self._player_label(1)}")
        lines.append(f"White    : {self._player_label(2)}")
        lines.append(f"Total time: {total_time:.1f}s")
        lines.append("")

        if winner == 0:
            lines.append(f"RESULT: Draw (no captures in 20 moves) after {len(self.move_log)} moves")
        elif winner:
            w_color = "Black" if winner == 1 else "White"
            lines.append(f"RESULT: {w_color} ({self._player_label(winner)}) won in {len(self.move_log)} moves")
        else:
            lines.append("RESULT: Game ended (no winner)")

        lines += ["", "-" * 50,
                  f"{'#':<5} {'Player':<8} {'Type':<25} {'From':<12} {'To':<12} {'Time(s)'}",
                  "-" * 50]

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
        snap = (frozenset(self.game.pieces[1]),
                frozenset(self.game.pieces[2]),
                self.game.current_player)
        self.position_history.append(snap)
        if len(self.position_history) > 16:
            self.position_history.pop(0)

    def save_game(self):
        import datetime
        os.makedirs("Logs", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = os.path.join("Logs", f"savegame_{timestamp}.txt")
        with open(filename, "w") as f:
            f.write(f"{self.game.current_player}\n")
            f.write(f"{self.game.pieces[1]}\n")
            f.write(f"{self.game.pieces[2]}\n")
            f.write(f"{self.game.moves_since_capture}\n")
        messagebox.showinfo("Save", f"Game state saved to {filename}")

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
            self.hint_move = move
            self.draw_board()
            messagebox.showinfo("Hint",
                                f"Suggested move:\n  From {move[0]}  →  To {move[1]}")
            self.hint_move = None
            self.draw_board()
        else:
            messagebox.showinfo("Hint", "No moves available!")

    # ------------------------------------------------------------------
    # Game management
    # ------------------------------------------------------------------
    def reset_game(self):
        if self._on_new_game_cb is not None:
            _sound_engine.cleanup()
            self.root.destroy()
            self._on_new_game_cb()
            return
        # Fallback: reset in-place (when launched without callback)
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


# ==================================================================
# Launcher
# ==================================================================

class AnnuvinLauncher:
    DIFFICULTIES = [
        "Beginner",
        "Medium-ABC", "Hard-ABC",
        "Medium-MCTS", "Hard-MCTS",
        "Custom-ABC", "Custom-MCTS",
    ]

    def __init__(self, root, on_launch_callback):
        self.root               = root
        self.on_launch_callback = on_launch_callback
        self.root.title("Annuvin — Configuration")
        self.root.configure(bg="#D2B48C")

        # Loaded-game state (None until a file is loaded)
        self._loaded_game = None   # dict from parse_game_file, format=="log" only
        self._loaded_moves = []    # move list replayed into the game

        self._build_menubar()
        self._build_ui()

        self.root.update_idletasks()
        self.root.resizable(False, False)

    # ------------------------------------------------------------------
    # Menu bar (File + Sound)
    # ------------------------------------------------------------------
    def _build_menubar(self):
        menubar = tk.Menu(self.root)

        # File menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Load Game…", command=self._load_game_dialog)
        menubar.add_cascade(label="File", menu=filemenu)

        self.root.config(menu=menubar)

    def _toggle_mute(self):
        _sound_engine.muted = self._mute_var.get()

    def _on_volume_change(self, val):
        vol = int(val) / 100.0
        _sound_engine.set_volume(vol)
        if vol == 0:
            self._mute_var.set(True)
            _sound_engine.muted = True
        else:
            self._mute_var.set(False)
            _sound_engine.muted = False

    # ------------------------------------------------------------------
    # Main launcher UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        ttk.Label(self.root, text="ANNUVIN",
                  font=("Arial", 20, "bold"), background="#D2B48C").pack(pady=(10, 2))
        self._subtitle = ttk.Label(self.root, text="Game Settings",
                                   font=("Arial", 10), background="#D2B48C")
        self._subtitle.pack(pady=(0, 6))

        # --- Sound controls ---
        sound_frame = tk.Frame(self.root, bg="#D2B48C")
        sound_frame.pack(pady=(0, 8))

        tk.Label(sound_frame, text="🔊", bg="#D2B48C",
                 font=("Arial", 11)).pack(side="left", padx=(0, 4))

        self._mute_var = tk.BooleanVar(value=_sound_engine.muted)
        self._vol_slider = tk.Scale(
            sound_frame, from_=0, to=100, orient="horizontal",
            length=160, bg="#D2B48C", highlightthickness=0,
            showvalue=False, command=self._on_volume_change
        )
        self._vol_slider.set(int(_sound_engine.volume * 100))
        self._vol_slider.pack(side="left")

        tk.Checkbutton(
            sound_frame, text="Mute", variable=self._mute_var,
            bg="#D2B48C", activebackground="#D2B48C",
            command=self._toggle_mute
        ).pack(side="left", padx=(6, 0))

        self._build_player_card(player=1)
        self._build_player_card(player=2)

        tk.Button(
            self.root, text="START GAME", command=self.launch,
            bg="black", fg="white", font=("Arial", 11, "bold"),
            padx=20, pady=6, relief="flat", cursor="hand2"
        ).pack(pady=18)

    # ------------------------------------------------------------------
    # Load Game dialog
    # ------------------------------------------------------------------
    def _load_game_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Load Game",
            filetypes=[("Game files", "*.txt"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, "r") as f:
                text = f.read()
            parsed = parse_game_file(text)
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
            return

        if parsed["format"] == "save":
            # Savegame: no player-type info, just board state.
            # Pre-fill defaults and let user choose.
            messagebox.showinfo(
                "Save file loaded",
                "Loaded a board snapshot (savegame.txt).\n"
                "Choose player settings below, then click START GAME.\n"
                "The board will start from the saved position."
            )
            self._loaded_game  = parsed
            self._loaded_moves = []   # no moves to replay
            self._subtitle.config(text="Loaded: savegame.txt")
            return

        # Game log: replay moves to reconstruct board, pre-fill player cards
        p1_type, p1_diff = label_to_settings(parsed["p1_label"])
        p2_type, p2_diff = label_to_settings(parsed["p2_label"])

        self._apply_player_defaults(1, p1_type, p1_diff)
        self._apply_player_defaults(2, p2_type, p2_diff)

        # Replay moves
        game = AnnuvinGame()
        for start, end in parsed["moves"]:
            if game.check_winner() is not None:
                break
            game.execute_move(start, end)

        self._loaded_game  = parsed
        self._loaded_game["_game_obj"] = game
        self._loaded_moves = parsed["moves"]

        n     = len(parsed["moves"])
        fname = os.path.basename(filepath)
        self._subtitle.config(text=f"Loaded: {fname}  ({n} moves)")

        winner = game.check_winner()
        if winner is not None:
            label = {0: "Draw", 1: "Black wins", 2: "White wins"}.get(winner, "?")
            messagebox.showinfo(
                "Game already finished",
                f"This log shows a completed game ({label}).\n"
                f"You can still START GAME to replay it from the beginning, "
                f"or adjust settings and play a new game."
            )
        else:
            p_name = "Black" if game.current_player == 1 else "White"
            messagebox.showinfo(
                "Log loaded",
                f"{n} moves replayed.\n"
                f"It is {p_name}'s turn.\n"
                f"Adjust settings if needed, then click START GAME."
            )

    def _apply_player_defaults(self, player, p_type, p_diff):
        """Pre-fill the player card widgets from loaded file info."""
        if player == 1:
            type_var = self.p1_type_var
            diff_cb  = self.p1_diff
        else:
            type_var = self.p2_type_var
            diff_cb  = self.p2_diff

        type_var.set(p_type)
        self._on_type_change(player)   # enable/disable diff dropdown

        if p_type == "AI" and p_diff in self.DIFFICULTIES:
            diff_cb.set(p_diff)
            self._refresh_custom(player)

    # ------------------------------------------------------------------
    # Player cards
    # ------------------------------------------------------------------
    def _build_player_card(self, player):
        label = "Black (Player 1)" if player == 1 else "White (Player 2)"
        bg    = "#C4A882"

        card = tk.Frame(self.root, bg=bg, bd=1, relief="groove")
        card.pack(fill="x", padx=30, pady=5)

        ttk.Label(card, text=label, font=("Arial", 10, "bold"),
                  background=bg).grid(row=0, column=0, columnspan=3,
                                      sticky="w", padx=10, pady=(8, 4))

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

        ttk.Label(card, text="Difficulty:", background=bg).grid(
            row=2, column=0, sticky="w", padx=10, pady=4)

        diff_var = ttk.Combobox(card, values=self.DIFFICULTIES,
                                state="disabled", width=14)
        diff_var.set("Beginner")
        diff_var.grid(row=2, column=1, sticky="w", padx=6, pady=4)

        custom_frame    = tk.Frame(card, bg=bg)
        custom_frame.grid(row=3, column=0, columnspan=3,
                          sticky="w", padx=10, pady=(2, 8))

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
            diff_val = self.p1_diff.get()
            is_ai    = self.p1_type_var.get() == "AI"
            mode     = self.p1_custom_mode.get()
            t_sl, d_sl, rb_t, rb_d = (self.p1_time_slider, self.p1_depth_slider,
                                       self.p1_rb_time,    self.p1_rb_depth)
        else:
            diff_val = self.p2_diff.get()
            is_ai    = self.p2_type_var.get() == "AI"
            mode     = self.p2_custom_mode.get()
            t_sl, d_sl, rb_t, rb_d = (self.p2_time_slider, self.p2_depth_slider,
                                       self.p2_rb_time,    self.p2_rb_depth)

        is_custom_abc  = is_ai and diff_val == "Custom-ABC"
        is_mcts_custom = is_ai and diff_val == "Custom-MCTS"
        show_time      = is_custom_abc or is_mcts_custom

        rb_t.config(state="normal" if is_custom_abc else "disabled")
        rb_d.config(state="normal" if is_custom_abc else "disabled")

        effective_mode = mode if is_custom_abc else "time"
        if effective_mode == "time" or is_mcts_custom:
            t_sl.grid(); d_sl.grid_remove()
        else:
            d_sl.grid(); t_sl.grid_remove()

        t_sl.config(state="normal" if show_time else "disabled")
        d_sl.config(state="normal" if (is_custom_abc and mode == "depth") else "disabled")

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------
    def launch(self):
        p1_is_ai = self.p1_type_var.get() == "AI"
        p2_is_ai = self.p2_type_var.get() == "AI"

        mode = "AVAI" if (p1_is_ai and p2_is_ai) else ("PVAI" if (p1_is_ai or p2_is_ai) else "PVP")

        def get_limits(is_ai, diff_cb, mode_var, t_sl, d_sl):
            if not is_ai:
                return None, None
            d = diff_cb.get()
            if d in ("Custom-MCTS", "Medium-MCTS", "Hard-MCTS"):
                return t_sl.get(), None
            if d == "Custom-ABC":
                return (t_sl.get(), None) if mode_var.get() == "time" else (None, d_sl.get())
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
            "loaded_game":    self._loaded_game,
        }
        self.root.destroy()
        self.on_launch_callback(settings)