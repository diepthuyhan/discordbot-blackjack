# ==============================================================================
# File: blackjack/entities.py
# Mô tả: Lớp lõi (Entities) - Định nghĩa các đối tượng và quy tắc cơ bản của game.
# Hoàn toàn không phụ thuộc vào Discord hay bất kỳ framework nào khác.
# ==============================================================================
import random
from enum import Enum

# --- Enums and Constants ---

SUITS = ["♥️", "♦️", "♣️", "♠️"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
VALUES = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10,
    "A": 11,
}


class GameState(Enum):
    WAITING_FOR_PLAYERS = 1
    PLAYERS_TURN = 2
    DEALER_TURN = 3
    GAME_OVER = 4


class GameResult(Enum):
    PLAYER_WINS = 1
    DEALER_WINS = 2
    PUSH = 3  # Hòa


# --- Core Classes ---


class Card:
    """Đại diện cho một lá bài."""

    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        self.value = VALUES[rank]

    def __str__(self):
        return f"{self.rank}{self.suit}"


class Deck:
    """Đại diện cho một bộ bài."""

    def __init__(self, num_decks: int = 1):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS] * num_decks
        self.shuffle()

    def shuffle(self):
        """Xáo trộn bộ bài."""
        random.shuffle(self.cards)

    def deal(self) -> Card:
        """Rút một lá bài từ bộ bài."""
        if not self.cards:
            # Tự động tạo và xáo trộn lại bộ bài nếu hết bài
            self.cards = [Card(s, r) for s in SUITS for r in RANKS]
            self.shuffle()
        return self.cards.pop()


class Hand:
    """Đại diện cho bài trên tay của một người chơi."""

    def __init__(self):
        self.cards: list[Card] = []
        self.value = 0
        self.aces = 0

    def add_card(self, card: Card):
        """Thêm một lá bài vào tay."""
        self.cards.append(card)
        self.value += card.value
        if card.rank == "A":
            self.aces += 1
        self.adjust_for_ace()

    def adjust_for_ace(self):
        """Điều chỉnh giá trị nếu có Át và tổng điểm > 21."""
        while self.value > 21 and self.aces:
            self.value -= 10
            self.aces -= 1

    def is_blackjack(self) -> bool:
        """Kiểm tra có phải là Blackjack (21 điểm với 2 lá)."""
        return self.value == 21 and len(self.cards) == 2


class Player:
    """Đại diện cho một người chơi."""

    def __init__(self, user_id: int, name: str):
        self.id = user_id
        self.name = name
        self.hand = Hand()
        self.is_standing = False

    def reset(self):
        """Reset lại tay bài và trạng thái của người chơi cho ván mới."""
        self.hand = Hand()
        self.is_standing = False


class Game:
    """Quản lý trạng thái và logic của một ván Xì Dách."""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.deck = Deck()
        self.players: dict[int, Player] = {}
        self.dealer = Player(user_id=0, name="Nhà Cái")
        self.state = GameState.WAITING_FOR_PLAYERS
        self.current_player_index = -1
        self.results: dict[int, GameResult] = {}
        self.player_order: list[int] = []

    def add_player(self, user_id: int, name: str):
        """Thêm người chơi mới vào ván."""
        if user_id not in self.players:
            self.players[user_id] = Player(user_id, name)

    def get_player(self, user_id: int) -> Player | None:
        """Lấy thông tin người chơi bằng user_id."""
        return self.players.get(user_id)

    def start_game(self):
        """Bắt đầu ván chơi, chia bài ban đầu."""
        if not self.players:
            raise ValueError("Không có người chơi nào để bắt đầu game.")

        self.state = GameState.PLAYERS_TURN
        self.player_order = list(self.players.keys())
        self.current_player_index = 0

        # Reset tất cả người chơi và nhà cái
        for player in self.players.values():
            player.reset()
        self.dealer.reset()
        self.results = {}

        # Chia bài
        for _ in range(2):
            for player_id in self.player_order:
                self.players[player_id].hand.add_card(self.deck.deal())
            self.dealer.hand.add_card(self.deck.deal())

        self._check_all_blackjacks()

    def get_current_player(self) -> Player | None:
        """Lấy người chơi đang trong lượt."""
        if (
            self.state == GameState.PLAYERS_TURN
            and 0 <= self.current_player_index < len(self.player_order)
        ):
            player_id = self.player_order[self.current_player_index]
            return self.players[player_id]
        return None

    def player_hit(self, user_id: int) -> bool:
        """Người chơi rút thêm bài."""
        player = self.get_player(user_id)
        if not player or self.get_current_player() != player:
            return False  # Không phải lượt của người này

        player.hand.add_card(self.deck.deal())
        if player.hand.value >= 21:
            self._next_player_turn()
        return True

    def player_stand(self, user_id: int) -> bool:
        """Người chơi dừng, không rút nữa."""
        player = self.get_player(user_id)
        if not player or self.get_current_player() != player:
            return False

        player.is_standing = True
        self._next_player_turn()
        return True

    def _check_all_blackjacks(self):
        """Kiểm tra ngay sau khi chia bài xem có ai được Blackjack không."""
        for player in self.players.values():
            if player.hand.is_blackjack():
                player.is_standing = True  # Tự động dằn bài

        # Nếu tất cả người chơi đều có blackjack hoặc quắc, chuyển lượt
        if all(p.is_standing or p.hand.value >
               21 for p in self.players.values()):
            self._start_dealer_turn()
        else:
            # Chuyển đến người chơi đầu tiên không bị Blackjack/quắc
            while self.get_current_player() and self.get_current_player().is_standing:
                self._next_player_turn()

    def _next_player_turn(self):
        """Chuyển lượt cho người chơi tiếp theo."""
        self.current_player_index += 1
        if self.current_player_index >= len(self.player_order):
            self._start_dealer_turn()
        else:
            # Bỏ qua những người chơi đã dằn bài (ví dụ: có blackjack)
            while self.get_current_player() and self.get_current_player().is_standing:
                self.current_player_index += 1
                if self.current_player_index >= len(self.player_order):
                    self._start_dealer_turn()
                    return

    def _start_dealer_turn(self):
        """Bắt đầu lượt của nhà cái."""
        self.state = GameState.DEALER_TURN
        # Nhà cái rút bài cho đến khi đạt 17 điểm trở lên
        while self.dealer.hand.value < 17:
            self.dealer.hand.add_card(self.deck.deal())
        self._end_game()

    def _end_game(self):
        """Kết thúc ván chơi và tính kết quả."""
        self.state = GameState.GAME_OVER
        dealer_value = self.dealer.hand.value

        for player in self.players.values():
            player_value = player.hand.value

            if player_value > 21:
                self.results[player.id] = GameResult.DEALER_WINS  # Quắc
            elif dealer_value > 21:
                # Nhà cái quắc
                self.results[player.id] = GameResult.PLAYER_WINS
            elif player_value > dealer_value:
                self.results[player.id] = GameResult.PLAYER_WINS  # Thắng
            elif player_value < dealer_value:
                self.results[player.id] = GameResult.DEALER_WINS  # Thua
            else:  # player_value == dealer_value
                # Xử lý trường hợp Blackjack
                player_bj = player.hand.is_blackjack()
                dealer_bj = self.dealer.hand.is_blackjack()
                if player_bj and not dealer_bj:
                    self.results[player.id] = GameResult.PLAYER_WINS
                elif not player_bj and dealer_bj:
                    self.results[player.id] = GameResult.DEALER_WINS
                else:
                    self.results[player.id] = GameResult.PUSH  # Hòa
