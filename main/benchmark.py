"""
benchmark.py — Automated AI vs AI tournament for Annuvin.

Runs every non-Custom AI against every other non-Custom AI.
Each matchup plays 10 games: 5 with P1 as Black, 5 with P2 as Black.
No GUI, no user interaction required.

Usage:
    python benchmark.py

Results are printed to the console and saved to Logs/benchmark_<timestamp>.txt
"""

import sys
import os
import copy
import time
import datetime
import itertools

# Make sure imports resolve relative to this file's directory
sys.path.insert(0, os.path.dirname(__file__))

from logic import AnnuvinGame
from engine import AnnuvinAI

# ─────────────────────────────────────────────────────────────────
# AI configurations to benchmark (no Custom variants)
# ─────────────────────────────────────────────────────────────────
AI_CONFIGS = [
    "Beginner",
    "Medium-ABC",
    "Hard-ABC",
    "Medium-MCTS",
    "Hard-MCTS",
]

GAMES_PER_SIDE = 5   # each AI plays N games as Black + N games as White
MAX_HALF_MOVES = 800  # safety cap — draw rule fires at 60 half-moves without capture


# ─────────────────────────────────────────────────────────────────
# Single game runner
# ─────────────────────────────────────────────────────────────────
def run_game(black_diff, white_diff):
    """
    Play one game. Black = player 1, White = player 2.
    Returns (winner, half_moves, duration_s)
      winner: 1 (Black), 2 (White), 0 (Draw)
    """
    game = AnnuvinGame()
    game.mode         = "AVAI"
    game.player1_type = "AI"
    game.player2_type = "AI"
    game.p1_difficulty = black_diff
    game.p2_difficulty = white_diff

    position_history = []
    half_moves = 0
    t0 = time.time()

    while half_moves < MAX_HALF_MOVES:
        winner = game.check_winner()
        if winner is not None:
            return winner, half_moves, time.time() - t0

        curr = game.current_player
        diff = game.p1_difficulty if curr == 1 else game.p2_difficulty

        ai = AnnuvinAI(game, difficulty=diff, position_history=list(position_history))
        move = ai.decide_move()

        if move is None:
            # No moves available — treat as loss for current player
            return (2 if curr == 1 else 1), half_moves, time.time() - t0

        snap = (frozenset(game.pieces[1]), frozenset(game.pieces[2]), game.current_player)
        position_history.append(snap)
        if len(position_history) > 16:
            position_history.pop(0)

        game.execute_move(*move)
        half_moves += 1

    # Safety cap hit — call it a draw
    return 0, half_moves, time.time() - t0


# ─────────────────────────────────────────────────────────────────
# Matchup runner
# ─────────────────────────────────────────────────────────────────
def run_matchup(ai_a, ai_b, games_per_side=GAMES_PER_SIDE):
    """
    Play games_per_side games with ai_a as Black and ai_b as White,
    then games_per_side games with ai_b as Black and ai_a as White.

    Returns a dict with full stats.
    """
    results = {
        "ai_a": ai_a,
        "ai_b": ai_b,
        "total": games_per_side * 2,
        "a_wins": 0,
        "b_wins": 0,
        "draws": 0,
        "total_moves": 0,
        "total_time": 0.0,
        "games": [],   # list of (black_diff, white_diff, winner, moves, duration)
    }

    print(f"\n  {'─'*60}")
    print(f"  {ai_a}  vs  {ai_b}")
    print(f"  {'─'*60}")

    # Phase 1: ai_a as Black, ai_b as White
    for i in range(games_per_side):
        winner, moves, dur = run_game(ai_a, ai_b)
        results["games"].append((ai_a, ai_b, winner, moves, dur))
        results["total_moves"] += moves
        results["total_time"]  += dur
        if winner == 1:
            results["a_wins"] += 1
            outcome = f"{ai_a} (Black) wins"
        elif winner == 2:
            results["b_wins"] += 1
            outcome = f"{ai_b} (White) wins"
        else:
            results["draws"] += 1
            outcome = "Draw"
        print(f"    Game {i+1:2d} [{ai_a} Black | {ai_b} White] → {outcome}  ({moves} moves, {dur:.1f}s)")

    # Phase 2: ai_b as Black, ai_a as White
    for i in range(games_per_side):
        winner, moves, dur = run_game(ai_b, ai_a)
        results["games"].append((ai_b, ai_a, winner, moves, dur))
        results["total_moves"] += moves
        results["total_time"]  += dur
        if winner == 1:
            results["b_wins"] += 1   # ai_b was Black (player 1) this time
            outcome = f"{ai_b} (Black) wins"
        elif winner == 2:
            results["a_wins"] += 1   # ai_a was White (player 2) this time
            outcome = f"{ai_a} (White) wins"
        else:
            results["draws"] += 1
            outcome = "Draw"
        print(f"    Game {games_per_side+i+1:2d} [{ai_b} Black | {ai_a} White] → {outcome}  ({moves} moves, {dur:.1f}s)")

    avg_moves = results["total_moves"] / results["total"]
    avg_time  = results["total_time"]  / results["total"]
    print(f"  Result: {ai_a} {results['a_wins']}W | {ai_b} {results['b_wins']}W | {results['draws']}D  "
          f"(avg {avg_moves:.1f} moves, {avg_time:.1f}s/game)")

    return results


