import tkinter as tk
from gui import AnnuvinLauncher, AnnuvinGUI

def run_game(settings):
    game_root = tk.Tk()
    game_root.title("Annuvin Project")
    
    app = AnnuvinGUI(game_root)
    # Apply the settings
    app.game.mode = settings["mode"]
    app.game.player1_type = settings["p1_type"]
    app.game.player2_type = settings["p2_type"]
    app.game.p1_difficulty = settings["p1_diff"]
    app.game.p2_difficulty = settings["p2_diff"]
    
    p_name = "Black" if app.game.current_player == 1 else "White"
    app.status_label.config(text=f"{p_name}'s Turn ({settings['mode']})")
    
    game_root.mainloop()

if __name__ == "__main__":
    launcher_root = tk.Tk()
    # Pass 'run_game' as the second argument here
    launcher = AnnuvinLauncher(launcher_root, run_game)
    launcher_root.mainloop()