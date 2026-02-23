class AnnuvinGame:
    def __init__(self, board_size=4):
        self.board_size = board_size  # Radius of hex board
        self.current_player = 1  # 1 for White, 2 for Black
        # Axial coordinates: (q, r)
        self.pieces = {
            1: [(3, 0), (3, -1), (3, -2), (2, 1), (2, 0), (2, -1)], # Example start
            2: [(-3, 0), (-3, 1), (-3, 2), (-2, -1), (-2, 0), (-2, 1)]
        }

    def get_move_distance(self, player):
        num_pieces = len(self.pieces[player])
        return 7 - num_pieces

    def is_win(self):
        p1, p2 = len(self.pieces[1]), len(self.pieces[2])
        if p2 == 0 or (p2 == 1 and p1 > 1): return 1
        if p1 == 0 or (p1 == 1 and p2 > 1): return 2
        return None