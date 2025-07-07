
# ==============================================================================
# File: blackjack/interfaces.py
# Mô tả: Lớp giao diện (Interfaces) - Định nghĩa các "hợp đồng" (abstract classes)
# mà các lớp bên ngoài phải tuân theo. Điều này giúp đảo ngược sự phụ thuộc.
# ==============================================================================
from abc import ABC, abstractmethod
from typing import Optional

# Forward declaration để tránh circular import
class Game: pass

class IGameRepository(ABC):
    """Giao diện cho việc lưu trữ và truy xuất trạng thái game."""
    @abstractmethod
    def get_game(self, channel_id: int) -> Optional[Game]:
        pass

    @abstractmethod
    def save_game(self, game: Game):
        pass

    @abstractmethod
    def delete_game(self, channel_id: int):
        pass
