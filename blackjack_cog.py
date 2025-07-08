# ==============================================================================
# File: blackjack_cog.py
# Mô tả: Lớp Framework - Đây là nơi code tương tác trực tiếp với discord.py.
# Nó sử dụng Use Cases để thực hiện hành động và Presenter để hiển thị kết quả.
# ==============================================================================
import discord
from discord.ext import commands
from blackjack.use_cases import GameUseCase
from blackjack.adapters.discord_presenter import DiscordPresenter
from blackjack.entities import GameState
import asyncio
from settings import WAITING_ROOM_TIMEOUT, COMMAND_PREFIX
import logging
from datetime import datetime


class BlackjackCog(commands.Cog):
    """Một Cog chứa các lệnh để chơi game Xì Dách."""

    def __init__(
        self, bot: commands.Bot, use_case: GameUseCase, presenter: DiscordPresenter
    ):
        self.bot = bot
        self.use_case = use_case
        self.presenter = presenter
        # Lưu trữ người khởi tạo phòng chờ để chỉ họ có quyền bắt đầu
        self.game_starters = {}
        # Lưu trữ task timeout cho từng phòng chờ
        self.waiting_room_timeouts = {}  # channel_id: asyncio.Task
        self.logger = logging.getLogger("blackjack-bot.cog")

    async def _waiting_room_timeout(self, channel_id: int, ctx: commands.Context):
        await asyncio.sleep(WAITING_ROOM_TIMEOUT)  # timeout lấy từ settings
        game = self.use_case.repo.get_game(channel_id)
        if (
            game
            and game.state == GameState.WAITING_FOR_PLAYERS
            and len(game.players) <= 1
        ):
            self.logger.info(f"Timeout phòng chờ channel {channel_id}, tự động đóng.")
            self.use_case.end_game(channel_id)
            if channel_id in self.game_starters:
                del self.game_starters[channel_id]
            await ctx.send(
                "⏰ Phòng chờ đã bị đóng do không có ai tham gia sau 5 phút."
            )
        self.waiting_room_timeouts.pop(channel_id, None)

    async def _check_dm_permission(self, user_id: int) -> bool:
        """Kiểm tra xem có thể gửi DM cho user không."""
        try:
            user = await self.bot.fetch_user(user_id)
            # Thử gửi một tin nhắn test để kiểm tra
            current_date = datetime.now().strftime("%d/%m/%Y")

            test_embed = discord.Embed(
                title="🎮 Chào mừng bạn đến với Xì Dách Bot!",
                description=f"Xin chào! Đây là tin nhắn kiểm tra để đảm bảo bot có thể gửi thông tin game cho bạn.\n\n📅 Ngày: {current_date}\n🎲 Sẵn sàng chơi Xì Dách chưa?",
                color=discord.Color.green(),
            )
            test_embed.set_footer(
                text="Bot sẽ gửi thông tin bài của bạn qua đây trong khi chơi!"
            )
            await user.send(embed=test_embed)
            return True
        except discord.Forbidden:
            # User đã chặn DM từ bot
            return False
        except Exception as e:
            # Lỗi khác (user không tồn tại, v.v.)
            self.logger.warning(f"Lỗi khi kiểm tra DM cho user {user_id}: {e}")
            return False

    async def _send_dm_to_all_players(self, game, embed_func):
        """Gửi DM cho tất cả người chơi."""
        for player in game.players.values():
            try:
                user = await self.bot.fetch_user(player.id)
                embed = embed_func(game, player)
                await user.send(embed=embed)
            except Exception as e:
                self.logger.warning(f"Không thể gửi DM cho user {player.id}: {e}")

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """Hiển thị bảng hướng dẫn các lệnh."""
        embed = discord.Embed(
            title="♦️ Hướng dẫn chơi Xì Dách ♥️",
            description="Dưới đây là danh sách các lệnh bạn có thể dùng:",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name=f"`{COMMAND_PREFIX}blackjack` hoặc `{COMMAND_PREFIX}bj`",
            value="Bắt đầu một phòng chờ mới để mọi người cùng tham gia.",
            inline=False,
        )
        embed.add_field(
            name=f"`{COMMAND_PREFIX}join`",
            value="Tham gia vào phòng chờ đang mở trong kênh này.",
            inline=False,
        )
        embed.add_field(
            name=f"`{COMMAND_PREFIX}start`",
            value="Bắt đầu ván đấu. (Chỉ người tạo phòng chờ mới dùng được)",
            inline=False,
        )
        embed.add_field(
            name=f"`{COMMAND_PREFIX}hit`",
            value="Rút thêm một lá bài khi đến lượt của bạn.",
            inline=False,
        )
        embed.add_field(
            name=f"`{COMMAND_PREFIX}stand`",
            value="Dằn bài, không rút nữa và kết thúc lượt của bạn.",
            inline=False,
        )
        embed.add_field(
            name=f"`{COMMAND_PREFIX}end` hoặc `{COMMAND_PREFIX}stop`",
            value="Buộc kết thúc ván chơi hiện tại. (Chỉ người tạo phòng hoặc admin)",
            inline=False,
        )
        embed.set_footer(text="Chúc bạn chơi game vui vẻ!")

        await ctx.send(embed=embed)

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx: commands.Context):
        """Bắt đầu một phòng chờ game Xì Dách."""
        # Kiểm tra nếu đã có game đang chờ hoặc đang chơi ở channel này
        game = self.use_case.repo.get_game(ctx.channel.id)
        if game and game.state in (
            GameState.WAITING_FOR_PLAYERS,
            GameState.PLAYERS_TURN,
            GameState.DEALER_TURN,
        ):
            await ctx.send(
                "❌ Đã có một phòng chờ/game đang diễn ra trong kênh này. Hãy kết thúc ván hiện tại trước khi tạo mới."
            )
            self.logger.warning(
                f"Channel {ctx.channel.id} đã có game active, không tạo mới."
            )
            return

        # Kiểm tra khả năng gửi DM trước khi tạo phòng chờ
        can_dm = await self._check_dm_permission(ctx.author.id)
        if not can_dm:
            await ctx.send(
                f"❌ {ctx.author.mention}, bot không thể gửi tin nhắn riêng cho bạn. "
                "Vui lòng bật DM từ server members trong cài đặt Discord để tham gia game."
            )
            self.logger.warning(
                f"User {ctx.author.id} không thể nhận DM, không cho phép tạo phòng chờ."
            )
            return

        # Nếu không có, tạo phòng chờ mới
        game, joined = self.use_case.join_game(
            ctx.channel.id, ctx.author.id, ctx.author.display_name
        )
        self.game_starters[ctx.channel.id] = ctx.author.id
        self.logger.info(
            f"Tạo phòng chờ mới ở channel {ctx.channel.id} bởi user {ctx.author.id} ({ctx.author.display_name})"
        )
        embed = self.presenter.create_waiting_embed(game)
        await ctx.send(embed=embed)
        # await ctx.send(content="@here Có ai chơi Xì Dách không? Vào lẹ!", embed=embed)
        # Tạo task timeout nếu chưa có
        if ctx.channel.id not in self.waiting_room_timeouts:
            self.waiting_room_timeouts[ctx.channel.id] = asyncio.create_task(
                self._waiting_room_timeout(ctx.channel.id, ctx)
            )

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        """Tham gia vào một ván Xì Dách đang chờ."""
        try:
            # Kiểm tra khả năng gửi DM trước khi cho phép join
            can_dm = await self._check_dm_permission(ctx.author.id)
            if not can_dm:
                await ctx.send(
                    f"❌ {ctx.author.mention}, bot không thể gửi tin nhắn riêng cho bạn. "
                    "Vui lòng bật DM từ server members trong cài đặt Discord để tham gia game."
                )
                self.logger.warning(
                    f"User {ctx.author.id} không thể nhận DM, không cho phép join game."
                )
                return

            game, joined = self.use_case.join_game(
                ctx.channel.id, ctx.author.id, ctx.author.display_name
            )
            if joined:
                self.logger.info(
                    f"User {ctx.author.id} ({ctx.author.display_name}) join phòng chờ channel {ctx.channel.id}"
                )
                await ctx.send(f"{ctx.author.display_name} đã tham gia ván đấu!")
                embed = self.presenter.create_waiting_embed(game)
                await ctx.send(embed=embed)
                # Nếu có nhiều hơn 1 người chơi, hủy timeout
                if (
                    ctx.channel.id in self.waiting_room_timeouts
                    and len(game.players) > 1
                ):
                    self.waiting_room_timeouts[ctx.channel.id].cancel()
                    del self.waiting_room_timeouts[ctx.channel.id]
            else:
                await ctx.send(
                    f"{ctx.author.display_name}, bạn đã ở trong phòng chờ rồi."
                )
        except RuntimeError as e:
            self.logger.warning(
                f"User {ctx.author.id} join phòng chờ channel {ctx.channel.id} lỗi: {e}"
            )
            await ctx.send(f"Lỗi: {e}")

    @commands.command(name="start")
    async def start(self, ctx: commands.Context):
        """Bắt đầu ván chơi với những người đã tham gia."""
        starter = self.game_starters.get(ctx.channel.id)
        if starter != ctx.author.id:
            await ctx.send("Chỉ người tạo phòng chờ mới có thể bắt đầu ván đấu.")
            self.logger.warning(
                f"User {ctx.author.id} cố gắng start game ở channel {ctx.channel.id} nhưng không phải starter."
            )
            return

        game = self.use_case.repo.get_game(ctx.channel.id)
        if not game or not game.players:
            await ctx.send("Không có ai trong phòng chờ để bắt đầu.")
            self.logger.warning(
                f"Channel {ctx.channel.id} không có ai trong phòng chờ khi start."
            )
            return

        if game.state != GameState.WAITING_FOR_PLAYERS:
            await ctx.send("Ván chơi đã bắt đầu rồi.")
            self.logger.warning(
                f"Channel {ctx.channel.id} đã start game khi game đã chạy."
            )
            return

        players_data = {p.id: p.name for p in game.players.values()}
        game = self.use_case.start_new_game(ctx.channel.id, players_data)

        self.logger.info(
            f"Game bắt đầu ở channel {ctx.channel.id} với {len(players_data)} người chơi."
        )

        # Hiển thị trạng thái trên channel
        embed = self.presenter.create_channel_embed(game)
        await ctx.send(embed=embed)

        # Gửi DM cho tất cả người chơi
        await self._send_dm_to_all_players(game, self.presenter.create_player_dm_embed)

        # Nếu game kết thúc ngay lập tức (ví dụ: mọi người đều có blackjack)
        if game.state == GameState.GAME_OVER:
            # Hiển thị kết quả cuối cùng trên channel
            final_embed = self.presenter.create_final_result_embed(game)
            await ctx.send(embed=final_embed)

            self.use_case.end_game(ctx.channel.id)
            if ctx.channel.id in self.game_starters:
                del self.game_starters[ctx.channel.id]
        # Hủy timeout nếu có
        if ctx.channel.id in self.waiting_room_timeouts:
            self.waiting_room_timeouts[ctx.channel.id].cancel()
            del self.waiting_room_timeouts[ctx.channel.id]

    @commands.command(name="hit")
    async def hit(self, ctx: commands.Context):
        """Rút thêm một lá bài."""
        try:
            game = self.use_case.player_action(ctx.channel.id, ctx.author.id, "hit")

            # Hiển thị trạng thái trên channel
            embed = self.presenter.create_channel_embed(game)
            await ctx.send(embed=embed)

            # Gửi DM cho tất cả người chơi
            await self._send_dm_to_all_players(
                game, self.presenter.create_player_dm_embed
            )

            if game.state == GameState.GAME_OVER:
                # Hiển thị kết quả cuối cùng trên channel
                final_embed = self.presenter.create_final_result_embed(game)
                await ctx.send(embed=final_embed)

                self.use_case.end_game(ctx.channel.id)
                if ctx.channel.id in self.game_starters:
                    del self.game_starters[ctx.channel.id]

        except (ValueError, PermissionError) as e:
            await ctx.send(f"{ctx.author.mention}, {e}")

    @commands.command(name="stand")
    async def stand(self, ctx: commands.Context):
        """Dừng, không rút bài nữa."""
        try:
            game = self.use_case.player_action(ctx.channel.id, ctx.author.id, "stand")

            # Hiển thị trạng thái trên channel
            embed = self.presenter.create_channel_embed(game)
            await ctx.send(embed=embed)

            # Gửi DM cho tất cả người chơi
            await self._send_dm_to_all_players(
                game, self.presenter.create_player_dm_embed
            )

            if game.state == GameState.GAME_OVER:
                # Hiển thị kết quả cuối cùng trên channel
                final_embed = self.presenter.create_final_result_embed(game)
                await ctx.send(embed=final_embed)

                self.use_case.end_game(ctx.channel.id)
                if ctx.channel.id in self.game_starters:
                    del self.game_starters[ctx.channel.id]

        except (ValueError, PermissionError) as e:
            await ctx.send(f"{ctx.author.mention}, {e}")

    @commands.command(name="end", aliases=["stop"])
    async def end_game_command(self, ctx: commands.Context):
        """Buộc kết thúc ván chơi hiện tại."""
        starter = self.game_starters.get(ctx.channel.id)
        # Cho phép người tạo phòng hoặc người có quyền quản lý kênh kết thúc
        if starter == ctx.author.id or ctx.author.guild_permissions.manage_channels:
            self.use_case.end_game(ctx.channel.id)
            if ctx.channel.id in self.game_starters:
                del self.game_starters[ctx.channel.id]
            await ctx.send("Đã kết thúc ván chơi hiện tại.")
            self.logger.info(
                f"Game ở channel {ctx.channel.id} đã bị kết thúc bởi user {ctx.author.id} ({ctx.author.display_name})"
            )
            # Hủy timeout nếu có
            if ctx.channel.id in self.waiting_room_timeouts:
                self.waiting_room_timeouts[ctx.channel.id].cancel()
                del self.waiting_room_timeouts[ctx.channel.id]
        else:
            await ctx.send("Bạn không có quyền kết thúc ván chơi này.")
            self.logger.warning(
                f"User {ctx.author.id} cố gắng end game ở channel {ctx.channel.id} nhưng không có quyền."
            )
