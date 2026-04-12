import random
import copy
import time
import math


# ==================================================================
# Difficulty routing reference
# ==================================================================
# "Beginner"    – mostly random, 50% chance of taking obvious capture
# "Medium-ABC"  – minimax depth 2, medium eval (material + threats)
# "Hard-ABC"    – iterative-deepening minimax (5 s), full positional eval
# "Medium-MCTS" – MCTS with 1.5 s budget + light rollout bias
# "Hard-MCTS"   – MCTS with 5 s budget + stronger capture bias + eval at cap
# "Custom-ABC"  – minimax: either fixed depth or iterative by time
# "Custom-MCTS" – MCTS: time budget from slider
# ==================================================================

class AnnuvinAI:
    def __init__(self, game, difficulty="Beginner",
                 time_limit=None, depth_limit=None, position_history=None):
        self.game             = game
        self.difficulty       = difficulty
        self.time_limit       = time_limit
        self.depth_limit      = depth_limit
        self.position_history = list(position_history) if position_history else []

    # ------------------------------------------------------------------
    # Main dispatcher
    # ------------------------------------------------------------------
    def decide_move(self):
        moves = self.game.get_all_valid_moves(self.game.current_player)
        if not moves:
            return None

        d = self.difficulty

        if d == "Beginner":
            return self._beginner_move(moves)

        # --- Alpha-Beta (Minimax) variants ---
        elif d == "Medium-ABC":
            return self.get_minimax_move(depth=2, eval_fn=self._evaluate_medium)
        elif d == "Hard-ABC":
            return self.get_iterative_deepening_move(time_limit=5)
        elif d == "Custom-ABC":
            if self.depth_limit is not None:
                return self.get_minimax_move(depth=self.depth_limit, eval_fn=self._evaluate_hard)
            else:
                return self.get_iterative_deepening_move(self.time_limit or 3)

        # --- MCTS variants ---
        elif d == "Medium-MCTS":
            return self.get_mcts_move(time_limit=1.5, capture_bias=0.7)
        elif d == "Hard-MCTS":
            return self.get_mcts_move(time_limit=5, capture_bias=0.85)
        elif d == "Custom-MCTS":
            tl = self.time_limit if self.time_limit is not None else 3
            return self.get_mcts_move(time_limit=tl, capture_bias=0.75)

        # Legacy / fallback
        elif d == "Medium":
            return self.get_minimax_move(depth=2, eval_fn=self._evaluate_medium)
        elif d == "Hard":
            return self.get_iterative_deepening_move(time_limit=5)

        return random.choice(moves)

    # ------------------------------------------------------------------
    # Move ordering: captures first (improves alpha-beta pruning)
    # ------------------------------------------------------------------
    def _order_moves(self, moves, game):
        opponent = 2 if game.current_player == 1 else 1
        captures, others = [], []
        for move in moves:
            if move[1] in game.pieces[opponent]:
                captures.append(move)
            else:
                others.append(move)
        return captures + others

    # ------------------------------------------------------------------
    # Beginner: mostly random, occasionally takes an obvious capture
    # ------------------------------------------------------------------
    def _beginner_move(self, moves):
        opponent = 2 if self.game.current_player == 1 else 1
        captures = [m for m in moves if m[1] in self.game.pieces[opponent]]
        if captures and random.random() < 0.5:
            return random.choice(captures)
        return random.choice(moves)

    # ------------------------------------------------------------------
    # Repetition detection
    # ------------------------------------------------------------------
    @staticmethod
    def _state_snapshot(game):
        return (
            frozenset(game.pieces[1]),
            frozenset(game.pieces[2]),
            game.current_player
        )

    def _repetition_penalty(self, game, history):
        snapshot = self._state_snapshot(game)
        count = history.count(snapshot)
        if count == 0:
            return 0
        if count == 1:
            return -400
        return -1200 * count

    # ==================================================================
    # MINIMAX / ALPHA-BETA
    # ==================================================================

    def get_iterative_deepening_move(self, time_limit):
        player_ai = self.game.current_player
        deadline  = time.time() + time_limit
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
        moves = self._order_moves(self.game.get_all_valid_moves(player_ai), self.game)

        best_move  = None
        best_value = -float("inf")
        alpha      = -float("inf")
        beta       = float("inf")

        for move in moves:
            if deadline and time.time() > deadline:
                raise _TimeUp()

            sim = copy.deepcopy(self.game)
            sim.execute_move(*move)
            new_history = history + [self._state_snapshot(sim)]

            value = self._minimax(sim, depth - 1, alpha, beta,
                                  player_ai, eval_fn, deadline, new_history)

            if value > best_value:
                best_value = value
                best_move  = move

            alpha = max(alpha, best_value)

        return best_move

    def _minimax(self, game, depth, alpha, beta, player_ai, eval_fn,
                 deadline=None, history=None):
        if history is None:
            history = []
        if deadline and time.time() > deadline:
            raise _TimeUp()

        winner = game.check_winner()
        if winner is not None:
            return eval_fn(game, player_ai, history)

        if depth == 0:
            return self._quiescence(game, alpha, beta, player_ai, eval_fn,
                                    deadline, history)

        moves = self._order_moves(game.get_all_valid_moves(game.current_player), game)

        if game.current_player == player_ai:
            max_eval = -float("inf")
            for move in moves:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val = self._minimax(sim, depth - 1, alpha, beta, player_ai, eval_fn,
                                    deadline, history + [self._state_snapshot(sim)])
                max_eval = max(max_eval, val)
                alpha    = max(alpha, val)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float("inf")
            for move in moves:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val = self._minimax(sim, depth - 1, alpha, beta, player_ai, eval_fn,
                                    deadline, history + [self._state_snapshot(sim)])
                min_eval = min(min_eval, val)
                beta     = min(beta, val)
                if beta <= alpha:
                    break
            return min_eval

    def _quiescence(self, game, alpha, beta, player_ai, eval_fn,
                    deadline=None, history=None, qdepth=0):
        if history is None:
            history = []
        if deadline and time.time() > deadline:
            raise _TimeUp()

        stand_pat = eval_fn(game, player_ai, history)

        if qdepth >= 4:
            return stand_pat

        winner = game.check_winner()
        if winner is not None:
            return stand_pat

        if game.current_player == player_ai:
            if stand_pat >= beta:
                return stand_pat
            alpha = max(alpha, stand_pat)

            opponent = 2 if player_ai == 1 else 1
            captures = [m for m in game.get_all_valid_moves(game.current_player)
                        if m[1] in game.pieces[opponent]]
            if not captures:
                return stand_pat

            for move in captures:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val   = self._quiescence(sim, alpha, beta, player_ai, eval_fn,
                                         deadline, history + [self._state_snapshot(sim)],
                                         qdepth + 1)
                alpha = max(alpha, val)
                if alpha >= beta:
                    break
            return alpha
        else:
            if stand_pat <= alpha:
                return stand_pat
            beta = min(beta, stand_pat)

            captures = [m for m in game.get_all_valid_moves(game.current_player)
                        if m[1] in game.pieces[player_ai]]
            if not captures:
                return stand_pat

            for move in captures:
                sim = copy.deepcopy(game)
                sim.execute_move(*move)
                val  = self._quiescence(sim, alpha, beta, player_ai, eval_fn,
                                        deadline, history + [self._state_snapshot(sim)],
                                        qdepth + 1)
                beta = min(beta, val)
                if alpha >= beta:
                    break
            return beta

    # ==================================================================
    # MONTE CARLO TREE SEARCH
    # ==================================================================

    def get_mcts_move(self, time_limit=3, capture_bias=0.75):
        """
        Run MCTS for `time_limit` seconds and return the best move.

        Parameters
        ----------
        time_limit   : seconds of thinking time
        capture_bias : probability of choosing a capture over a random move
                       during rollouts when a capture is available
        """
        player_ai = self.game.current_player
        root      = _MCTSNode(game=copy.deepcopy(self.game), parent=None, move=None,
                              player_ai=player_ai)
        deadline  = time.time() + time_limit

        while time.time() < deadline:
            node   = self._mcts_select(root)
            node   = self._mcts_expand(node, player_ai)
            result = self._mcts_simulate(node.game, player_ai,
                                         capture_bias=capture_bias)
            self._mcts_backpropagate(node, result)

        if not root.children:
            moves = self.game.get_all_valid_moves(player_ai)
            return random.choice(moves) if moves else None

        # Most-visited child = most robust choice
        best_child = max(root.children, key=lambda c: c.visits)
        return best_child.move

    # --- Selection ---
    def _mcts_select(self, node):
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node
            node = node.best_child(c=1.41)
        return node

    # --- Expansion: prefer captures ---
    def _mcts_expand(self, node, player_ai):
        if node.is_terminal():
            return node

        untried = node.untried_moves()
        # Prefer capturing moves during expansion
        opponent = 2 if node.game.current_player == 1 else 1
        captures = [m for m in untried if m[1] in node.game.pieces[opponent]]
        if captures and random.random() < 0.7:
            move = random.choice(captures)
        else:
            move = random.choice(untried)

        sim = copy.deepcopy(node.game)
        sim.execute_move(*move)

        child = _MCTSNode(game=sim, parent=node, move=move, player_ai=player_ai)
        node.children.append(child)
        return child

    # --- Simulation (rollout) ---
    def _mcts_simulate(self, game, player_ai, max_moves=20, capture_bias=0.75):
        """
        Short biased rollout followed by a material evaluation.

        Instead of playing out 60 random moves and hoping the result is
        meaningful, we play at most 20 moves (enough to resolve immediate
        exchanges) and then score the resulting position with a lightweight
        material + capture-threat heuristic. This gives MCTS a much cleaner
        signal than pure random play.
        """
        sim          = copy.deepcopy(game)
        moves_played = 0
        local_hist   = list(self.position_history)

        while moves_played < max_moves:
            winner = sim.check_winner()
            if winner is not None:
                if winner == 0:
                    return 0.5
                return 1.0 if winner == player_ai else 0.0

            all_moves = sim.get_all_valid_moves(sim.current_player)
            if not all_moves:
                return 0.5

            opponent = 2 if sim.current_player == 1 else 1

            # --- Repetition avoidance (no deepcopy) ---
            recent = set(local_hist[-6:]) if local_hist else set()
            non_repeating = [m for m in all_moves
                             if self._quick_snapshot(sim, m) not in recent]
            candidate_moves = non_repeating if non_repeating else all_moves

            # --- Capture bias ---
            captures = [m for m in candidate_moves if m[1] in sim.pieces[opponent]]
            if captures and random.random() < capture_bias:
                move = random.choice(captures)
            else:
                move = random.choice(candidate_moves)

            sim.execute_move(*move)
            local_hist.append(self._state_snapshot(sim))
            moves_played += 1

        # --- Evaluate position at rollout end ---
        return self._mcts_evaluate(sim, player_ai)

    @staticmethod
    def _quick_snapshot(game, move):
        """Snapshot after a hypothetical move without deepcopy — for repetition avoidance."""
        p   = game.current_player
        opp = 2 if p == 1 else 1
        start, end = move
        p1 = set(game.pieces[1])
        p2 = set(game.pieces[2])
        if p == 1:
            p1.discard(start); p1.add(end); p2.discard(end)
        else:
            p2.discard(start); p2.add(end); p1.discard(end)
        return (frozenset(p1), frozenset(p2), opp)

    def _mcts_evaluate(self, game, player_ai):
        """
        Lightweight evaluation for MCTS rollout termination.
        Returns a value in [0, 1] from player_ai's perspective.
        """
        opponent = 2 if player_ai == 1 else 1
        winner   = game.check_winner()
        if winner == player_ai: return 1.0
        if winner == opponent:  return 0.0
        if winner == 0:         return 0.5

        my_count  = len(game.pieces[player_ai])
        opp_count = len(game.pieces[opponent])

        score  = (my_count - opp_count) * 100
        score += self._capture_threats(game, player_ai) * 20
        score -= self._capture_threats(game, opponent)  * 20

        for q, r in game.pieces[player_ai]:
            score += (3 - self._hex_dist_from_center(q, r)) * 5
        for q, r in game.pieces[opponent]:
            score -= (3 - self._hex_dist_from_center(q, r)) * 5

        # Normalise to [0, 1] — max swing is roughly ±800
        return max(0.0, min(1.0, (score + 800) / 1600))

    # --- Backpropagation ---
    @staticmethod
    def _mcts_backpropagate(node, result):
        """
        result is from player_ai's perspective: 1.0 = AI wins, 0.0 = AI loses.
        We store it consistently (no flipping) in every node.
        UCB1 in best_child() handles the perspective flip based on whose turn it is.
        """
        while node is not None:
            node.visits += 1
            node.wins   += result
            node = node.parent

    # ==================================================================
    # EVALUATION FUNCTIONS  (used by Minimax)
    # ==================================================================

    def _hex_dist_from_center(self, q, r):
        return (abs(q) + abs(r) + abs(q + r)) // 2

    def _capture_threats(self, game, player):
        opponent = 2 if player == 1 else 1
        my_moves = game.get_all_valid_moves(player)
        return len({end for _, end in my_moves if end in game.pieces[opponent]})

    def _mobility(self, game, player):
        return len(game.get_all_valid_moves(player))

    def _clustering_score(self, pieces):
        if len(pieces) <= 1:
            return 0
        total = 0
        for i, (q1, r1) in enumerate(pieces):
            for q2, r2 in pieces[i + 1:]:
                dist = (abs(q1-q2) + abs(q1+r1-q2-r2) + abs(r1-r2)) // 2
                if dist <= 2:
                    total += 1
        return total

    # Medium eval — material + immediate capture threats only
    def _evaluate_medium(self, game, player_ai, history=None):
        if history is None:
            history = []
        opponent = 2 if player_ai == 1 else 1
        winner   = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score  = (len(game.pieces[player_ai]) - len(game.pieces[opponent])) * 1000
        score += self._capture_threats(game, player_ai) * 80
        return score + self._repetition_penalty(game, history)

    # Hard eval — full positional heuristic with mastery/endgame awareness
    def _evaluate_hard(self, game, player_ai, history=None):
        if history is None:
            history = []
        opponent   = 2 if player_ai == 1 else 1
        winner     = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        my_pieces  = game.pieces[player_ai]
        opp_pieces = game.pieces[opponent]
        my_count   = len(my_pieces)
        opp_count  = len(opp_pieces)

        score  = (my_count - opp_count) * 1000
        score += self._capture_threats(game, player_ai) * 80
        score += self._mobility(game, player_ai) * 3
        score -= self._mobility(game, opponent)  * 3

        if opp_count == 1 and my_count > 1:  score += 800
        if my_count  == 1 and opp_count > 1: score -= 800
        if opp_count == 2:                    score += 150
        if my_count  == 2:                    score -= 150

        for q, r in my_pieces:
            score += (3 - self._hex_dist_from_center(q, r)) * 3
        for q, r in opp_pieces:
            score -= (3 - self._hex_dist_from_center(q, r)) * 3

        score += self._clustering_score(my_pieces)  * 2
        score -= self._clustering_score(opp_pieces) * 2

        return score + self._repetition_penalty(game, history)


