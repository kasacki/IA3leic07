import math

class AnnuvinGame:
    def __init__(self, board_radius=3):
        self.radius = board_radius
        self.current_player = 1  # 1 for White, 2 for Black
        
        # Initial piece setup (Standard Annuvin: 6 pieces each)
        # Using Axial Coordinates (q, r)
        self.pieces = {
            1: [(0, 3), (1, 2), (2, 1), (3, 0), (2, 2), (1, 3)], 
            2: [(0, -3), (-1, -2), (-2, -1), (-3, 0), (-2, -2), (-1, -3)]
        }

    def get_max_distance(self, player):
        """The 'Mastery' Rule: 7 minus number of pieces owned."""
        return 7 - len(self.pieces[player])

    def get_hex_distance(self, q1, r1, q2, r2):
        """Calculates how many steps between two hexes."""
        return (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2

    def is_valid_move(self, start, end):
        q1, r1 = start
        q2, r2 = end
        
        # 1. Must stay within board radius
        if abs(q2) > self.radius or abs(r2) > self.radius or abs(q2 + r2) > self.radius:
            return False
            
        # 2. Check distance vs Mastery
        dist = self.get_hex_distance(q1, r1, q2, r2)
        if dist == 0 or dist > self.get_max_distance(self.current_player):
            return False
            
        # 3. Cannot land on own piece
        if end in self.pieces[self.current_player]:
            return False
            
        return True

    def execute_move(self, start, end):
        # Move piece
        self.pieces[self.current_player].remove(start)
        self.pieces[self.current_player].append(end)
        
        # Capture logic: If opponent is there, remove them
        opponent = 2 if self.current_player == 1 else 1
        if end in self.pieces[opponent]:
            self.pieces[opponent].remove(end)
            
        # Switch turns
        self.current_player = opponent