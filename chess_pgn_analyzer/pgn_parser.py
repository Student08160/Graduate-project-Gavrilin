import chess.pgn
import io

def parse_pgn_file(file_content: str) -> list[dict]:
    games = []
    pgn_io = io.StringIO(file_content)

    while True:
        # Читаем партию
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        headers = game.headers
        
        # Получаем полный PGN-текст партии (используем экспортер)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        pgn_text = game.accept(exporter)

        game_data = {
            "white_player": headers.get("White", "Не указано"),
            "black_player": headers.get("Black", "Не указано"),
            "result": headers.get("Result", "Не указано"),
            "game_date": headers.get("Date", None),
            "opening_name": headers.get("Opening", None),
            "pgn_text": pgn_text # СОХРАНЯЕМ ХОДЫ
        }
        games.append(game_data)

    return games