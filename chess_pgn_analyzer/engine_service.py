import chess.engine
import os

ENGINE_PATH = os.path.join(os.path.dirname(__file__), "engine", "stockfish.exe")


def evaluate_position(fen: str, time_limit: float = 0.1) -> str:
    if not os.path.exists(ENGINE_PATH):
        return "Движок не найден"

    try:
        with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
            board = chess.Board(fen)
            info = engine.analyse(board, chess.engine.Limit(time=time_limit))

            score = info["score"].white()

            if score.is_mate():
                moves_to_mate = score.mate()
                if moves_to_mate > 0:
                    return f"Мат через {moves_to_mate} (Белые)"
                else:
                    return f"Мат через {abs(moves_to_mate)} (Чёрные)"
            else:
                cp = score.score()
                if cp is not None:
                    val = cp / 100.0
                    return f"{val:+.2f}"
                return "Н/Д"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def save_analysis(db, game_id: int, move_number: int, fen: str, score: str):
    from models import AnalysisHistory

    record = AnalysisHistory(
        game_id=game_id,
        move_number=move_number,
        fen=fen,
        score=score
    )
    db.add(record)
    db.commit()