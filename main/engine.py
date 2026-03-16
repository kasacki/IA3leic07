import random
import copy

class AnnuvinAI:
    def __init__(self, game, difficulty="Beginner"):
        self.game = game
        self.difficulty = difficulty

    def decide_move(self):
        moves = self.game.get_all_valid_moves(self.game.current_player)

        if not moves:
            return None

        if self.difficulty == "Beginner":
            return random.choice(moves)

        elif self.difficulty == "Medium":
            return self.get_minimax_move(depth=2)

        elif self.difficulty == "Hard":
            return self.get_minimax_move(depth=4)

        return random.choice(moves)

    def get_minimax_move(self, depth):

        player_ai = self.game.current_player
        moves = self.game.get_all_valid_moves(player_ai)

        best_move = None
        best_value = -float("inf")

        alpha = -float("inf")
        beta = float("inf")

        for move in moves:

            simulated_game = copy.deepcopy(self.game)

            simulated_game.execute_move(*move)

            value = self.minimax(
                simulated_game,
                depth - 1,
                alpha,
                beta,
                False,
                player_ai
            )

            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, best_value)

        return best_move if best_move else random.choice(moves)

    def minimax(self, game, depth, alpha, beta, maximizing, player_ai):

        winner = game.check_winner()

        if depth == 0 or winner is not None:
            return self.evaluate_board(game, player_ai)

        current_player = game.current_player

        if maximizing:

            max_eval = -float("inf")

            for move in game.get_all_valid_moves(current_player):

                sim = copy.deepcopy(game)
                sim.execute_move(*move)

                eval = self.minimax(sim, depth-1, alpha, beta, False, player_ai)

                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)

                if beta <= alpha:
                    break

            return max_eval

        else:

            min_eval = float("inf")

            for move in game.get_all_valid_moves(current_player):

                sim = copy.deepcopy(game)
                sim.execute_move(*move)

                eval = self.minimax(sim, depth-1, alpha, beta, True, player_ai)

                min_eval = min(min_eval, eval)
                beta = min(beta, eval)

                if beta <= alpha:
                    break

            return min_eval


    def evaluate_board(self, board, player_ai):

        opponent = 2 if player_ai == 1 else 1

        winner = board.check_winner()

        if winner == player_ai:
            return 10000

        if winner == opponent:
            return -10000

        score = 0

        # MATERIAL (najważniejsze)
        score += len(board.pieces[player_ai]) * 100
        score -= len(board.pieces[opponent]) * 100

        # POZYCJA (centrum planszy)
        for q, r in board.pieces[player_ai]:

            dist = (abs(q) + abs(r) + abs(q+r)) / 2

            score += (3 - dist) * 5

        for q, r in board.pieces[opponent]:

            dist = (abs(q) + abs(r) + abs(q+r)) / 2

            score -= (3 - dist) * 5

        return score