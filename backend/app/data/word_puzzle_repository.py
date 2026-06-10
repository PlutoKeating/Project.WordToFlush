import json
import logging
import random
from pathlib import Path

from app.models.game import WordPuzzle

logger = logging.getLogger(__name__)

WORD_DATA_DIR = Path(__file__).parent / "word_data"


class WordPuzzleRepository:
    def __init__(self, data_dir: Path | None = None):
        self._puzzles: list[WordPuzzle] = []
        self._by_category: dict[str, list[WordPuzzle]] = {}
        self._load(data_dir or WORD_DATA_DIR)

    def _load(self, data_dir: Path) -> None:
        if not data_dir.exists():
            logger.warning("Word data directory not found: %s", data_dir)
            return

        json_files = sorted(data_dir.glob("*.json"))
        logger.info("Loading word data from %d JSON file(s) in %s", len(json_files), data_dir)

        for json_file in json_files:
            category = json_file.stem
            try:
                items = json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping %s: %s", json_file.name, exc)
                continue

            if not isinstance(items, list):
                logger.warning("Skipping %s: expected a JSON array", json_file.name)
                continue

            category_puzzles: list[WordPuzzle] = []
            for item in items:
                try:
                    item["category"] = category
                    puzzle = WordPuzzle(**item)
                    self._puzzles.append(puzzle)
                    category_puzzles.append(puzzle)
                except Exception as exc:
                    logger.warning("Skipping item in %s: %s", json_file.name, exc)
                    continue

            self._by_category[category] = category_puzzles

    def random(self) -> WordPuzzle:
        if not self._puzzles:
            raise RuntimeError("No puzzles loaded from word_data directory")
        return random.choice(self._puzzles)

    def get_by_category(self, category: str) -> list[WordPuzzle]:
        return self._by_category.get(category, [])

    def get_categories(self) -> list[str]:
        return list(self._by_category.keys())
