import random
import copy
import time
import math


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
        elif self.difficulty == "MCTS":
            tl = self.time_limit if self.time_limit is not None else 3
            return self.get_mcts_move(time_limit=tl)
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
            all_moves = game.get_all_valid_moves(game.current_player)
            captures = [m for m in all_moves if m[1] in game.pieces[opponent]]

            if not captures:
                return stand_pat

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
                return stand_pat
            beta = min(beta, stand_pat)

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
    # MONTE CARLO TREE SEARCH
    # ==================================================================

    def get_mcts_move(self, time_limit=3):
        """
        Run MCTS for up to `time_limit` seconds and return the best move found.

        Algorithm outline:
          1. SELECT   – walk the tree using UCB1 until reaching an unexpanded or terminal node.
          2. EXPAND   – create one new child for an untried move.
          3. SIMULATE – play out the game with a biased random rollout.
          4. BACKPROP – update visit/win counts up the path to the root.

        After the time budget is exhausted the child with the most visits is chosen
        (the "most robust" child — less sensitive to outlier simulations than
        choosing purely by win rate).
        """
        player_ai = self.game.current_player
        root = _MCTSNode(game=copy.deepcopy(self.game), parent=None, move=None)
        deadline = time.time() + time_limit

        while time.time() < deadline:
            # 1. Selection
            node = self._mcts_select(root)
            # 2. Expansion
            node = self._mcts_expand(node)
            # 3. Simulation
            result = self._mcts_simulate(node.game, player_ai)
            # 4. Backpropagation
            self._mcts_backpropagate(node, result)

        if not root.children:
            # Fallback: no simulations ran (e.g. trivial position)
            moves = self.game.get_all_valid_moves(player_ai)
            return random.choice(moves) if moves else None

        best_child = max(root.children, key=lambda c: c.visits)
        return best_child.move

    def _mcts_select(self, node):
        """
        Tree policy: descend the tree using UCB1 until we reach a node that is
        not yet fully expanded, or a terminal node.
        """
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node
            node = node.best_child(c=1.41)
        return node

    def _mcts_expand(self, node):
        """
        Expansion policy: pick one untried move at random, add it as a child.
        Returns the new child, or the node itself if it is terminal.
        """
        if node.is_terminal():
            return node

        untried = node.untried_moves()
        move = random.choice(untried)

        sim = copy.deepcopy(node.game)
        sim.execute_move(*move)

        child = _MCTSNode(game=sim, parent=node, move=move)
        node.children.append(child)
        return child

    def _mcts_simulate(self, game, player_ai, max_moves=80):
        """
        Default policy (rollout): play randomly until the game ends or the move
        cap is reached, then score the result from player_ai's perspective.

        A light bias is applied: captures are preferred ~60 % of the time when
        available. This dramatically improves rollout quality with almost no
        computational overhead compared to a purely random rollout.

        Returns:
            1.0  – player_ai wins
            0.0  – player_ai loses
            0.5  – draw or move-cap (treat as half-point)
        """
        sim = copy.deepcopy(game)
        moves_played = 0

        while moves_played < max_moves:
            winner = sim.check_winner()
            if winner is not None:
                if winner == 0:
                    return 0.5
                return 1.0 if winner == player_ai else 0.0

            moves = sim.get_all_valid_moves(sim.current_player)
            if not moves:
                return 0.5

            opponent = 2 if sim.current_player == 1 else 1
            captures = [m for m in moves if m[1] in sim.pieces[opponent]]
            if captures and random.random() < 0.6:
                move = random.choice(captures)
            else:
                move = random.choice(moves)

            sim.execute_move(*move)
            moves_played += 1

        return 0.5   # move cap — treat as draw

    @staticmethod
    def _mcts_backpropagate(node, result):
        """
        Walk from `node` back to the root, incrementing visit counts and
        adding the result to win totals.

        The result is flipped at each level because each node stores statistics
        from the perspective of the player who made the move *arriving* at it,
        which alternates as we climb toward the root.
        """
        while node is not None:
            node.visits += 1
            node.wins   += result
            result = 1.0 - result   # flip for the parent's player
            node = node.parent

    # ==================================================================
    # EVALUATION FUNCTIONS  (used by Minimax)
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

    # Medium — depth 1, pure material + immediate threats.
    # Plays reasonable moves but is blind to strategy.
    def _evaluate_medium(self, game, player_ai, history=None):
        if history is None:
            history = []
        opponent = 2 if player_ai == 1 else 1
        winner = game.check_winner()
        if winner == player_ai:
            return 10000
        if winner == opponent:
            return -10000

        score  = 0
        my_count  = len(game.pieces[player_ai])
        opp_count = len(game.pieces[opponent])

        score += (my_count - opp_count) * 1000
        score += self._capture_threats(game, player_ai) * 80

        return score + self._repetition_penalty(game, history)

    # Hard — full positional heuristic with mastery awareness.
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

        score += (my_count - opp_count) * 1000
        score += self._capture_threats(game, player_ai) * 80
        score += self._mobility(game, player_ai) * 3
        score -= self._mobility(game, opponent) * 3

        if opp_count == 1 and my_count > 1:
            score += 800
        if my_count == 1 and opp_count > 1:
            score -= 800
        if opp_count == 2:
            score += 150
        if my_count == 2:
            score -= 150

        for q, r in my_pieces:
            score += (3 - self._hex_dist_from_center(q, r)) * 3
        for q, r in opp_pieces:
            score -= (3 - self._hex_dist_from_center(q, r)) * 3

        score += self._clustering_score(my_pieces) * 2
        score -= self._clustering_score(opp_pieces) * 2

        return score + self._repetition_penalty(game, history)


# ==================================================================
# MCTS Node
# ==================================================================

class _MCTSNode:
    """
    A single node in the MCTS search tree.

    Attributes
    ----------
    game     : AnnuvinGame  — board state *after* `move` was applied
    parent   : _MCTSNode | None
    move     : tuple | None — (start, end) that produced this state
    children : list[_MCTSNode]
    visits   : int          — total simulations through this node
    wins     : float        — cumulative win score (1=win, 0.5=draw, 0=loss)
    """
    __slots__ = ("game", "parent", "move", "children", "visits", "wins", "_untried")

    def __init__(self, game, parent, move):
        self.game     = game
        self.parent   = parent
        self.move     = move
        self.children = []
        self.visits   = 0
        self.wins     = 0.0
        self._untried = None   # lazily initialised

    def is_terminal(self):
        return self.game.check_winner() is not None

    def untried_moves(self):
        """Return the list of moves not yet represented by a child node."""
        if self._untried is None:
            all_moves = self.game.get_all_valid_moves(self.game.current_player)
            self._untried = list(all_moves)
        tried = {c.move for c in self.children}
        return [m for m in self._untried if m not in tried]

    def is_fully_expanded(self):
        return len(self.untried_moves()) == 0

    def best_child(self, c=1.41):
        """Return the child with the highest UCB1 score."""
        log_parent = math.log(self.visits) if self.visits > 0 else 0

        def ucb1(child):
            if child.visits == 0:
                return float("inf")
            return (child.wins / child.visits) + c * math.sqrt(log_parent / child.visits)

        return max(self.children, key=ucb1)


class _TimeUp(Exception):
    pass
