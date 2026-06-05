from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Game

def get_results_distribution(db: Session, user_id: int) -> dict:
    white_wins = db.query(Game).filter(Game.user_id == user_id, Game.result == "1-0").count()
    black_wins = db.query(Game).filter(Game.user_id == user_id, Game.result == "0-1").count()
    draws = db.query(Game).filter(Game.user_id == user_id, Game.result == "1/2-1/2").count()
    return {"white_wins": white_wins, "black_wins": black_wins, "draws": draws}

def get_top_openings(db: Session, user_id: int, limit: int = 5) -> list[dict]:
    results = (
        db.query(Game.opening_name, func.count(Game.opening_name).label("count"))
        .filter(Game.user_id == user_id, Game.opening_name.isnot(None))
        .group_by(Game.opening_name)
        .order_by(func.count(Game.opening_name).desc())
        .limit(limit)
        .all()
    )
    return [{"opening": row.opening_name, "count": row.count} for row in results]

def get_user_games(db: Session, user_id: int) -> list[Game]:
    return db.query(Game).filter(Game.user_id == user_id).all()

def get_total_count(db: Session, user_id: int) -> int:
    return db.query(Game).filter(Game.user_id == user_id).count()