# ==================================================================
# MCTS Node
# ==================================================================

class _MCTSNode:
    __slots__ = ("game", "parent", "move", "children", "visits", "wins", "_untried", "player_ai")

    def __init__(self, game, parent, move, player_ai=None):
        self.game      = game
        self.parent    = parent
        self.move      = move
        self.children  = []
        self.visits    = 0
        self.wins      = 0.0
        self._untried  = None
        # player_ai: the AI player number (1 or 2) — used to orient UCB1
        self.player_ai = player_ai

    def is_terminal(self):
        return self.game.check_winner() is not None

    def untried_moves(self):
        if self._untried is None:
            self._untried = list(
                self.game.get_all_valid_moves(self.game.current_player)
            )
        tried = {c.move for c in self.children}
        return [m for m in self._untried if m not in tried]

    def is_fully_expanded(self):
        return len(self.untried_moves()) == 0

    def best_child(self, c=1.41):
        """
        UCB1 from the perspective of the player who is TO MOVE at this node.
        wins is stored from player_ai's perspective (1.0 = AI wins).
        When it is player_ai's turn we maximise wins/visits.
        When it is the opponent's turn we maximise (1 - wins/visits).
        """
        log_parent = math.log(self.visits) if self.visits > 0 else 0
        is_ai_turn = (self.game.current_player == self.player_ai)

        def ucb1(child):
            if child.visits == 0:
                return float("inf")
            exploitation = child.wins / child.visits
            if not is_ai_turn:
                exploitation = 1.0 - exploitation
            return exploitation + c * math.sqrt(log_parent / child.visits)

        return max(self.children, key=ucb1)


class _TimeUp(Exception):
    pass