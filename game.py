"""
game.py - Game Controller.

Orchestrates all modules:
  - ChessBoard (engine)
  - AdaptiveAI (AI opponent)
  - PlayerModeler (profile tracking)

Provides a clean API for the UI layer.
"""

import chess
import time
from typing import Optional, Tuple, List

from board import ChessBoard
from adaptive_ai import AdaptiveAI
from player_model import PlayerModeler


class Game:
    """
    Top-level game controller. Manages a single game session
    and coordinates board, AI, and player modeling.
    """

    def __init__(self,
                 player_color: str = "white",
                 difficulty: str = "adaptive",
                 profile_path: str = "data/player_profile.json"):
        """
        Args:
            player_color: 'white' or 'black' (AI takes the other).
            difficulty:   AI difficulty preset name.
            profile_path: Path for persistent player profile.
        """
        self.player_color_str = player_color
        self.player_color = chess.WHITE if player_color == "white" else chess.BLACK
        self.ai_color = chess.BLACK if player_color == "white" else chess.WHITE
        self.ai_color_str = "black" if player_color == "white" else "white"

        self.board = ChessBoard()
        self.ai = AdaptiveAI(
            difficulty=difficulty,
            color=self.ai_color,
        )
        self.modeler = PlayerModeler(profile_path=profile_path)

        self.game_over = False
        self.result: Optional[str] = None
        self.result_reason: str = ""
        self.move_start_time: float = time.time()

    # ------------------------------------------------------------------
    # Player move handling
    # ------------------------------------------------------------------

    def player_move(self, uci_str: str) -> Tuple[bool, str]:
        """
        Process a player move given in UCI format (e.g., 'e2e4').
        Returns (success, message).
        """
        if self.game_over:
            return False, "Game is already over."
        if self.board.board.turn != self.player_color:
            return False, "It's not your turn."

        time_taken = time.time() - self.move_start_time
        success = self.board.make_move_uci(uci_str, time_taken=time_taken)

        if not success:
            return False, f"Illegal move: {uci_str}"

        self.move_start_time = time.time()
        self._check_game_over()
        return True, f"Move {uci_str} played."

    # ------------------------------------------------------------------
    # AI move handling
    # ------------------------------------------------------------------

    def ai_move(self, time_limit: float = 5.0) -> Optional[str]:
        """
        Let the AI choose and play its move.
        Returns the move in UCI notation, or None if game is over.
        """
        if self.game_over:
            return None
        if self.board.board.turn != self.ai_color:
            return None

        profile = self.modeler.get_profile()
        move = self.ai.choose_move(
            board=self.board.board,
            profile=profile,
            time_limit=time_limit,
        )

        if move is None:
            return None

        time_taken = time.time() - self.move_start_time
        self.board.make_move(move, time_taken=time_taken)
        self.move_start_time = time.time()
        self._check_game_over()
        return move.uci()

    # ------------------------------------------------------------------
    # Game state helpers
    # ------------------------------------------------------------------

    def _check_game_over(self):
        """Check if the game has ended and update state."""
        if self.board.is_game_over():
            self.game_over = True
            self.result = self.board.get_result()
            self.result_reason = self.board.get_game_over_reason()
            self._end_game()

    def _end_game(self):
        """Handle post-game processing: update player profile."""
        if self.result:
            self.ai.record_result(self.result, self.ai_color_str)
            self.modeler.update_profile(
                move_history=self.board.move_history,
                player_color=self.player_color_str,
                result=self.result,
            )

    def get_state(self) -> dict:
        """
        Return a complete game state snapshot for the UI.
        """
        profile = self.modeler.get_profile()
        ai_status = self.ai.get_status()

        return {
            "board": self.board.get_board_dict(),
            "fen": self.board.get_fen(),
            "turn": "white" if self.board.is_white_turn() else "black",
            "player_color": self.player_color_str,
            "legal_moves": self.board.get_legal_moves_uci(),
            "is_check": self.board.is_in_check(),
            "game_over": self.game_over,
            "result": self.result,
            "result_reason": self.result_reason,
            "move_count": len(self.board.move_history),
            "last_move": self.board.move_history[-1]["move"]
                         if self.board.move_history else None,
            "ai": ai_status,
            "player_profile": {
                "wins": profile.wins,
                "losses": profile.losses,
                "draws": profile.draws,
                "aggression": round(profile.aggression, 2),
                "mistake_rate": round(profile.mistake_rate, 2),
                "games_played": profile.games_played,
            },
        }

    def get_legal_moves_for_square(self, square_name: str) -> List[str]:
        """Return UCI moves that originate from the given square (e.g., 'e2')."""
        try:
            sq = chess.parse_square(square_name)
        except ValueError:
            return []
        return [
            m.uci() for m in self.board.board.legal_moves
            if m.from_square == sq
        ]

    def resign(self):
        """Player resigns the current game."""
        self.game_over = True
        self.result = "0-1" if self.player_color == chess.WHITE else "1-0"
        self.result_reason = f"{self.player_color_str.capitalize()} resigned."
        self._end_game()

    def offer_draw(self) -> bool:
        """Accept a draw (auto-accept for simplicity)."""
        self.game_over = True
        self.result = "1/2-1/2"
        self.result_reason = "Draw by agreement."
        self._end_game()
        return True

    def get_profile_summary(self) -> str:
        """Return the player profile as a readable string."""
        return self.modeler.get_summary()

    def new_game(self,
                 player_color: Optional[str] = None,
                 difficulty: Optional[str] = None):
        """Start a fresh game (preserves profile)."""
        if player_color:
            self.player_color_str = player_color
            self.player_color = chess.WHITE if player_color == "white" else chess.BLACK
            self.ai_color = chess.BLACK if player_color == "white" else chess.WHITE
            self.ai_color_str = "black" if player_color == "white" else "white"
        if difficulty:
            self.ai.set_difficulty(difficulty)

        self.board.reset()
        self.game_over = False
        self.result = None
        self.result_reason = ""
        self.move_start_time = time.time()
