import random
import copy
import time


class AnnuvinAI:
    def __init__(self, game, difficulty="Beginner", time_limit=None, depth_limit=None, position_history=None):
        self.game = game
        self.difficulty       = difficulty
        self.time_limit       = time_limit
        self.depth_limit      = depth_limit
        # List of frozenset snapshots of past positions (last ~6 states).
        # Used to penalise moves that repeat a position we've already been in.
        self.position_history = position_history or []

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
    # Repetition detection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _state_snapshot(game):
        """Hashable representation of the board — used to detect repeated positions."""
        return (
            frozenset(game.pieces[1]),
            frozenset(game.pieces[2]),
            game.current_player
        )

    def _repetition_penalty(self, game, history):
        """Return a penalty score if this position has been seen in the history."""
        snapshot = self._state_snapshot(game)
        count = history.count(snapshot)
        if count == 0:
            return 0
        # First repeat: strong nudge. Second+: overwhelming deterrent.
        if count == 1:
            return -400
        return -1200 * count


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
                    deadline=deadline,
                    history=list(self.position_history)
                )
                if move is not None:
                    best_move = move
                depth += 1
                if depth > 10:
                    break
            except _TimeUp:
                break

        return best_move

    # ------------------------------------------------------------------
    # Fixed-depth minimax entry point
    # ------------------------------------------------------------------
    def get_minimax_move(self, depth, eval_fn):
        player_ai = self.game.current_player
        move = self._minimax_root(depth, player_ai, eval_fn=eval_fn,
                                  history=list(self.position_history))
        if move is None:
            moves = self.game.get_all_valid_moves(player_ai)
            return random.choice(moves)
        return move

    def _minimax_root(self, depth, player_ai, eval_fn, deadline=None, history=None):
        if history is None:
            history = []
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
            new_snapshot = self._state_snapshot(sim)
            new_history = history + [new_snapshot]

            value = self._minimax(
                sim, depth - 1, alpha, beta,
                player_ai, eval_fn, deadline, new_history
            )

            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, best_value)

        return best_move

    def _minimax(self, game, depth, alpha, beta, player_ai, eval_fn, deadline=None, history=None):
        if history is None:
            history = []
        if deadline and time.time() > deadline:
            raise _TimeUp()

        winner = game.check_winner()
        if winner is not None:
            return eval_fn(game, player_ai, history)

        if depth == 0:
            return self._quiescence(game, alpha, beta, player_ai, eval_fn, deadline, history)

        moves = self._order_moves(game.get_all_valid_moves(game.current_player), game)

        if game.current_player == player_ai:
            max_eval = -float("inf")
            for move in moves:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                new_snapshot = self._state_snapshot(sim)
                new_history = history + [new_snapshot]
                val = self._minimax(sim, depth - 1, alpha, beta, player_ai, eval_fn, deadline, new_history)
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
                new_snapshot = self._state_snapshot(sim)
                new_history = history + [new_snapshot]
                val = self._minimax(sim, depth - 1, alpha, beta, player_ai, eval_fn, deadline, new_history)
                min_eval = min(min_eval, val)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return min_eval

    # ------------------------------------------------------------------
    # Quiescence search — called at depth 0 instead of evaluating blindly.
    # Only searches captures until the position is quiet (no captures left).
    # Prevents the horizon effect where the AI stops mid-exchange.
    # ------------------------------------------------------------------
    def _quiescence(self, game, alpha, beta, player_ai, eval_fn, deadline=None, history=None, qdepth=0):
        if history is None:
            history = []
        if deadline and time.time() > deadline:
            raise _TimeUp()

        # "Stand-pat" score — what we get if we don't capture anything further
        stand_pat = eval_fn(game, player_ai, history)

        # Safety cap to prevent infinite quiescence in extreme positions
        if qdepth >= 4:
            return stand_pat

        winner = game.check_winner()
        if winner is not None:
            return stand_pat

        if game.current_player == player_ai:
            if stand_pat >= beta:
                return stand_pat          # beta cutoff
            alpha = max(alpha, stand_pat)

            # Only look at captures
            opponent = 2 if player_ai == 1 else 1
            all_moves = game.get_all_valid_moves(game.current_player)
            captures = [m for m in all_moves if m[1] in game.pieces[opponent]]

            if not captures:
                return stand_pat          # position is quiet

            for move in captures:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                new_snapshot = self._state_snapshot(sim)
                new_history = history + [new_snapshot]
                val = self._quiescence(sim, alpha, beta, player_ai, eval_fn, deadline, new_history, qdepth + 1)
                alpha = max(alpha, val)
                if alpha >= beta:
                    break
            return alpha

        else:
            if stand_pat <= alpha:
                return stand_pat          # alpha cutoff
            beta = min(beta, stand_pat)

            my_opponent = 2 if player_ai == 1 else 1
            all_moves = game.get_all_valid_moves(game.current_player)
            captures = [m for m in all_moves if m[1] in game.pieces[player_ai]]

            if not captures:
                return stand_pat

            for move in captures:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                new_snapshot = self._state_snapshot(sim)
                new_history = history + [new_snapshot]
                val = self._quiescence(sim, alpha, beta, player_ai, eval_fn, deadline, new_history, qdepth + 1)
                beta = min(beta, val)
                if alpha >= beta:
                    break
            return beta

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
    def _evaluate_medium(self, game, player_ai, history=None):
        if history is None:
            history = []
        opponent = 2 if player_ai == 1 else 1
        winner = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score = 0
        my_count  = len(game.pieces[player_ai])
        opp_count = len(game.pieces[opponent])

        score += (my_count - opp_count) * 1000
        score += self._capture_threats(game, player_ai) * 80

        return score + self._repetition_penalty(game, history)
    # Full positional play: material + mastery mechanic + mobility +
    # centrality + clustering + endgame awareness.
    # Understands the core Annuvin rules at a strategic level.
    # ------------------------------------------------------------------
    def _evaluate_hard(self, game, player_ai, history=None):
        if history is None:
            history = []
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

        # --- Material: dominant term, everything else is a tiebreaker ---
        score += (my_count - opp_count) * 1000

        # --- Immediate capture opportunities ---
        score += self._capture_threats(game, player_ai) * 80

        # --- Mobility ---
        score += self._mobility(game, player_ai) * 3
        score -= self._mobility(game, opponent) * 3

        # --- Endgame awareness ---
        if opp_count == 1 and my_count > 1:
            score += 800
        if my_count == 1 and opp_count > 1:
            score -= 800
        if opp_count == 2:
            score += 150
        if my_count == 2:
            score -= 150

        # --- Positional: small tiebreakers only ---
        for q, r in my_pieces:
            score += (3 - self._hex_dist_from_center(q, r)) * 3
        for q, r in opp_pieces:
            score -= (3 - self._hex_dist_from_center(q, r)) * 3

        score += self._clustering_score(my_pieces) * 2
        score -= self._clustering_score(opp_pieces) * 2

        return score + self._repetition_penalty(game, history)
class _TimeUp(Exception):
    pass