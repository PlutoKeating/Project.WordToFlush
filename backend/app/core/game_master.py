import time
from app.models.game import WordPuzzle, RoomState, GuessRecord, Platform
from app.data.word_puzzle_repository import WordPuzzleRepository
from app.core.vector_calculator import VectorCalculator
from app.core.danmaku_filter import clean_danmaku


class GameMaster:
    def __init__(self, vector_calculator: VectorCalculator):
        self.vector_calculator = vector_calculator
        self.repository = WordPuzzleRepository()

    async def create_room(self, room_id: str, platform: Platform) -> RoomState:
        return RoomState(
            room_id=room_id,
            platform=platform,
            current_puzzle=None,
            streak=0,
            star_level=0,
            highest_affinity=0.0,
            guess_board=[],
            leaderboard=[],
            previous_puzzle=None,
        )

    async def next_puzzle(self, room_state: RoomState) -> WordPuzzle:
        if room_state.current_puzzle:
            room_state.previous_puzzle = room_state.current_puzzle.word

        puzzle = self.repository.random()
        room_state.current_puzzle = puzzle
        room_state.guess_board = []
        room_state.highest_affinity = 0.0

        return puzzle

    async def process_guess(
        self,
        room_state: RoomState,
        user_id: str,
        user_name: str,
        raw_guess: str,
    ) -> GuessRecord | None:
        if not room_state.current_puzzle:
            return None

        cleaned = clean_danmaku(raw_guess)
        if not cleaned["valid"]:
            return None

        guess = cleaned["word"]

        affinity = await self.vector_calculator.calculate_affinity(
            guess, room_state.current_puzzle.word
        )

        if affinity > room_state.highest_affinity:
            room_state.highest_affinity = affinity

        record = GuessRecord(
            user_id=user_id,
            user_name=user_name,
            guess=guess,
            affinity=affinity,
            timestamp=int(time.time() * 1000),
        )

        room_state.guess_board.insert(0, record)
        room_state.guess_board = room_state.guess_board[:20]

        return record