# ─────────────────────────────────────────────────────────────────
# Report builder
# ─────────────────────────────────────────────────────────────────
def build_report(all_results, total_duration):
    lines = []
    lines.append("=" * 70)
    lines.append("ANNUVIN AI BENCHMARK REPORT")
    lines.append("=" * 70)
    lines.append(f"Date        : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"AIs tested  : {', '.join(AI_CONFIGS)}")
    lines.append(f"Games/matchup: {GAMES_PER_SIDE * 2}  ({GAMES_PER_SIDE} per side)")
    lines.append(f"Total time  : {total_duration:.1f}s")
    lines.append("")

    # ── Per-matchup table ──────────────────────────────────────────
    lines.append("─" * 70)
    lines.append(f"{'Matchup':<38} {'A-wins':>7} {'B-wins':>7} {'Draws':>6} {'Avg moves':>10} {'Avg time':>9}")
    lines.append("─" * 70)

    overall = {ai: {"wins": 0, "losses": 0, "draws": 0, "games": 0} for ai in AI_CONFIGS}

    for r in all_results:
        ai_a, ai_b = r["ai_a"], r["ai_b"]
        avg_m = r["total_moves"] / r["total"]
        avg_t = r["total_time"]  / r["total"]
        matchup_str = f"{ai_a}  vs  {ai_b}"
        lines.append(f"{matchup_str:<38} {r['a_wins']:>7} {r['b_wins']:>7} {r['draws']:>6} {avg_m:>10.1f} {avg_t:>8.1f}s")

        # Accumulate overall stats
        overall[ai_a]["wins"]   += r["a_wins"]
        overall[ai_a]["losses"] += r["b_wins"]
        overall[ai_a]["draws"]  += r["draws"]
        overall[ai_a]["games"]  += r["total"]

        overall[ai_b]["wins"]   += r["b_wins"]
        overall[ai_b]["losses"] += r["a_wins"]
        overall[ai_b]["draws"]  += r["draws"]
        overall[ai_b]["games"]  += r["total"]

    lines.append("─" * 70)
    lines.append("")

    # ── Overall standings ─────────────────────────────────────────
    lines.append("OVERALL STANDINGS")
    lines.append("─" * 70)
    lines.append(f"{'AI':<16} {'Games':>6} {'Wins':>6} {'Losses':>7} {'Draws':>6} {'Win %':>7}")
    lines.append("─" * 70)

    # Sort by win rate then win count
    ranking = sorted(
        overall.items(),
        key=lambda x: (x[1]["wins"] / x[1]["games"] if x[1]["games"] else 0, x[1]["wins"]),
        reverse=True
    )
    for ai, s in ranking:
        win_pct = 100.0 * s["wins"] / s["games"] if s["games"] else 0
        lines.append(f"{ai:<16} {s['games']:>6} {s['wins']:>6} {s['losses']:>7} {s['draws']:>6} {win_pct:>6.1f}%")

    lines.append("─" * 70)
    lines.append("")

    # ── Per-game log ──────────────────────────────────────────────
    lines.append("FULL GAME LOG")
    lines.append("─" * 70)
    lines.append(f"{'#':>4}  {'Black':<16} {'White':<16} {'Winner':<16} {'Moves':>6} {'Time':>7}")
    lines.append("─" * 70)

    game_num = 1
    for r in all_results:
        for black_diff, white_diff, winner, moves, dur in r["games"]:
            if winner == 1:
                winner_str = f"{black_diff} (Black)"
            elif winner == 2:
                winner_str = f"{white_diff} (White)"
            else:
                winner_str = "Draw"
            lines.append(f"{game_num:>4}  {black_diff:<16} {white_diff:<16} {winner_str:<16} {moves:>6} {dur:>6.1f}s")
            game_num += 1

    lines.append("─" * 70)
    lines.append("=" * 70)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    pairs = list(itertools.combinations(AI_CONFIGS, 2))
    total_games = len(pairs) * GAMES_PER_SIDE * 2

    print("=" * 62)
    print("  ANNUVIN BENCHMARK")
    print("=" * 62)
    print(f"  AIs      : {', '.join(AI_CONFIGS)}")
    print(f"  Matchups : {len(pairs)}")
    print(f"  Games    : {total_games} total ({GAMES_PER_SIDE}×2 per matchup)")
    print("=" * 62)

    t_start = time.time()
    all_results = []

    for ai_a, ai_b in pairs:
        result = run_matchup(ai_a, ai_b)
        all_results.append(result)

    total_duration = time.time() - t_start

    report = build_report(all_results, total_duration)

    print("\n")
    print(report)

    os.makedirs("Logs", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = os.path.join("Logs", f"benchmark_{timestamp}.txt")
    with open(filename, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {filename}")


if __name__ == "__main__":
    main()
