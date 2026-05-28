"""
main.py - Command-line interface for AdaptoAlgo Chess.

Run with: python main.py
"""

import sys
import os
import time

# Force UTF-8 encoding for standard output (handles chess Unicode symbols on Windows terminal)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import Game


def print_board(game_state: dict, player_color: str):
    """Print a colored ASCII board to the terminal."""
    board_dict = game_state["board"]
    fen = game_state["fen"]

    # Parse FEN board section for ordered display
    from board import ChessBoard
    import chess

    board = chess.Board(fen)
    flipped = player_color == "black"

    print()
    print("  +" + "---+" * 8)
    rank_range = range(7, -1, -1) if not flipped else range(8)
    file_range = range(8) if not flipped else range(7, -1, -1)

    for rank in rank_range:
        row = f"{rank+1} |"
        for file in file_range:
            sq = chess.square(file, rank)
            piece = board.piece_at(sq)
            if piece:
                pieces_map = {
                    'K': '♚', 'Q': '♛', 'R': '♜', 'B': '♝', 'N': '♞', 'P': '♟',
                    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
                }
                symbol = pieces_map.get(piece.symbol(), piece.symbol())
                cell = f" {symbol} "
            else:
                cell = " . "
            row += cell + "|"
        print(row)
        print("  +" + "---+" * 8)

    file_labels = "abcdefgh" if not flipped else "hgfedcba"
    print("    " + "   ".join(file_labels))
    print()


def print_status(state: dict):
    """Print game status information."""
    turn = state["turn"].upper()
    move_num = (state["move_count"] // 2) + 1
    check = " [CHECK!]" if state["is_check"] else ""
    last = f"  Last: {state['last_move']}" if state["last_move"] else ""
    ai = state["ai"]
    print(f"Move {move_num} | Turn: {turn}{check}{last}")
    print(f"AI: depth={ai['search_depth']} style={ai['style']} "
          f"mistakes={ai['mistake_prob']:.0%}")


def print_profile(state: dict):
    """Print player profile summary."""
    p = state["player_profile"]
    print(f"\nPlayer: {p['wins']}W/{p['losses']}L/{p['draws']}D | "
          f"Aggression: {p['aggression']:.2f} | "
          f"Mistakes: {p['mistake_rate']:.2f}")


def main():
    print("=" * 50)
    print("       AdaptoAlgo Chess - Adaptive Engine")
    print("=" * 50)

    # Setup
    color = input("Play as [w]hite or [b]lack? (default=white): ").strip().lower()
    player_color = "black" if color.startswith("b") else "white"

    diff_map = {"1": "beginner", "2": "easy", "3": "medium",
                "4": "hard", "5": "expert", "a": "adaptive"}
    print("Difficulty: 1=Beginner 2=Easy 3=Medium 4=Hard 5=Expert a=Adaptive")
    diff_key = input("Choose difficulty (default=a): ").strip().lower() or "a"
    difficulty = diff_map.get(diff_key, "adaptive")

    game = Game(player_color=player_color, difficulty=difficulty)
    print(f"\nStarting game! You play {player_color.upper()}.\n")

    # If player is Black, AI moves first
    if player_color == "black":
        print("AI (White) is thinking...")
        ai_move = game.ai_move()
        if ai_move:
            print(f"AI plays: {ai_move}")

    # Main game loop
    while not game.game_over:
        state = game.get_state()
        print_board(state, player_color)
        print_status(state)
        print_profile(state)

        if state["turn"] != player_color:
            # AI turn
            print("\nAI is thinking...")
            start = time.time()
            ai_move = game.ai_move()
            elapsed = time.time() - start
            if ai_move:
                print(f"AI plays: {ai_move} ({elapsed:.2f}s)")
            continue

        # Player turn
        print(f"\nLegal moves: {' '.join(state['legal_moves'][:12])}...")
        cmd = input("Your move (UCI) or [r]esign / [d]raw / [u]ndo / [q]uit: ").strip().lower()

        if cmd == "q":
            print("Goodbye!")
            break
        elif cmd == "r":
            game.resign()
        elif cmd == "d":
            game.offer_draw()
        elif cmd == "u":
            # Undo twice (player + AI move)
            game.board.undo_move()
            game.board.undo_move()
            game.game_over = False
            game.result = None
            print("Move undone.")
        elif cmd:
            success, msg = game.player_move(cmd)
            if not success:
                print(f"  [X] {msg}")
            else:
                print(f"  [OK] {msg}")

    # Game over
    state = game.get_state()
    print_board(state, player_color)
    print("\n" + "=" * 50)
    print(f"GAME OVER: {game.result_reason}")
    print(f"Result: {game.result}")
    print("=" * 50)
    print(game.get_profile_summary())


if __name__ == "__main__":
    main()
