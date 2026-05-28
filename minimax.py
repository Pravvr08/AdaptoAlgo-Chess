"""
minimax.py - Minimax algorithm with alpha-beta pruning.

Implements the core AI search:
  - Iterative deepening for time management
  - Alpha-beta pruning for efficiency
  - Move ordering for better pruning
  - Quiescence search to avoid horizon effect
"""

import chess
import random
import time
from typing import Optional, Tuple
from evaluator import evaluate


# -------------------------------------------------------------------
# Move Ordering Helpers
# -------------------------------------------------------------------

def mvv_lva_score(board: chess.Board, move: chess.Move) -> int:
    """
    Most Valuable Victim – Least Valuable Attacker heuristic.
    Ranks captures: prefer capturing high-value pieces with low-value ones.
    """
    if not board.is_capture(move):
        return 0
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim is None or attacker is None:
        return 0
    from evaluator import PIECE_VALUES
    return PIECE_VALUES.get(victim.piece_type, 0) * 10 - \
           PIECE_VALUES.get(attacker.piece_type, 0)


def order_moves(board: chess.Board, moves: list) -> list:
    """
    Order moves to improve alpha-beta cutoffs:
      1. Captures (by MVV-LVA score)
      2. Promotions
      3. Checks
      4. Quiet moves
    """
    def move_priority(move: chess.Move) -> int:
        score = 0
        if board.is_capture(move):
            score += 10000 + mvv_lva_score(board, move)
        if move.promotion:
            score += 9000
        if board.gives_check(move):
            score += 5000
        return score

    return sorted(moves, key=move_priority, reverse=True)


# -------------------------------------------------------------------
# Quiescence Search
# -------------------------------------------------------------------

def quiescence(board: chess.Board, alpha: int, beta: int,
               style: str, aggression_bias: float) -> int:
    """
    Quiescence search: extend search in tactical positions (captures only).
    Prevents the 'horizon effect' where the engine misses obvious recaptures.
    """
    stand_pat = evaluate(board, aggression_bias, style)
    if board.turn == chess.BLACK:
        stand_pat = -stand_pat

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    # Only look at captures
    captures = [m for m in board.legal_moves if board.is_capture(m)]
    captures = order_moves(board, captures)

    for move in captures:
        board.push(move)
        score = -quiescence(board, -beta, -alpha, style, aggression_bias)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


# -------------------------------------------------------------------
# Alpha-Beta Minimax
# -------------------------------------------------------------------

def alpha_beta(board: chess.Board,
               depth: int,
               alpha: int,
               beta: int,
               style: str,
               aggression_bias: float) -> int:
    """
    Negamax with alpha-beta pruning.
    Returns the score of the position from the perspective of the side to move.
    """
    if depth == 0:
        return quiescence(board, alpha, beta, style, aggression_bias)

    if board.is_game_over():
        result = board.result()
        if board.is_checkmate():
            return -100000 + board.fullmove_number  # Prefer faster checkmates
        return 0  # Draw

    moves = order_moves(board, list(board.legal_moves))

    for move in moves:
        board.push(move)
        score = -alpha_beta(board, depth - 1, -beta, -alpha,
                            style, aggression_bias)
        board.pop()

        if score >= beta:
            return beta  # Beta cutoff
        if score > alpha:
            alpha = score

    return alpha


# -------------------------------------------------------------------
# Best Move Finder
# -------------------------------------------------------------------

def find_best_move(board: chess.Board,
                   depth: int = 3,
                   style: str = "balanced",
                   aggression_bias: float = 0.0,
                   mistake_prob: float = 0.0,
                   time_limit: float = 5.0) -> Optional[chess.Move]:
    """
    Find the best move using iterative deepening alpha-beta.
    
    Args:
        board:          Current board position.
        depth:          Search depth (higher = stronger but slower).
        style:          AI playstyle ('aggressive', 'defensive', 'balanced').
        aggression_bias: Float [-1, 1] to tilt evaluation.
        mistake_prob:   Probability [0,1] of playing a suboptimal move.
        time_limit:     Maximum search time in seconds.
    
    Returns:
        The chosen chess.Move, or None if no legal moves exist.
    """
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None

    # Simulate human mistake: occasionally play a random or suboptimal move
    if mistake_prob > 0 and random.random() < mistake_prob:
        # Return a random move among the top 30% worst moves (plausible blunder)
        scored_moves = []
        for move in legal_moves:
            board.push(move)
            score = -evaluate(board, aggression_bias, style)
            board.pop()
            scored_moves.append((score, move))
        scored_moves.sort(key=lambda x: x[0])
        # Pick from the bottom third as a "mistake"
        n = max(1, len(scored_moves) // 3)
        return random.choice(scored_moves[:n])[1]

    start_time = time.time()
    best_move = legal_moves[0]
    best_score = -float('inf')

    # Iterative deepening: search deeper until time runs out
    for current_depth in range(1, depth + 1):
        if time.time() - start_time > time_limit:
            break

        current_best_move = best_move
        current_best_score = -float('inf')
        alpha = -float('inf')
        beta = float('inf')

        ordered_moves = order_moves(board, legal_moves)

        for move in ordered_moves:
            board.push(move)
            score = -alpha_beta(board, current_depth - 1, -beta, -alpha,
                                style, aggression_bias)
            board.pop()

            if score > current_best_score:
                current_best_score = score
                current_best_move = move
            if score > alpha:
                alpha = score

        best_move = current_best_move
        best_score = current_best_score

    return best_move


def get_move_score(board: chess.Board, move: chess.Move,
                   style: str = "balanced",
                   aggression_bias: float = 0.0) -> int:
    """
    Quick single-move evaluation (depth=1) for analysis purposes.
    Returns score from White's perspective.
    """
    board.push(move)
    score = evaluate(board, aggression_bias, style)
    board.pop()
    return score
