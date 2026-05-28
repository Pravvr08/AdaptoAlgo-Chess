"""
player_model.py - Player Modeling System.

Tracks player behavior across games and builds a structured profile:
  - Aggression level (tendency to capture, attack, sacrifice)
  - Mistake rate (blunders, inaccuracies per game)
  - Preferred openings and piece preferences
  - Average thinking time per move
  - Strategic tendencies (positional vs tactical)
  - Win/loss/draw record
"""

import json
import os
import chess
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class GameRecord:
    """Stores statistics from a single completed game."""
    date: str
    result: str           # '1-0', '0-1', '1/2-1/2'
    player_color: str     # 'white' or 'black'
    total_moves: int
    captures: int
    mistakes: int         # Obvious blunders detected
    avg_move_time: float  # Average seconds per move
    opening_moves: List[str] = field(default_factory=list)  # First 5 moves UCI
    checks_given: int = 0
    pieces_sacrificed: int = 0


@dataclass
class PlayerProfile:
    """
    Persistent player profile updated after each game.
    All float fields are in [0, 1] unless noted.
    """
    name: str = "Player"
    
    # Performance metrics
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    # Behavioral metrics (rolling averages)
    aggression: float = 0.5         # 0=passive, 1=highly aggressive
    mistake_rate: float = 0.1       # mistakes per game (normalized)
    avg_move_time: float = 5.0      # seconds per move
    
    # Strategic tendencies
    tactical_tendency: float = 0.5  # 0=positional, 1=tactical/attacking
    endgame_comfort: float = 0.5    # 0=avoids, 1=seeks endgames
    pawn_advancement: float = 0.5   # tendency to push pawns
    
    # Piece preferences
    prefers_bishops: bool = False
    prefers_knights: bool = False
    
    # Opening fingerprint (most played first moves)
    favorite_first_move: str = "e2e4"
    opening_diversity: float = 0.5  # 0=plays same opening, 1=very varied
    
    # Recent game history (last 10 games)
    recent_games: List[dict] = field(default_factory=list)
    
    # Adaptation metadata
    last_updated: str = ""
    
    def win_rate(self) -> float:
        """Return win rate as a fraction."""
        if self.games_played == 0:
            return 0.5
        return self.wins / self.games_played
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlayerProfile":
        return cls(**data)


