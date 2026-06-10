import time
from app.models.game import WordPuzzle, RoomState, GuessRecord, Player, Platform
from app.data.word_puzzle_repository import WordPuzzleRepository
from app.core.vector_calculator import VectorCalculator
from app.core.danmaku_filter import clean_danmaku
from app.config import WIN_AFFINITY_THRESHOLD

STAR_THRESHOLD = 0.85
MAX_STAR = 5


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
            solved_by=None,
        )

    async def next_puzzle(self, room_state: RoomState) -> WordPuzzle:
        if room_state.current_puzzle:
            room_state.previous_puzzle = room_state.current_puzzle.word

        prev_category = room_state.current_puzzle.category if room_state.current_puzzle else None
        puzzle = self.repository.random(exclude_category=prev_category)
        room_state.current_puzzle = puzzle
        room_state.guess_board = []
        room_state.highest_affinity = 0.0
        room_state.star_level = 0
        room_state.solved_by = None

        for p in room_state.leaderboard:
            p.current_score = 0

        return puzzle

    def get_available_hints(self, room_state: RoomState) -> list[str]:
        if not room_state.current_puzzle:
            return []
        hints = room_state.current_puzzle.hints
        return hints[:room_state.star_level]

    async def process_guess(
        self,
        room_state: RoomState,
        user_id: str,
        user_name: str,
        raw_guess: str,
    ) -> dict | None:
        if not room_state.current_puzzle:
            return None

        if room_state.solved_by is not None:
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

        score = round(affinity * 100)

        player = self._get_or_create_player(room_state, user_id, user_name)
        player.guess_count += 1
        player.current_score += score
        player.total_score += score

        is_solved = affinity >= WIN_AFFINITY_THRESHOLD
        if is_solved:
            room_state.solved_by = user_name

        if (
            room_state.highest_affinity >= STAR_THRESHOLD
            and room_state.star_level < MAX_STAR
        ):
            room_state.star_level = min(MAX_STAR, room_state.star_level + 1)

        record = GuessRecord(
            user_id=user_id,
            user_name=user_name,
            guess=guess,
            affinity=affinity,
            timestamp=int(time.time() * 1000),
        )

        room_state.guess_board.insert(0, record)
        room_state.guess_board = room_state.guess_board[:20]

        room_state.leaderboard.sort(key=lambda p: p.total_score, reverse=True)

        return {"record": record, "solved": is_solved}

    def _get_or_create_player(
        self, room_state: RoomState, user_id: str, user_name: str
    ) -> Player:
        for p in room_state.leaderboard:
            if p.user_id == user_id:
                p.user_name = user_name
                return p
        player = Player(user_id=user_id, user_name=user_name)
        room_state.leaderboard.append(player)
        return player
