
# ==============================================================================
# File: blackjack/adapters/discord_presenter.py
# Mô tả: Lớp Adapter - Chuyển đổi trạng thái game (từ Entities) thành định dạng
# mà Discord có thể hiển thị (cụ thể là discord.Embed).
# ==============================================================================
import discord
from ..entities import Game, GameState, GameResult, Player

class DiscordPresenter:
    """Tạo các tin nhắn discord.Embed để hiển thị trạng thái game."""

    def _format_hand(self, player: Player, hide_one_card: bool = False) -> str:
        """Định dạng bài trên tay của người chơi."""
        if hide_one_card:
            # Chỉ hiển thị lá bài đầu tiên của nhà cái
            return f"[{str(player.hand.cards[0])}] [?]"
        
        cards_str = " ".join([f"[{str(card)}]" for card in player.hand.cards])
        return cards_str

    def _get_player_status(self, game: Game, player: Player) -> str:
        """Lấy trạng thái hiện tại của người chơi (ví dụ: BUSTED, BLACKJACK)."""
        if player.hand.value > 21:
            return " -  bù (Busted!)"
        if player.hand.is_blackjack():
            return " - Xì Dách (Blackjack!)"
        if player.is_standing:
            return " - đã dằn bài (Stand)"
        if game.get_current_player() == player:
            return " - 👈 **Lượt của bạn**"
        return ""

    def create_game_embed(self, game: Game) -> discord.Embed:
        """Tạo một discord.Embed để hiển thị toàn bộ trạng thái ván chơi."""
        if game.state == GameState.WAITING_FOR_PLAYERS:
            return self.create_waiting_embed(game)
        
        title = "♦️ Ván Xì Dách đang diễn ra! ♥️"
        color = discord.Color.gold()
        
        if game.state == GameState.GAME_OVER:
            title = "🏁 Ván Xì Dách đã kết thúc! 🏁"
            color = discord.Color.dark_red()

        embed = discord.Embed(title=title, color=color)

        # Hiển thị bài của nhà cái
        hide_dealer_card = game.state != GameState.GAME_OVER
        dealer_hand_str = self._format_hand(game.dealer, hide_one_card=hide_dealer_card)
        dealer_value = game.dealer.hand.value if not hide_dealer_card else game.dealer.hand.cards[0].value
        dealer_status = ""
        if game.state == GameState.GAME_OVER:
            if game.dealer.hand.value > 21:
                dealer_status = " - Bù (Busted!)"
            elif game.dealer.hand.is_blackjack():
                dealer_status = " - Xì Dách (Blackjack!)"

        embed.add_field(
            name=f"**Nhà Cái** (Điểm: {dealer_value}{dealer_status})",
            value=f"`{dealer_hand_str}`",
            inline=False
        )
        embed.add_field(name="-"*30, value="", inline=False)


        # Hiển thị bài của người chơi
        for player in game.players.values():
            player_hand_str = self._format_hand(player)
            player_status = self._get_player_status(game, player)
            
            field_name = f"**{player.name}** (Điểm: {player.hand.value}{player_status})"
            field_value = f"`{player_hand_str}`"
            
            if game.state == GameState.GAME_OVER:
                result = game.results.get(player.id)
                if result == GameResult.PLAYER_WINS:
                    field_value += "\n🎉 **Thắng!**"
                elif result == GameResult.DEALER_WINS:
                    field_value += "\n😢 **Thua!**"
                else:
                    field_value += "\n🤝 **Hòa!**"

            embed.add_field(name=field_name, value=field_value, inline=True)

        # Hướng dẫn
        current_player = game.get_current_player()
        if current_player:
            footer_text = f"Lượt của {current_player.name}. Dùng lệnh `!hit` để rút hoặc `!stand` để dằn."
            embed.set_footer(text=footer_text)
        elif game.state == GameState.GAME_OVER:
             embed.set_footer(text="Gõ !blackjack để bắt đầu ván mới.")

        return embed

    def create_waiting_embed(self, game: Game) -> discord.Embed:
        """Tạo embed cho phòng chờ."""
        embed = discord.Embed(
            title="🎲 Phòng chờ Xì Dách 🎲",
            description="Mọi người ơi, vào chơi nào! Gõ `!join` để tham gia.\nChủ phòng gõ `!start` để bắt đầu.",
            color=discord.Color.green()
        )
        player_list = "\n".join([p.name for p in game.players.values()])
        if not player_list:
            player_list = "Chưa có ai tham gia..."
        
        embed.add_field(name="Người chơi đã tham gia:", value=player_list, inline=False)
        return embed