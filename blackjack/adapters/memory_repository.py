
# ==============================================================================
# File: blackjack/adapters/memory_repository.py
# Mô tả: Lớp Adapter - Cung cấp một triển khai cụ thể cho IGameRepository.
# Ở đây, chúng ta lưu trạng thái game vào một dictionary trong bộ nhớ.
# ==============================================================================
from typing import Optional, Dict
from ..entities import Game
from ..interfaces import IGameRepository

class MemoryGameRepository(IGameRepository):
    """Lưu trữ trạng thái các ván game trong bộ nhớ (dictionary)."""
    _games: Dict[int, Game] = {}

    def get_game(self, channel_id: int) -> Optional[Game]:
        return self._games.get(channel_id)

    def save_game(self, game: Game):
        self._games[game.channel_id] = game

    def delete_game(self, channel_id: int):
        if channel_id in self._games:
            del self._games[channel_id]
