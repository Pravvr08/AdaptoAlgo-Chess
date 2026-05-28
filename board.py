"""
board.py - Chess board management using python-chess library.
Wraps python-chess for clean integration with the AI and UI layers.
"""

import chess
import chess.pgn
from typing import Optional, List, Tuple
from datetime import datetime


class ChessBoard:
    """
    Manages the chess board state, move validation, and game history.
    Acts as the core game engine interface.
    """

    def __init__(self):
        self.board = chess.Board()
        self.move_history: List[dict] = []
        self.game_start_time = datetime.now()

    def reset(self):
        """Reset the board to the starting position."""
        self.board = chess.Board()
        self.move_history = []
        self.game_start_time = datetime.now()

    def get_legal_moves(self) -> List[chess.Move]:
        """Return all legal moves for the current position."""
        return list(self.board.legal_moves)

    def get_legal_moves_uci(self) -> List[str]:
        """Return legal moves in UCI notation (e.g., 'e2e4')."""
        return [move.uci() for move in self.board.legal_moves]

    def make_move(self, move: chess.Move, time_taken: float = 0.0) -> bool:
        """
        Apply a move to the board if it's legal.
        Records move metadata for player profiling.
        Returns True if move was successful.
        """
        if move in self.board.legal_moves:
            move_data = {
                "move": move.uci(),
                "san": self.board.san(move),
                "fen_before": self.board.fen(),
                "turn": "white" if self.board.turn == chess.WHITE else "black",
                "move_number": self.board.fullmove_number,
                "time_taken": time_taken,
                "is_capture": self.board.is_capture(move),
                "is_check": False,  # Will update after push
            }
            self.board.push(move)
            move_data["is_check"] = self.board.is_check()
            move_data["fen_after"] = self.board.fen()
            self.move_history.append(move_data)
            return True
        return False

    def make_move_uci(self, uci_str: str, time_taken: float = 0.0) -> bool:
        """Make a move from a UCI string like 'e2e4'."""
        try:
            move = chess.Move.from_uci(uci_str)
            return self.make_move(move, time_taken)
        except ValueError:
            return False

    def make_move_san(self, san_str: str, time_taken: float = 0.0) -> bool:
        """Make a move from SAN notation like 'Nf3'."""
        try:
            move = self.board.parse_san(san_str)
            return self.make_move(move, time_taken)
        except ValueError:
            return False

    def undo_move(self) -> bool:
        """Undo the last move."""
        if self.move_history:
            self.board.pop()
            self.move_history.pop()
            return True
        return False

    def is_game_over(self) -> bool:
        """Check if the game has ended."""
        return self.board.is_game_over()

    def get_result(self) -> Optional[str]:
        """
        Return the game result string.
        '1-0' = White wins, '0-1' = Black wins, '1/2-1/2' = Draw
        """
        if self.board.is_checkmate():
            return "0-1" if self.board.turn == chess.WHITE else "1-0"
        if self.board.is_stalemate():
            return "1/2-1/2"
        if self.board.is_insufficient_material():
            return "1/2-1/2"
        if self.board.is_seventyfive_moves():
            return "1/2-1/2"
        if self.board.is_fivefold_repetition():
            return "1/2-1/2"
        return None

    def get_game_over_reason(self) -> str:
        """Return a human-readable reason for game end."""
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"Checkmate! {winner} wins."
        if self.board.is_stalemate():
            return "Stalemate! Draw."
        if self.board.is_insufficient_material():
            return "Insufficient material! Draw."
        if self.board.is_seventyfive_moves():
            return "75-move rule! Draw."
        if self.board.is_fivefold_repetition():
            return "Fivefold repetition! Draw."
        return "Game ongoing."

    def get_fen(self) -> str:
        """Return the current FEN string."""
        return self.board.fen()

    def get_board_unicode(self) -> str:
        """Return a unicode representation of the board."""
        return str(self.board)

    def is_white_turn(self) -> bool:
        """Return True if it's White's turn."""
        return self.board.turn == chess.WHITE

    def get_piece_at(self, square: chess.Square) -> Optional[chess.Piece]:
        """Return the piece at a given square, or None."""
        return self.board.piece_at(square)

    def get_board_dict(self) -> dict:
        """
        Return board state as a dictionary for UI rendering.
        Maps square names to piece symbols.
        """
        board_dict = {}
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                square_name = chess.square_name(square)
                board_dict[square_name] = {
                    "symbol": piece.symbol(),
                    "color": "white" if piece.color == chess.WHITE else "black",
                    "type": chess.piece_name(piece.piece_type),
                }
        return board_dict

    def is_in_check(self) -> bool:
        """Return True if the current player is in check."""
        return self.board.is_check()

    def get_attacked_squares(self, color: chess.Color) -> List[str]:
        """Return list of squares attacked by the given color."""
        attacked = []
        for square in chess.SQUARES:
            if self.board.is_attacked_by(color, square):
                attacked.append(chess.square_name(square))
        return attacked
