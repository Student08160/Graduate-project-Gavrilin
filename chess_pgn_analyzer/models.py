from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_premium = Column(Boolean, default=False)

    games = relationship("Game", back_populates="owner")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    white_player = Column(String, nullable=False, default="Не указано")
    black_player = Column(String, nullable=False, default="Не указано")
    result = Column(String, nullable=False, default="Не указано")
    game_date = Column(String, nullable=True)
    opening_name = Column(String, nullable=True)

    pgn_text = Column(String, nullable=False)

    owner = relationship("User", back_populates="games")
    analyses = relationship("AnalysisHistory", back_populates="game")


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    move_number = Column(Integer, nullable=False)
    fen = Column(String, nullable=False)
    score = Column(String, nullable=False)

    game = relationship("Game", back_populates="analyses")