"""
adaptive_ai.py - Adaptive AI Module.

Dynamically adjusts the AI's behavior based on:
  - The player's skill profile (aggression, mistake rate, etc.)
  - Current game state (opening, middlegame, endgame)
  - Match history (win streak, recent performance)

Controls:
  - Search depth (difficulty)
  - Playing style (aggressive / defensive / balanced)
  - Mistake simulation probability
  - Aggression bias in evaluation
"""

import random
import chess
from player_model import PlayerProfile
from minimax import find_best_move
from typing import Optional, Tuple


# -------------------------------------------------------------------
# Difficulty Presets
# -------------------------------------------------------------------

DIFFICULTY_PRESETS = {
    "beginner":     {"depth": 1, "mistake_prob": 0.35, "base_style": "random"},
    "easy":         {"depth": 2, "mistake_prob": 0.20, "base_style": "balanced"},
    "medium":       {"depth": 3, "mistake_prob": 0.08, "base_style": "balanced"},
    "hard":         {"depth": 4, "mistake_prob": 0.02, "base_style": "balanced"},
    "expert":       {"depth": 5, "mistake_prob": 0.00, "base_style": "balanced"},
    "adaptive":     {"depth": 3, "mistake_prob": 0.10, "base_style": "balanced"},
}


class AdaptiveAI:
    """
    Wraps the minimax engine with adaptive behavior.
    Reads the player profile to calibrate search depth, playstyle,
    and mistake probability for a personalized experience.
    """

    def __init__(self,
                 difficulty: str = "adaptive",
                 color: chess.Color = chess.BLACK):
        """
        Args:
            difficulty: One of the DIFFICULTY_PRESETS keys.
            color:      The color the AI plays (default Black).
        """
        self.color = color
        self.difficulty = difficulty
        self.preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["medium"])

        # Current parameters (can change during the game)
        self.search_depth: int = self.preset["depth"]
        self.style: str = self.preset["base_style"]
        self.mistake_prob: float = self.preset["mistake_prob"]
        self.aggression_bias: float = 0.0

        # Tracks consecutive wins/losses this session
        self.session_results: list = []

    # ------------------------------------------------------------------
    # Adaptation logic
    # ------------------------------------------------------------------

    def adapt_to_player(self, profile: PlayerProfile, board: chess.Board):
        """
        Adjust AI parameters based on the current player profile and
        game phase. Called before each AI move.
        """
        if self.difficulty != "adaptive":
            return  # Fixed difficulty — no adaptation

        win_rate = profile.win_rate()
        aggression = profile.aggression
        mistake_rate = profile.mistake_rate

        # --- Difficulty (depth) adaptation ---
        # If the player is winning a lot, increase depth (get harder)
        if win_rate > 0.60 and profile.games_played >= 3:
            self.search_depth = min(5, self.search_depth + 1)
        elif win_rate < 0.35 and profile.games_played >= 3:
            self.search_depth = max(1, self.search_depth - 1)

        # --- Mistake probability adaptation ---
        # Match mistake rate inversely to player's mistakes
        if mistake_rate > 0.25:
            self.mistake_prob = 0.25  # Player blunders a lot → AI also makes mistakes
        elif mistake_rate < 0.05:
            self.mistake_prob = 0.02  # Strong player → AI plays near-optimally
        else:
            self.mistake_prob = 0.10

        # --- Style adaptation ---
        # Counter the player's tendencies
        if aggression > 0.65:
            # Aggressive player → play defensively, focus on king safety
            self.style = "defensive"
            self.aggression_bias = -0.3
        elif aggression < 0.35:
            # Passive player → be aggressive, apply pressure
            self.style = "aggressive"
            self.aggression_bias = 0.3
        else:
            self.style = "balanced"
            self.aggression_bias = 0.0

        # --- Game phase adjustments ---
        piece_count = len(board.piece_map())
        if piece_count <= 12:  # Endgame: activate king, increase depth
            self.search_depth = min(5, self.search_depth + 1)
            self.mistake_prob = max(0, self.mistake_prob - 0.05)

    # ------------------------------------------------------------------
    # Move selection
    # ------------------------------------------------------------------

    def choose_move(self,
                    board: chess.Board,
                    profile: Optional[PlayerProfile] = None,
                    time_limit: float = 5.0) -> Optional[chess.Move]:
        """
        Select a move using the minimax engine with current adaptive params.
        
        Args:
            board:      Current board state.
            profile:    Player profile for adaptation (None = no adaptation).
            time_limit: Max seconds to search.
        
        Returns:
            The chosen chess.Move.
        """
        if profile and self.difficulty == "adaptive":
            self.adapt_to_player(profile, board)

        # Special case: beginner just plays random moves occasionally
        if self.style == "random" or (
                self.difficulty == "beginner" and random.random() < 0.5):
            return random.choice(list(board.legal_moves))

        return find_best_move(
            board=board,
            depth=self.search_depth,
            style=self.style,
            aggression_bias=self.aggression_bias,
            mistake_prob=self.mistake_prob,
            time_limit=time_limit,
        )

    # ------------------------------------------------------------------
    # Session tracking
    # ------------------------------------------------------------------

    def record_result(self, result: str, ai_color: str):
        """Record a game result to track session performance."""
        ai_won = (result == "1-0" and ai_color == "white") or \
                 (result == "0-1" and ai_color == "black")
        self.session_results.append("win" if ai_won else
                                    ("draw" if "1/2" in result else "loss"))
        # Keep last 10 results
        self.session_results = self.session_results[-10:]

    def get_status(self) -> dict:
        """Return current AI parameter snapshot for UI display."""
        return {
            "difficulty": self.difficulty,
            "search_depth": self.search_depth,
            "style": self.style,
            "mistake_prob": round(self.mistake_prob, 3),
            "aggression_bias": round(self.aggression_bias, 3),
        }

    def set_difficulty(self, difficulty: str):
        """Switch to a named difficulty preset."""
        if difficulty in DIFFICULTY_PRESETS:
            self.difficulty = difficulty
            preset = DIFFICULTY_PRESETS[difficulty]
            self.search_depth = preset["depth"]
            self.style = preset["base_style"]
            self.mistake_prob = preset["mistake_prob"]
            self.aggression_bias = 0.0
