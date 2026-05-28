"""
evaluator.py - Chess position evaluation function.

Evaluates positions using multiple strategic factors:
  - Material balance
  - Piece mobility
  - King safety
  - Center control
  - Pawn structure
  - Piece-square tables
"""

import chess
from typing import Dict

# -------------------------------------------------------------------
# Piece Values (centipawns)
# -------------------------------------------------------------------
PIECE_VALUES: Dict[chess.PieceType, int] = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

# -------------------------------------------------------------------
# Piece-Square Tables
# Positive = good square, Negative = bad square (from White's view)
# -------------------------------------------------------------------

PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

ROOK_TABLE = [
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0,
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

KING_MIDDLE_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

KING_END_TABLE = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

PIECE_TABLES = {
    chess.PAWN:   PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK:   ROOK_TABLE,
    chess.QUEEN:  QUEEN_TABLE,
    chess.KING:   KING_MIDDLE_TABLE,  # Switched to end table in endgame
}

# Center squares for center control bonus
CENTER_SQUARES = {chess.D4, chess.D5, chess.E4, chess.E5}
EXTENDED_CENTER = {chess.C3, chess.C4, chess.C5, chess.C6,
                   chess.D3, chess.D6, chess.E3, chess.E6,
                   chess.F3, chess.F4, chess.F5, chess.F6}


def get_piece_square_value(piece_type: chess.PieceType,
                           square: chess.Square,
                           color: chess.Color,
                           is_endgame: bool) -> int:
    """
    Look up piece-square table value.
    White uses the table as-is (a1=index 0); Black mirrors it.
    """
    if piece_type == chess.KING and is_endgame:
        table = KING_END_TABLE
    else:
        table = PIECE_TABLES.get(piece_type, [0] * 64)

    if color == chess.WHITE:
        # Mirror square so a1 is index 0 for White
        idx = (7 - chess.square_rank(square)) * 8 + chess.square_file(square)
    else:
        idx = chess.square_rank(square) * 8 + chess.square_file(square)

    return table[idx]


def is_endgame(board: chess.Board) -> bool:
    """
    Detect endgame: both sides have ≤1 queen or very low total material.
    """
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + \
             len(board.pieces(chess.QUEEN, chess.BLACK))
    if queens == 0:
        return True
    if queens == 2:
        minor_and_rooks = (
            len(board.pieces(chess.ROOK,   chess.WHITE)) +
            len(board.pieces(chess.ROOK,   chess.BLACK)) +
            len(board.pieces(chess.BISHOP, chess.WHITE)) +
            len(board.pieces(chess.BISHOP, chess.BLACK)) +
            len(board.pieces(chess.KNIGHT, chess.WHITE)) +
            len(board.pieces(chess.KNIGHT, chess.BLACK))
        )
        return minor_and_rooks <= 2
    return False


def evaluate_material(board: chess.Board) -> int:
    """Compute raw material balance in centipawns (positive = White ahead)."""
    score = 0
    for piece_type in PIECE_VALUES:
        score += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]
    return score


def evaluate_piece_square(board: chess.Board, endgame: bool) -> int:
    """Sum up piece-square table bonuses for all pieces."""
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = get_piece_square_value(piece.piece_type, square,
                                         piece.color, endgame)
            score += val if piece.color == chess.WHITE else -val
    return score


def evaluate_mobility(board: chess.Board) -> int:
    """
    Mobility: count legal moves for each side.
    More moves = more options = better position.
    """
    current_turn = board.turn

    board.turn = chess.WHITE
    white_moves = len(list(board.legal_moves))

    board.turn = chess.BLACK
    black_moves = len(list(board.legal_moves))

    board.turn = current_turn  # Restore original turn
    return (white_moves - black_moves) * 3  # 3 centipawns per extra move


def evaluate_king_safety(board: chess.Board, endgame: bool) -> int:
    """
    King safety heuristic (middle-game only).
    Checks pawn shield in front of the king and attackers near king.
    """
    if endgame:
        return 0

    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        king_sq = board.king(color)
        if king_sq is None:
            continue

        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)

        # Castled king pawn shield bonus
        pawn_shield = 0
        shield_ranks = [king_rank + 1] if color == chess.WHITE else [king_rank - 1]
        for r in shield_ranks:
            if 0 <= r <= 7:
                for f in range(max(0, king_file - 1), min(7, king_file + 2)):
                    sq = chess.square(f, r)
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        pawn_shield += 1

        # Attacker pressure near king
        attackers = 0
        for sq in chess.SQUARES:
            if chess.square_distance(sq, king_sq) <= 2:
                if board.is_attacked_by(not color, sq):
                    attackers += 1

        safety = pawn_shield * 10 - attackers * 8
        score += safety if color == chess.WHITE else -safety

    return score


def evaluate_center_control(board: chess.Board) -> int:
    """Bonus for controlling/occupying central squares."""
    score = 0
    for sq in CENTER_SQUARES:
        if board.is_attacked_by(chess.WHITE, sq):
            score += 15
        if board.is_attacked_by(chess.BLACK, sq):
            score -= 15
        piece = board.piece_at(sq)
        if piece:
            bonus = 20
            score += bonus if piece.color == chess.WHITE else -bonus

    for sq in EXTENDED_CENTER:
        if board.is_attacked_by(chess.WHITE, sq):
            score += 5
        if board.is_attacked_by(chess.BLACK, sq):
            score -= 5
    return score


def evaluate_pawn_structure(board: chess.Board) -> int:
    """Penalize doubled, isolated, and backward pawns."""
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        sign = 1 if color == chess.WHITE else -1
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]

        # Doubled pawns penalty
        for f in range(8):
            count = files.count(f)
            if count > 1:
                score -= sign * (count - 1) * 20

        # Isolated pawns penalty
        for f in range(8):
            if f in files:
                neighbors = [f - 1, f + 1]
                if not any(n in files for n in neighbors if 0 <= n <= 7):
                    score -= sign * 15

    return score


def evaluate(board: chess.Board,
             aggression_bias: float = 0.0,
             style: str = "balanced") -> int:
    """
    Full position evaluation from White's perspective (centipawns).
    
    Args:
        board:          The chess board to evaluate.
        aggression_bias: Float in [-1, 1]; positive = more attacking play.
        style:          'aggressive', 'defensive', or 'balanced'.
    
    Returns:
        Integer score. Positive = White is better.
    """
    if board.is_checkmate():
        # Current player is in checkmate → they lose
        return -100000 if board.turn == chess.WHITE else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    endgame = is_endgame(board)

    material     = evaluate_material(board)
    psq          = evaluate_piece_square(board, endgame)
    mobility     = evaluate_mobility(board)
    king_safety  = evaluate_king_safety(board, endgame)
    center       = evaluate_center_control(board)
    pawn_struct  = evaluate_pawn_structure(board)

    # Base score
    score = (material + psq + mobility + king_safety + center + pawn_struct)

    # Style-based weighting
    if style == "aggressive":
        score += int(mobility * 0.5 * (1 + aggression_bias))
        score += int(center * 0.3)
    elif style == "defensive":
        score += int(king_safety * 0.5)
        score -= int(mobility * 0.2)
    # 'balanced' uses default weighting

    return score
