# IA3leic07
======================================================
  ANNUVIN — HOW TO INSTALL, RUN, AND PLAY
======================================================


------------------------------------------------------
REQUIREMENTS
------------------------------------------------------

- Python 3.10 or newer
  Download from: https://www.python.org/downloads/

- tkinter (usually bundled with Python)
  If missing on Linux, run:  sudo apt install python3-tk

- Optional (for better sound):
  pip install pygame


------------------------------------------------------
INSTALLATION
------------------------------------------------------

1. Extract the ZIP archive anywhere on your computer.

2. Open a terminal (Command Prompt / PowerShell on Windows,
   Terminal on macOS/Linux).

3. Navigate to the "main" folder inside the project:

     cd path/to/IA3leic07-main/main


------------------------------------------------------
RUNNING THE GAME
------------------------------------------------------

From inside the "main" folder, run:

     python app.py

The launcher window will open where you can configure
the game before starting.

No compilation step is needed — Python runs directly.


------------------------------------------------------
LAUNCHER — GAME SETTINGS
------------------------------------------------------

Before each game you can configure both players:

  Type:
    Human  — a person plays using mouse clicks
    AI     — the computer plays automatically

  Difficulty (only active when Type is set to AI):

    Beginner     — mostly random; occasionally takes captures
    Medium-ABC   — minimax search, depth 2
    Hard-ABC     — iterative-deepening minimax, up to 5 seconds
    Medium-MCTS  — Monte Carlo Tree Search, 1.5 second budget
    Hard-MCTS    — MCTS with 5 second budget, stronger capture bias
    Custom-ABC   — minimax with a time or depth limit you set
    Custom-MCTS  — MCTS with a time limit you set

  For Custom modes, choose between:
    Time (s)  — AI thinks for N seconds per move (slider 1–15)
    Depth     — AI searches N half-moves deep (slider 1–8)
                (depth option is only available for Custom-ABC)

Game modes:
    Human vs Human  — two people play on the same computer
    Human vs AI     — one person vs the computer
    AI vs AI        — watch two AI players compete

Click START GAME when ready.

You can also load a previously saved game or game log
via File > Load Game… in the launcher menu.


------------------------------------------------------
HOW TO PLAY (IN-GAME)
------------------------------------------------------

The board is a hexagonal grid. Each player starts with
6 pieces:
  Black pieces — start at the bottom of the board
  White pieces — start at the top of the board

Black always moves first.

MOVING:
  1. Click one of your pieces to select it
     (it will be highlighted in yellow).
  2. Click a valid destination hex to move there.
  3. Click the selected piece again to deselect it.

CAPTURING:
  Move your piece onto a hex occupied by an enemy piece
  to capture and remove it from the board.

THE MASTERY RULE (move distance):
  Each player's maximum move distance equals:
    7 minus the number of pieces they currently have.
  So with 6 pieces your max distance is 1;
  with 5 pieces it is 2; and so on.
  The current distance is shown in the status bar.

WINNING CONDITIONS:
  A player wins if:
    - All opponent pieces are eliminated, OR
    - The opponent is reduced to 1 piece while you
      still have all 6 (Mastery victory).

DRAW:
  If 20 consecutive half-moves pass with no capture,
  the game ends in a draw.


------------------------------------------------------
IN-GAME MENU
------------------------------------------------------

File > New Game    — closes the current game and reopens
                     the launcher so you can choose new
                     settings for the next game.

File > Save Game   — saves the current board state to a
                     file in the Logs/ folder. You can
                     reload it later from the launcher.

File > Save Log    — saves a full move-by-move game log
                     to the Logs/ folder.

File > Exit        — quits the application.

Get Hint           — asks the AI for a suggested move
                     (only available on your turn when
                     you are playing as Human).


------------------------------------------------------
SAVED FILES
------------------------------------------------------

All saves and logs are written to a "Logs/" folder
created automatically in the "main/" directory.

  savegame_YYYYMMDD_HHMMSS.txt  — board snapshot
  game_YYYYMMDD_HHMMSS.txt      — full move log

Game logs are also saved automatically when a game ends.
Both file types can be reloaded via File > Load Game…
in the launcher.


------------------------------------------------------
SOUND
------------------------------------------------------

A move sound plays on each piece placement.
Sound can be adjusted or muted using the slider and
Mute checkbox in the launcher window.
If pygame is not installed, the game falls back to
system audio (aplay on Linux, afplay on macOS).


------------------------------------------------------
TROUBLESHOOTING
------------------------------------------------------

"No module named tkinter"
  → Install it: sudo apt install python3-tk  (Linux)
    On Windows/macOS tkinter is included by default.

"No module named pygame" (warning, not a crash)
  → Install with: pip install pygame
    The game works without it; sound quality may vary.

Game window does not open
  → Make sure you are running from the "main/" folder,
    not the root of the project.

======================================================
