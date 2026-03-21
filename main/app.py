import tkinter as tk
from gui import AnnuvinLauncher, AnnuvinGUI

def run_game(settings):
    game_root = tk.Tk()
    game_root.title("Annuvin Project")
    
    app = AnnuvinGUI(game_root)
    
    # 1. Apply settings immediately
    app.game.mode = settings["mode"]
    app.game.player1_type = settings["p1_type"]
    app.game.player2_type = settings["p2_type"]
    app.game.p1_difficulty = settings["p1_diff"]
    app.game.p2_difficulty = settings["p2_diff"]
    app.game.p1_time_limit = settings.get("p1_time_limit", None)
    app.game.p2_time_limit = settings.get("p2_time_limit", None)

    # 2. Set the initial status label correctly based on settings
    p_type = app.game.player1_type # Black always starts
    p_name = "Black"
    app.status_label.config(text=f"{p_name}'s Turn ({p_type})")
    
    # 3. Schedule the first AI check to happen 100ms AFTER the loop starts
    # This prevents the AI from moving before the window even appears
    game_root.after(100, app.check_for_ai_turn)
    
    game_root.mainloop()

if __name__ == "__main__":
    launcher_root = tk.Tk()
    # Pass 'run_game' as the second argument here
    launcher = AnnuvinLauncher(launcher_root, run_game)
    launcher_root.mainloop()