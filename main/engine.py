import random
import copy
import time


class AnnuvinAI:
    def __init__(self, game, difficulty="Beginner", time_limit=None, depth_limit=None):
        self.game = game
        self.difficulty  = difficulty
        self.time_limit  = time_limit
        self.depth_limit = depth_limit

    def decide_move(self):
        moves = self.game.get_all_valid_moves(self.game.current_player)
        if not moves:
            return None

        if self.difficulty == "Beginner":
            return self._beginner_move(moves)
        elif self.difficulty == "Medium":
            return self.get_minimax_move(depth=1, eval_fn=self._evaluate_medium)
        elif self.difficulty == "Hard":
            return self.get_iterative_deepening_move(time_limit=5)
        elif self.difficulty == "Custom":
            if self.depth_limit is not None:
                return self.get_minimax_move(depth=self.depth_limit, eval_fn=self._evaluate_hard)
            else:
                return self.get_iterative_deepening_move(self.time_limit or 3)

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
    # Iterative deepening — used by Hard (5s cap) and Custom (slider)
    # Always uses the hard evaluation function.
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
                player_ai, eval_fn, deadline
            )

            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, best_value)

        return best_move

    def _minimax(self, game, depth, alpha, beta, player_ai, eval_fn, deadline=None):
        if deadline and time.time() > deadline:
            raise _TimeUp()

        winner = game.check_winner()
        if depth == 0 or winner is not None:
            return eval_fn(game, player_ai)

        moves = self._order_moves(game.get_all_valid_moves(game.current_player), game)

        # Maximizing when it's the AI's turn, minimizing when it's the opponent's
        if game.current_player == player_ai:
            max_eval = -float("inf")
            for move in moves:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val = self._minimax(sim, depth - 1, alpha, beta, player_ai, eval_fn, deadline)
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
                val = self._minimax(sim, depth - 1, alpha, beta, player_ai, eval_fn, deadline)
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
    # Medium heuristic — depth 2
    # Pure tactics: only cares about piece count and immediate captures/danger.
    # Has no concept of position, mobility, or the endgame mastery condition.
    # Plays reasonable moves but is blind to strategy.
    # ------------------------------------------------------------------
    def _evaluate_medium(self, game, player_ai):
        opponent = 2 if player_ai == 1 else 1
        winner = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score = 0
        my_count  = len(game.pieces[player_ai])
        opp_count = len(game.pieces[opponent])

        # Material is the dominant factor
        score += (my_count - opp_count) * 200

        # Aware of immediate captures and immediate danger, nothing more
        score += self._capture_threats(game, player_ai) * 40
        score -= self._pieces_at_risk(game, player_ai) * 35

        return score

    # ------------------------------------------------------------------
    # Hard heuristic — depth 5
    # Full positional play: material + mastery mechanic + mobility +
    # centrality + clustering + endgame awareness.
    # Understands the core Annuvin rules at a strategic level.
    # ------------------------------------------------------------------
    def _evaluate_hard(self, game, player_ai):
        opponent = 2 if player_ai == 1 else 1
        winner = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score = 0
        my_pieces  = game.pieces[player_ai]
        opp_pieces = game.pieces[opponent]
        my_count   = len(my_pieces)
        opp_count  = len(opp_pieces)

        # --- Material ---
        score += (my_count - opp_count) * 200

        # --- Mastery distance: the core Annuvin mechanic ---
        # Fewer pieces = longer reach. Hard understands this as both a
        # weapon (force opponent to 1 piece) and a danger (avoid being
        # reduced to 1 piece yourself while opponent still has many).
        my_dist  = game.get_max_distance(player_ai)
        opp_dist = game.get_max_distance(opponent)
        score += (my_dist - opp_dist) * 20

        # --- Immediate tactics ---
        score += self._capture_threats(game, player_ai) * 50
        score -= self._pieces_at_risk(game, player_ai) * 45

        # --- Mobility: more options = more control ---
        score += self._mobility(game, player_ai) * 4
        score -= self._mobility(game, opponent) * 4

        # --- Endgame: explicitly value/fear the mastery win condition ---
        # Opponent is one piece away from mastery loss
        if opp_count == 1 and my_count > 1:
            score += 800
        # We are one piece away from mastery loss
        if my_count == 1 and opp_count > 1:
            score -= 800
        # Opponent dangerously close (2 pieces left)
        if opp_count == 2:
            score += 200
        if my_count == 2:
            score -= 200

        # --- Centrality: central pieces threaten more hexes ---
        for q, r in my_pieces:
            score += (3 - self._hex_dist_from_center(q, r)) * 6
        for q, r in opp_pieces:
            score -= (3 - self._hex_dist_from_center(q, r)) * 6

        # --- Clustering: pieces near friends are harder to pick off ---
        score += self._clustering_score(my_pieces) * 5
        score -= self._clustering_score(opp_pieces) * 5

        return score


# ------------------------------------------------------------------
# Internal exception used to interrupt iterative deepening
# ------------------------------------------------------------------
class _TimeUp(Exception):
    pass