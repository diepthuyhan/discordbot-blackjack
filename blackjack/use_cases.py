
# ==============================================================================
# File: blackjack/use_cases.py
# Mô tả: Lớp Use Cases - Chứa logic nghiệp vụ của ứng dụng.
# Lớp này điều phối các entities và sử dụng các interfaces để thực hiện công việc.
# ==============================================================================
from .entities import Game, GameState
from .interfaces import IGameRepository

class GameUseCase:
    """Bao gồm các hành động mà người dùng có thể thực hiện trong game."""
    def __init__(self, repo: IGameRepository):
        self.repo = repo

    def start_new_game(self, channel_id: int, players: dict[int, str]) -> Game:
        """Bắt đầu một ván chơi mới."""
        game = Game(channel_id)
        for user_id, name in players.items():
            game.add_player(user_id, name)
        
        if not game.players:
            raise ValueError("Không có người chơi.")

        game.start_game()
        self.repo.save_game(game)
        return game

    def join_game(self, channel_id: int, user_id: int, user_name: str) -> tuple[Game, bool]:
        """Cho phép người chơi tham gia vào ván đang chờ."""
        game = self.repo.get_game(channel_id)
        if not game:
            game = Game(channel_id)
        
        if game.state != GameState.WAITING_FOR_PLAYERS:
            raise RuntimeError("Ván chơi đã bắt đầu, không thể tham gia.")

        if user_id in game.players:
            return game, False # Đã tham gia rồi

        game.add_player(user_id, user_name)
        self.repo.save_game(game)
        return game, True

    def player_action(self, channel_id: int, user_id: int, action: str) -> Game:
        """Xử lý hành động 'hit' (rút) hoặc 'stand' (dừng) của người chơi."""
        game = self.repo.get_game(channel_id)
        if not game:
            raise ValueError("Không có ván chơi nào đang diễn ra.")
        
        current_player = game.get_current_player()
        if not current_player or current_player.id != user_id:
            raise PermissionError("Không phải lượt của bạn.")

        if action == 'hit':
            game.player_hit(user_id)
        elif action == 'stand':
            game.player_stand(user_id)
        else:
            raise ValueError("Hành động không hợp lệ.")

        self.repo.save_game(game)
        return game
    
    def end_game(self, channel_id: int):
        """Kết thúc và xóa game khỏi bộ nhớ."""
        self.repo.delete_game(channel_id)
