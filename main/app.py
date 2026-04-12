import tkinter as tk
from gui import AnnuvinLauncher, AnnuvinGUI
from logic import AnnuvinGame


def open_launcher():
    launcher_root = tk.Tk()
    launcher = AnnuvinLauncher(launcher_root, run_game)
    launcher_root.mainloop()


def run_game(settings):
    game_root = tk.Tk()
    game_root.title("Annuvin")

    app = AnnuvinGUI(game_root, on_new_game=open_launcher)

    # --- Apply player settings ---
    app.game.mode           = settings["mode"]
    app.game.player1_type   = settings["p1_type"]
    app.game.player2_type   = settings["p2_type"]
    app.game.p1_difficulty  = settings["p1_diff"]
    app.game.p2_difficulty  = settings["p2_diff"]
    app.game.p1_time_limit  = settings.get("p1_time_limit",  None)
    app.game.p2_time_limit  = settings.get("p2_time_limit",  None)
    app.game.p1_depth_limit = settings.get("p1_depth_limit", None)
    app.game.p2_depth_limit = settings.get("p2_depth_limit", None)

    # --- Restore a loaded game if one was provided ---
    loaded = settings.get("loaded_game")
    if loaded:
        if loaded.get("format") == "log" and "_game_obj" in loaded:
            # Game-log: board already replayed in the launcher, just swap it in
            replayed_game = loaded["_game_obj"]
            replayed_game.player1_type   = settings["p1_type"]
            replayed_game.player2_type   = settings["p2_type"]
            replayed_game.p1_difficulty  = settings["p1_diff"]
            replayed_game.p2_difficulty  = settings["p2_diff"]
            replayed_game.p1_time_limit  = settings.get("p1_time_limit",  None)
            replayed_game.p2_time_limit  = settings.get("p2_time_limit",  None)
            replayed_game.p1_depth_limit = settings.get("p1_depth_limit", None)
            replayed_game.p2_depth_limit = settings.get("p2_depth_limit", None)
            app.game = replayed_game

            # Rebuild position history from the replayed moves
            g_temp = AnnuvinGame()
            for start, end in loaded.get("moves", []):
                if g_temp.check_winner() is not None:
                    break
                g_temp.execute_move(start, end)
                snap = (frozenset(g_temp.pieces[1]),
                        frozenset(g_temp.pieces[2]),
                        g_temp.current_player)
                app.position_history.append(snap)
            app.position_history = app.position_history[-16:]

            # Show last move shadow
            moves = loaded.get("moves", [])
            app.last_move = moves[-1] if moves else None

        elif loaded.get("format") == "save":
            # Savegame snapshot: restore raw board state
            import ast
            app.game.current_player      = loaded["current_player"]
            app.game.pieces[1]           = loaded["pieces1"]
            app.game.pieces[2]           = loaded["pieces2"]
            app.game.moves_since_capture = loaded["moves_since_capture"]
            app.last_move = None

    # --- Update status label ---
    app.draw_board()
    p_name = "Black" if app.game.current_player == 1 else "White"
    curr_type = (app.game.player1_type if app.game.current_player == 1
                 else app.game.player2_type)

    winner = app.game.check_winner()
    if winner is not None:
        app._game_over = True
        if winner == 0:
            app.status_label.config(text="Game over — Draw")
        else:
            w_name = "Black" if winner == 1 else "White"
            app.status_label.config(text=f"Game over — {w_name} wins")
    else:
        dist = app.game.get_max_distance(app.game.current_player)
        if curr_type == "Human":
            app.status_label.config(text=f"{p_name}'s Turn (Distance: {dist})")
        else:
            app.status_label.config(text=f"{p_name}'s Turn (AI Thinking...)")
        game_root.after(300, app.check_for_ai_turn)

    game_root.mainloop()


if __name__ == "__main__":
    open_launcher()