class PlayerModeler:
    """
    Analyzes move history to build and update a PlayerProfile.
    Called at the end of each game with full move data.
    """

    def __init__(self, profile_path: str = "data/player_profile.json"):
        self.profile_path = profile_path
        self.profile = self._load_profile()

    # ------------------------------------------------------------------
    # Profile persistence
    # ------------------------------------------------------------------

    def _load_profile(self) -> PlayerProfile:
        """Load profile from disk, or create a fresh one."""
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r") as f:
                    data = json.load(f)
                return PlayerProfile.from_dict(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return PlayerProfile()

    def save_profile(self):
        """Persist the profile to disk."""
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        with open(self.profile_path, "w") as f:
            json.dump(self.profile.to_dict(), f, indent=2)

    # ------------------------------------------------------------------
    # Game analysis
    # ------------------------------------------------------------------

    def analyze_game(self,
                     move_history: List[dict],
                     player_color: str,
                     result: str) -> GameRecord:
        """
        Analyze a completed game's move history and return a GameRecord.
        
        Args:
            move_history: List of move dicts from ChessBoard.move_history.
            player_color: 'white' or 'black'.
            result:       Game result string.
        """
        player_moves = [m for m in move_history if m["turn"] == player_color]

        captures = sum(1 for m in player_moves if m.get("is_capture"))
        checks   = sum(1 for m in player_moves if m.get("is_check"))
        total_moves = len(player_moves)

        # Mistake detection: moves that took unusually long (proxy for difficulty)
        # In a real engine, we'd compare eval before/after; here we use a simpler heuristic
        mistakes = self._estimate_mistakes(player_moves)

        avg_time = (sum(m.get("time_taken", 0) for m in player_moves) / total_moves
                    if total_moves > 0 else 0)

        opening_moves = [m["move"] for m in move_history[:10] if m["turn"] == player_color][:5]

        return GameRecord(
            date=datetime.now().isoformat(),
            result=result,
            player_color=player_color,
            total_moves=total_moves,
            captures=captures,
            mistakes=mistakes,
            avg_move_time=avg_time,
            opening_moves=opening_moves,
            checks_given=checks,
        )

    def _estimate_mistakes(self, player_moves: List[dict]) -> int:
        """
        Heuristic mistake estimation.
        Real implementation would compare engine eval before/after each move.
        Here we flag moves where thinking time was very low (< 1s) in
        complex positions as potential blunders.
        """
        mistakes = 0
        times = [m.get("time_taken", 0) for m in player_moves]
        if not times:
            return 0
        avg = sum(times) / len(times)
        # Flag suspiciously fast moves in mid/endgame as potential blunders
        for i, m in enumerate(player_moves):
            move_num = m.get("move_number", 0)
            if move_num > 10 and m.get("time_taken", 0) < avg * 0.2:
                mistakes += 1
        return mistakes

    # ------------------------------------------------------------------
    # Profile update (called after each game)
    # ------------------------------------------------------------------

    def update_profile(self,
                       move_history: List[dict],
                       player_color: str,
                       result: str,
                       alpha: float = 0.2):
        """
        Update the player profile using exponential moving average.
        
        Args:
            move_history:  Full game move list.
            player_color:  'white' or 'black'.
            result:        Game result.
            alpha:         EMA smoothing factor (0=ignore new game, 1=overwrite).
        """
        record = self.analyze_game(move_history, player_color, result)
        p = self.profile

        # Win/loss/draw tracking
        p.games_played += 1
        if (result == "1-0" and player_color == "white") or \
           (result == "0-1" and player_color == "black"):
            p.wins += 1
        elif (result == "0-1" and player_color == "white") or \
             (result == "1-0" and player_color == "black"):
            p.losses += 1
        else:
            p.draws += 1

        # Rolling behavioral updates (EMA)
        if record.total_moves > 0:
            new_aggression = min(1.0, record.captures / max(1, record.total_moves) * 3.0)
            p.aggression = (1 - alpha) * p.aggression + alpha * new_aggression

            new_mistake_rate = min(1.0, record.mistakes / max(1, record.total_moves) * 5.0)
            p.mistake_rate = (1 - alpha) * p.mistake_rate + alpha * new_mistake_rate

            p.avg_move_time = (1 - alpha) * p.avg_move_time + alpha * record.avg_move_time

            new_tactical = min(1.0, record.checks_given / max(1, record.total_moves) * 5.0)
            p.tactical_tendency = (1 - alpha) * p.tactical_tendency + alpha * new_tactical

        # Opening fingerprint
        if record.opening_moves:
            p.favorite_first_move = record.opening_moves[0]

        # Store in recent history (keep last 10)
        p.recent_games.append({
            "date": record.date,
            "result": record.result,
            "mistakes": record.mistakes,
            "aggression": round(self.profile.aggression, 3),
        })
        p.recent_games = p.recent_games[-10:]
        p.last_updated = datetime.now().isoformat()

        self.save_profile()

    # ------------------------------------------------------------------
    # Profile summary for display
    # ------------------------------------------------------------------

    def get_summary(self) -> str:
        """Return a human-readable profile summary."""
        p = self.profile
        wr = f"{p.win_rate()*100:.1f}%"
        aggr = "High" if p.aggression > 0.65 else ("Low" if p.aggression < 0.35 else "Medium")
        style = "Tactical" if p.tactical_tendency > 0.6 else \
                ("Positional" if p.tactical_tendency < 0.4 else "Balanced")
        return (
            f"Player: {p.name}\n"
            f"Record: {p.wins}W / {p.losses}L / {p.draws}D ({wr} win rate)\n"
            f"Aggression: {aggr} ({p.aggression:.2f})\n"
            f"Mistake Rate: {p.mistake_rate:.2f}\n"
            f"Playing Style: {style}\n"
            f"Avg Move Time: {p.avg_move_time:.1f}s\n"
            f"Favorite Opening: {p.favorite_first_move}"
        )

    def get_profile(self) -> PlayerProfile:
        return self.profile
