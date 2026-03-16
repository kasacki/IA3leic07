import math

class AnnuvinGame:
    def __init__(self, board_radius=3):
        self.radius = board_radius
        self.current_player = 1  # 1 (now Black), 2 (now White)
        self.starting_count = 6
        self.mode = "PVP" # Default: Person vs Person
        self.player1_type = "Human"
        self.player2_type = "Human"
        self.p1_difficulty = "Beginner"
        self.p2_difficulty = "Beginner"
        
        # New starting coordinates matching image_1.png
        # Validated for Pointy-Topped, Radius 3
        self.pieces = {
        1: [(-2, 3), (-1, 3), (0, 3), (0, 2), (1, 2), (2, 1)], # Black
        2: [(2, -3), (1, -3), (0, -3), (0, -2), (-1, -2), (-2, -1)] # White
    }
        
    def get_all_valid_moves(self, player):
        """Returns a list of (start_coords, end_coords) for all legal moves."""
        valid_moves = []
        # Get all pieces belonging to the player
        player_pieces = self.pieces[player]
        
        for start in player_pieces:
            # Scan every possible hex on a radius 3 board
            for q in range(-3, 4):
                for r in range(-3, 4):
                    if abs(q + r) <= 3:
                        target = (q, r)
                        # Reuse your existing movement logic!
                        if self.is_valid_move(start, target):
                            valid_moves.append((start, target))
        return valid_moves

    def get_max_distance(self, player):
        """The 'Mastery' Rule: 7 minus number of pieces owned."""
        return 7 - len(self.pieces[player])

    def get_hex_distance(self, q1, r1, q2, r2):
        """Calculates how many steps between two hexes."""
        return (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2

    def is_valid_move(self, start, end):

      q1, r1 = start
      q2, r2 = end

      if start == end:
        return False

      if abs(q2) > self.radius or abs(r2) > self.radius or abs(q2 + r2) > self.radius:
        return False

      dist = self.get_hex_distance(q1, r1, q2, r2)

      if dist > self.get_max_distance(self.current_player):
        return False

      if end in self.pieces[self.current_player]:
        return False

      return True
    def execute_move(self, start, end):
        # 1. Identify players
        current = self.current_player
        opponent = 2 if current == 1 else 1

        # 2. Capture: Remove enemy piece if it's at 'end'
        if end in self.pieces[opponent]:
            self.pieces[opponent].remove(end)

        # 3. Move: Update your own piece position
        # We use index because 'remove' by value can be slow/buggy if duplicates exist
        idx = self.pieces[current].index(start)
        self.pieces[current][idx] = end
            
        # 4. Switch turns
        self.current_player = 2 if self.current_player == 1 else 1
    
    def check_winner(self):
        p1_count = len(self.pieces[1])
        p2_count = len(self.pieces[2])

        # Condition 1: Elimination
        if p1_count == 0: return 2
        if p2_count == 0: return 1

        # Condition 2: Mastery (1 piece vs 6 pieces)
        # Assuming starting pieces = 6
        if p1_count == 1 and p2_count == 6: return 2
        if p2_count == 1 and p1_count == 6: return 1

        return None # No winner yet