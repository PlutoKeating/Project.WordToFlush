from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Literal, Optional

Platform = Literal["bilibili", "douyin", "kuaishou"]
Difficulty = Literal["easy", "medium", "hard"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class WordPuzzle(CamelModel):
    id: str
    word: str
    word_length: int
    category: str
    difficulty: Difficulty


class GuessRecord(CamelModel):
    user_id: str
    user_name: str
    guess: str
    affinity: float
    timestamp: int


class Player(CamelModel):
    user_id: str
    user_name: str
    total_score: int = 0
    current_score: int = 0
    guess_count: int = 0


class RoomState(CamelModel):
    room_id: str
    platform: Platform
    current_puzzle: Optional[WordPuzzle] = None
    streak: int = 0
    highest_affinity: float = 0.0
    guess_board: list[GuessRecord] = []
    leaderboard: list[Player] = []
    previous_puzzle: Optional[str] = None
    solved_by: Optional[str] = None
