import random
import copy

class AnnuvinAI:
    def __init__(self, game, difficulty="Beginner"):
        self.game = game
        self.difficulty = difficulty

    def decide_move(self):
        # This now calls the function we just added to logic.py
        moves = self.game.get_all_valid_moves(self.game.current_player)
        
        if not moves:
            return None

        if self.difficulty == "Beginner":
            return random.choice(moves)
        
        # Placeholder for Medium/Hard
        return random.choice(moves)

    def get_beginner_move(self, moves):
        """Randomly picks a move from available legal moves."""
        return random.choice(moves)

    def get_medium_move(self, moves):
        """Placeholder: Shallow Minimax (Depth 2)."""
        # For now, it just acts like Beginner
        return random.choice(moves)

    def get_hard_move(self, moves):
        """Placeholder: Deep Minimax with Alpha-Beta Pruning (Depth 4+)."""
        # For now, it just acts like Beginner
        return random.choice(moves)
    
    def evaluate_board(self, board):
        """Returns a score: higher is better for Black, lower better for White."""
        # 1. Check for Terminal States (Wins)
        winner = board.check_winner()
        if winner == 1: return 1000  # Black won
        if winner == 2: return -1000 # White won

        score = 0
        
        # 2. Material Advantage (Value of pieces)
        # Each piece is worth 10 points
        score += len(board.pieces[1]) * 10
        score -= len(board.pieces[2]) * 10

        # 3. Position (Distance to center)
        # In Annuvin, pieces are safer/stronger near the center (0,0)
        for q, r in board.pieces[1]:
            dist = (abs(q) + abs(r) + abs(q + r)) / 2
            score += (3 - dist) # Bonus for being close to (0,0)
            
        for q, r in board.pieces[2]:
            dist = (abs(q) + abs(r) + abs(q + r)) / 2
            score -= (3 - dist)

        return score