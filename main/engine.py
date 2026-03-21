import random
import copy
import time


class AnnuvinAI:
    def __init__(self, game, difficulty="Beginner", time_limit=None):
        self.game = game
        self.difficulty = difficulty
        # time_limit in seconds; overrides depth-based mode if set
        self.time_limit = time_limit

    def decide_move(self):
        moves = self.game.get_all_valid_moves(self.game.current_player)
        if not moves:
            return None

        # Time-based mode: iterative deepening until time runs out
        if self.time_limit is not None:
            return self.get_iterative_deepening_move(self.time_limit)

        # Difficulty-based mode
        if self.difficulty == "Beginner":
            return self._beginner_move(moves)
        elif self.difficulty == "Medium":
            return self.get_minimax_move(depth=2, eval_fn=self._evaluate_medium)
        elif self.difficulty == "Hard":
            return self.get_minimax_move(depth=4, eval_fn=self._evaluate_hard)

        return random.choice(moves)

    # ------------------------------------------------------------------
    # Move ordering: try captures first (improves alpha-beta pruning)
    # ------------------------------------------------------------------
    def _order_moves(self, moves, game):
        opponent = 2 if game.current_player == 1 else 1
        captures, others = [], []
        for move in moves:
            start, end = move
            if end in game.pieces[opponent]:
                captures.append(move)
            else:
                others.append(move)
        return captures + others

    # ------------------------------------------------------------------
    # Beginner: mostly random, but occasionally takes an obvious capture
    # ------------------------------------------------------------------
    def _beginner_move(self, moves):
        opponent = 2 if self.game.current_player == 1 else 1
        captures = [m for m in moves if m[1] in self.game.pieces[opponent]]
        if captures and random.random() < 0.5:   # only 50% of the time
            return random.choice(captures)
        return random.choice(moves)

    # ------------------------------------------------------------------
    # Iterative deepening (used by the time slider)
    # ------------------------------------------------------------------
    def get_iterative_deepening_move(self, time_limit):
        player_ai = self.game.current_player
        deadline = time.time() + time_limit
        best_move = random.choice(self.game.get_all_valid_moves(player_ai))

        depth = 1
        while time.time() < deadline:
            try:
                move = self._minimax_root(
                    depth, player_ai,
                    eval_fn=self._evaluate_hard,
                    deadline=deadline
                )
                if move is not None:
                    best_move = move
                depth += 1
                if depth > 10:   # safety cap
                    break
            except _TimeUp:
                break

        return best_move

    # ------------------------------------------------------------------
    # Fixed-depth minimax entry point
    # ------------------------------------------------------------------
    def get_minimax_move(self, depth, eval_fn):
        player_ai = self.game.current_player
        move = self._minimax_root(depth, player_ai, eval_fn=eval_fn)
        if move is None:
            moves = self.game.get_all_valid_moves(player_ai)
            return random.choice(moves)
        return move

    def _minimax_root(self, depth, player_ai, eval_fn, deadline=None):
        moves = self.game.get_all_valid_moves(player_ai)
        moves = self._order_moves(moves, self.game)

        best_move = None
        best_value = -float("inf")
        alpha = -float("inf")
        beta = float("inf")

        for move in moves:
            if deadline and time.time() > deadline:
                raise _TimeUp()

            sim = copy.deepcopy(self.game)
            sim.execute_move(*move)

            value = self._minimax(
                sim, depth - 1, alpha, beta,
                False, player_ai, eval_fn, deadline
            )

            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, best_value)

        return best_move

    def _minimax(self, game, depth, alpha, beta, maximizing, player_ai, eval_fn, deadline=None):
        if deadline and time.time() > deadline:
            raise _TimeUp()

        winner = game.check_winner()
        if depth == 0 or winner is not None:
            return eval_fn(game, player_ai)

        moves = self._order_moves(game.get_all_valid_moves(game.current_player), game)

        if maximizing:
            max_eval = -float("inf")
            for move in moves:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val = self._minimax(sim, depth - 1, alpha, beta, False, player_ai, eval_fn, deadline)
                max_eval = max(max_eval, val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float("inf")
            for move in moves:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val = self._minimax(sim, depth - 1, alpha, beta, True, player_ai, eval_fn, deadline)
                min_eval = min(min_eval, val)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return min_eval

    # ==================================================================
    # EVALUATION FUNCTIONS
    # ==================================================================

    def _hex_dist_from_center(self, q, r):
        return (abs(q) + abs(r) + abs(q + r)) // 2

    def _pieces_at_risk(self, game, player):
        """Count own pieces that can be captured by the opponent next move."""
        opponent = 2 if player == 1 else 1
        opp_moves = game.get_all_valid_moves(opponent)
        threatened = set(end for _, end in opp_moves if end in game.pieces[player])
        return len(threatened)

    def _capture_threats(self, game, player):
        """Count opponent pieces we can capture right now."""
        opponent = 2 if player == 1 else 1
        my_moves = game.get_all_valid_moves(player)
        capturable = set(end for _, end in my_moves if end in game.pieces[opponent])
        return len(capturable)

    def _mobility(self, game, player):
        """Number of legal moves available."""
        return len(game.get_all_valid_moves(player))

    def _clustering_score(self, pieces):
        """Reward pieces that are close to friendly pieces (mutual protection)."""
        if len(pieces) <= 1:
            return 0
        total = 0
        for i, (q1, r1) in enumerate(pieces):
            for q2, r2 in pieces[i + 1:]:
                dist = (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2
                if dist <= 2:
                    total += 1
        return total

    # ------------------------------------------------------------------
    # Medium heuristic: material + threats + mobility
    # Understands captures and danger but not deep positional play
    # ------------------------------------------------------------------
    def _evaluate_medium(self, game, player_ai):
        opponent = 2 if player_ai == 1 else 1
        winner = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score = 0
        my_count = len(game.pieces[player_ai])
        opp_count = len(game.pieces[opponent])

        # Material
        score += (my_count - opp_count) * 100

        # Mastery distance (the core Annuvin mechanic)
        score += game.get_max_distance(player_ai) * 10
        score -= game.get_max_distance(opponent) * 10

        # Immediate capture opportunities and danger
        score += self._capture_threats(game, player_ai) * 30
        score -= self._pieces_at_risk(game, player_ai) * 25

        # Mobility
        score += self._mobility(game, player_ai) * 2
        score -= self._mobility(game, opponent) * 2

        return score

    # ------------------------------------------------------------------
    # Hard heuristic: medium + positional + endgame awareness + clustering
    # ------------------------------------------------------------------
    def _evaluate_hard(self, game, player_ai):
        opponent = 2 if player_ai == 1 else 1
        winner = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score = 0
        my_pieces = game.pieces[player_ai]
        opp_pieces = game.pieces[opponent]
        my_count = len(my_pieces)
        opp_count = len(opp_pieces)

        # Material
        score += (my_count - opp_count) * 100

        # Mastery distance (crucial: more range = more power)
        my_dist = game.get_max_distance(player_ai)
        opp_dist = game.get_max_distance(opponent)
        score += (my_dist - opp_dist) * 15

        # Capture threats and danger
        score += self._capture_threats(game, player_ai) * 35
        score -= self._pieces_at_risk(game, player_ai) * 30

        # Mobility
        score += self._mobility(game, player_ai) * 3
        score -= self._mobility(game, opponent) * 3

        # Endgame awareness: mastery win/loss condition
        if opp_count == 1 and my_count > 1:
            score += 500   # opponent is about to hit mastery loss
        if my_count == 1 and opp_count > 1:
            score -= 500   # we are about to hit mastery loss

        # Centrality: central pieces have more options
        for q, r in my_pieces:
            score += (3 - self._hex_dist_from_center(q, r)) * 4
        for q, r in opp_pieces:
            score -= (3 - self._hex_dist_from_center(q, r)) * 4

        # Clustering: pieces near friends are safer
        score += self._clustering_score(my_pieces) * 3
        score -= self._clustering_score(opp_pieces) * 3

        return score


# ------------------------------------------------------------------
# Internal exception used to interrupt iterative deepening
# ------------------------------------------------------------------
class _TimeUp(Exception):
    pass