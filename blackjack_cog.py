# ==============================================================================
# File: blackjack_cog.py
# Mô tả: Lớp Framework - Đây là nơi code tương tác trực tiếp với discord.py.
# Nó sử dụng Use Cases để thực hiện hành động và Presenter để hiển thị kết quả.
# ==============================================================================
import discord
from discord.ext import commands
from discord import app_commands
from blackjack.use_cases import GameUseCase
from blackjack.adapters.discord_presenter import DiscordPresenter
from blackjack.entities import GameState
import asyncio
from settings import WAITING_ROOM_TIMEOUT, PLAYER_TURN_TIMEOUT
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
        self.player_turn_timeouts = {}  # channel_id: asyncio.Task
        self.logger = logging.getLogger("blackjack-bot.cog")

    async def _send_message(self, ctx, *args, **kwargs):
        # Helper to send message correctly for both classic and slash commands
        if hasattr(ctx, "interaction") and ctx.interaction is not None:
            interaction = ctx.interaction
            if not interaction.response.is_done():
                await interaction.response.send_message(*args, **kwargs)
            else:
                await interaction.followup.send(*args, **kwargs)
        else:
            await ctx.send(*args, **kwargs)

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

    async def _start_player_turn_timeout(
        self, channel_id: int, player_id: int, ctx: commands.Context
    ):
        self._cancel_player_turn_timeout(channel_id)
        # Gửi mention khi tới lượt mới
        mention_msg = f"<@{player_id}>, tới lượt bạn!"
        await self._send_message(ctx, mention_msg)
        self.player_turn_timeouts[channel_id] = asyncio.create_task(
            self._player_turn_timeout(channel_id, player_id, ctx)
        )

    async def _player_turn_timeout(
        self, channel_id: int, player_id: int, ctx: commands.Context
    ):
        await asyncio.sleep(PLAYER_TURN_TIMEOUT)
        game = self.use_case.repo.get_game(channel_id)
        if (
            game
            and game.state == GameState.PLAYERS_TURN
            and game.get_current_player() is not None
            and game.get_current_player().id == player_id
        ):
            await self._send_message(
                ctx, f"⏰ <@{player_id}> đã hết thời gian lượt chơi và bị bỏ lượt!"
            )
            try:
                game = self.use_case.player_action(channel_id, player_id, "stand")
                embed = self.presenter.create_channel_embed(game)
                await self._send_message(ctx, embed=embed)
                if game.state == GameState.GAME_OVER:
                    final_embed = self.presenter.create_final_result_embed(game)
                    await self._send_message(ctx, embed=final_embed)
                    self.use_case.end_game(channel_id)
                    if channel_id in self.game_starters:
                        del self.game_starters[channel_id]
                else:
                    current = game.get_current_player()
                    if current:
                        await self._start_player_turn_timeout(
                            channel_id, current.id, ctx
                        )
            except Exception as e:
                self.logger.warning(
                    f"Lỗi khi tự động stand cho player {player_id} ở channel {channel_id}: {e}"
                )
        self.player_turn_timeouts.pop(channel_id, None)

    def _cancel_player_turn_timeout(self, channel_id: int):
        if channel_id in self.player_turn_timeouts:
            self.player_turn_timeouts[channel_id].cancel()
            del self.player_turn_timeouts[channel_id]

    # XÓA các hàm và logic liên quan đến gửi DM/inbox
    # 1. Xóa _check_dm_permission
    # 2. Xóa _send_dm_to_all_players
    # 3. Xóa mọi chỗ gọi self._check_dm_permission và self._send_dm_to_all_players
    # 4. Chỉ trả kết quả qua slash command/channel

    # --- XÓA _check_dm_permission và _send_dm_to_all_players ---
    # (Không cần thay thế, chỉ xóa)

    # --- Sửa các lệnh: bỏ kiểm tra DM và gửi DM ---
    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx: commands.Context):
        """Bắt đầu một phòng chờ game Xì Dách."""
        game = self.use_case.repo.get_game(ctx.channel.id)
        if game and game.state in (
            GameState.WAITING_FOR_PLAYERS,
            GameState.PLAYERS_TURN,
            GameState.DEALER_TURN,
        ):
            await self._send_message(
                ctx,
                "❌ Đã có một phòng chờ/game đang diễn ra trong kênh này. Hãy kết thúc ván hiện tại trước khi tạo mới.",
            )
            self.logger.warning(
                f"Channel {ctx.channel.id} đã có game active, không tạo mới."
            )
            return
        # KHÔNG kiểm tra DM nữa
        game, joined = self.use_case.join_game(
            ctx.channel.id, ctx.author.id, ctx.author.display_name
        )
        self.game_starters[ctx.channel.id] = ctx.author.id
        self.logger.info(
            f"Tạo phòng chờ mới ở channel {ctx.channel.id} bởi user {ctx.author.id} ({ctx.author.display_name})"
        )
        embed = self.presenter.create_waiting_embed(game)
        await self._send_message(ctx, embed=embed)
        if ctx.channel.id not in self.waiting_room_timeouts:
            self.waiting_room_timeouts[ctx.channel.id] = asyncio.create_task(
                self._waiting_room_timeout(ctx.channel.id, ctx)
            )

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        """Tham gia vào một ván Xì Dách đang chờ."""
        try:
            # KHÔNG kiểm tra DM nữa
            game, joined = self.use_case.join_game(
                ctx.channel.id, ctx.author.id, ctx.author.display_name
            )
            # Gửi thông báo join thành công ngay lập tức (và defer nếu là slash command)
            join_msg = f"{ctx.author.display_name} đã tham gia ván đấu!"
            if hasattr(ctx, "interaction") and ctx.interaction is not None:
                interaction = ctx.interaction
                if not interaction.response.is_done():
                    await interaction.response.defer(thinking=False)
                await interaction.followup.send(join_msg)
            else:
                await self._send_message(ctx, join_msg)
            if joined:
                self.logger.info(
                    f"User {ctx.author.id} ({ctx.author.display_name}) join phòng chờ channel {ctx.channel.id}"
                )
                embed = self.presenter.create_waiting_embed(game)
                await self._send_message(ctx, embed=embed)
                if (
                    ctx.channel.id in self.waiting_room_timeouts
                    and len(game.players) > 1
                ):
                    self.waiting_room_timeouts[ctx.channel.id].cancel()
                    del self.waiting_room_timeouts[ctx.channel.id]
            else:
                await self._send_message(
                    ctx, f"{ctx.author.display_name}, bạn đã ở trong phòng chờ rồi."
                )
        except RuntimeError as e:
            self.logger.warning(
                f"User {ctx.author.id} join phòng chờ channel {ctx.channel.id} lỗi: {e}"
            )
            await self._send_message(ctx, f"Lỗi: {e}")

    @commands.command(name="start")
    async def start(self, ctx: commands.Context):
        """Bắt đầu ván chơi với những người đã tham gia."""
        starter = self.game_starters.get(ctx.channel.id)
        if starter != ctx.author.id:
            await self._send_message(
                ctx, "Chỉ người tạo phòng chờ mới có thể bắt đầu ván đấu."
            )
            self.logger.warning(
                f"User {ctx.author.id} cố gắng start game ở channel {ctx.channel.id} nhưng không phải starter."
            )
            return
        game = self.use_case.repo.get_game(ctx.channel.id)
        if not game or not game.players:
            await self._send_message(ctx, "Không có ai trong phòng chờ để bắt đầu.")
            self.logger.warning(
                f"Channel {ctx.channel.id} không có ai trong phòng chờ khi start."
            )
            return
        if game.state != GameState.WAITING_FOR_PLAYERS:
            await self._send_message(ctx, "Ván chơi đã bắt đầu rồi.")
            self.logger.warning(
                f"Channel {ctx.channel.id} đã start game khi game đã chạy."
            )
            return
        players_data = {p.id: p.name for p in game.players.values()}
        game = self.use_case.start_new_game(ctx.channel.id, players_data)
        self.logger.info(
            f"Game bắt đầu ở channel {ctx.channel.id} với {len(players_data)} người chơi."
        )
        # Gửi bài riêng cho chính người gọi lệnh nếu là slash command
        if hasattr(ctx, "interaction") and ctx.interaction is not None:
            interaction = ctx.interaction
            player = game.players.get(ctx.author.id)
            if player:
                player_embed = self.presenter.create_player_dm_embed(game, player)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=player_embed, ephemeral=True
                    )
                else:
                    await interaction.followup.send(embed=player_embed, ephemeral=True)
        else:
            # Classic: gửi công khai cho tất cả
            for player in game.players.values():
                player_embed = self.presenter.create_player_dm_embed(game, player)
                await self._send_message(ctx, embed=player_embed)
        # Gửi trạng thái toàn bộ bàn chơi công khai
        embed = self.presenter.create_channel_embed(game)
        await self._send_message(ctx, embed=embed)
        if game.state == GameState.GAME_OVER:
            final_embed = self.presenter.create_final_result_embed(game)
            await self._send_message(ctx, embed=final_embed)
            self.use_case.end_game(ctx.channel.id)
            if ctx.channel.id in self.game_starters:
                del self.game_starters[ctx.channel.id]
        else:
            current = game.get_current_player()
            if current:
                await self._start_player_turn_timeout(ctx.channel.id, current.id, ctx)
        if ctx.channel.id in self.waiting_room_timeouts:
            self.waiting_room_timeouts[ctx.channel.id].cancel()
            del self.waiting_room_timeouts[ctx.channel.id]

    @commands.command(name="hit")
    async def hit(self, ctx: commands.Context):
        """Rút thêm một lá bài."""
        try:
            self._cancel_player_turn_timeout(ctx.channel.id)
            game = self.use_case.player_action(ctx.channel.id, ctx.author.id, "hit")
            # Gửi embed riêng cho người chơi (ephemeral nếu là slash command)
            player = game.players.get(ctx.author.id)
            if player:
                player_embed = self.presenter.create_player_dm_embed(game, player)
                if hasattr(ctx, "interaction") and ctx.interaction is not None:
                    interaction = ctx.interaction
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            embed=player_embed, ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            embed=player_embed, ephemeral=True
                        )
                else:
                    await self._send_message(ctx, embed=player_embed)
            # Sau đó gửi trạng thái toàn bộ bàn chơi (luôn công khai)
            embed = self.presenter.create_channel_embed(game)
            await self._send_message(ctx, embed=embed)
            # KHÔNG gửi DM nữa
            if game.state == GameState.GAME_OVER:
                final_embed = self.presenter.create_final_result_embed(game)
                await self._send_message(ctx, embed=final_embed)
                self.use_case.end_game(ctx.channel.id)
                if ctx.channel.id in self.game_starters:
                    del self.game_starters[ctx.channel.id]
            else:
                current = game.get_current_player()
                if current:
                    await self._start_player_turn_timeout(
                        ctx.channel.id, current.id, ctx
                    )
        except (ValueError, PermissionError) as e:
            await self._send_message(ctx, f"{ctx.author.mention}, {e}")

    @commands.command(name="stand")
    async def stand(self, ctx: commands.Context):
        """Dừng, không rút bài nữa."""
        try:
            self._cancel_player_turn_timeout(ctx.channel.id)
            game = self.use_case.player_action(ctx.channel.id, ctx.author.id, "stand")
            embed = self.presenter.create_channel_embed(game)
            await self._send_message(ctx, embed=embed)
            # KHÔNG gửi DM nữa
            if game.state == GameState.GAME_OVER:
                final_embed = self.presenter.create_final_result_embed(game)
                await self._send_message(ctx, embed=final_embed)
                self.use_case.end_game(ctx.channel.id)
                if ctx.channel.id in self.game_starters:
                    del self.game_starters[ctx.channel.id]
            else:
                current = game.get_current_player()
                if current:
                    await self._start_player_turn_timeout(
                        ctx.channel.id, current.id, ctx
                    )
        except (ValueError, PermissionError) as e:
            await self._send_message(ctx, f"{ctx.author.mention}, {e}")

    @commands.command(name="end", aliases=["stop"])
    async def end_game_command(self, ctx: commands.Context):
        """Buộc kết thúc ván chơi hiện tại."""
        starter = self.game_starters.get(ctx.channel.id)
        # Cho phép người tạo phòng hoặc người có quyền quản lý kênh kết thúc
        if starter == ctx.author.id or ctx.author.guild_permissions.manage_channels:
            self.use_case.end_game(ctx.channel.id)
            if ctx.channel.id in self.game_starters:
                del self.game_starters[ctx.channel.id]
            await self._send_message(ctx, "Đã kết thúc ván chơi hiện tại.")
            self.logger.info(
                f"Game ở channel {ctx.channel.id} đã bị kết thúc bởi user {ctx.author.id} ({ctx.author.display_name})"
            )
            # Hủy timeout nếu có
            if ctx.channel.id in self.waiting_room_timeouts:
                self.waiting_room_timeouts[ctx.channel.id].cancel()
                del self.waiting_room_timeouts[ctx.channel.id]
            if ctx.channel.id in self.player_turn_timeouts:
                self.player_turn_timeouts[ctx.channel.id].cancel()
                del self.player_turn_timeouts[ctx.channel.id]
        else:
            await self._send_message(ctx, "Bạn không có quyền kết thúc ván chơi này.")
            self.logger.warning(
                f"User {ctx.author.id} cố gắng end game ở channel {ctx.channel.id} nhưng không có quyền."
            )

    # --- SLASH COMMANDS ---
    @app_commands.command(
        name="blackjack", description="Bắt đầu một phòng chờ game Xì Dách."
    )
    async def slash_blackjack(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.blackjack(ctx)

    @app_commands.command(
        name="join", description="Tham gia vào một ván Xì Dách đang chờ."
    )
    async def slash_join(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.join(ctx)

    @app_commands.command(
        name="start", description="Bắt đầu ván chơi với những người đã tham gia."
    )
    async def slash_start(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.start(ctx)

    @app_commands.command(name="hit", description="Rút thêm một lá bài.")
    async def slash_hit(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.hit(ctx)

    @app_commands.command(name="stand", description="Dừng, không rút bài nữa.")
    async def slash_stand(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.stand(ctx)

    @app_commands.command(name="end", description="Buộc kết thúc ván chơi hiện tại.")
    async def slash_end(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.end_game_command(ctx)

    @app_commands.command(
        name="myhand", description="Xem bài hiện tại của bạn (ephemeral)"
    )
    async def slash_myhand(self, interaction: discord.Interaction):
        """Trả về bài hiện tại của người gọi (ephemeral)."""
        ctx = await self.bot.get_context(interaction)
        game = self.use_case.repo.get_game(ctx.channel.id)
        if not game or interaction.user.id not in game.players:
            await interaction.response.send_message(
                "Bạn chưa tham gia hoặc chưa có ván nào đang diễn ra!", ephemeral=True
            )
            return
        player = game.players.get(interaction.user.id)
        if player:
            player_embed = self.presenter.create_player_dm_embed(game, player)
            await interaction.response.send_message(embed=player_embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "Không tìm thấy bài của bạn!", ephemeral=True
            )

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """Hiển thị bảng hướng dẫn các lệnh."""
        embed = discord.Embed(
            title="♦️ Hướng dẫn chơi Xì Dách ♥️",
            description="Dưới đây là danh sách các slash command bạn có thể dùng:",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="`/blackjack`",
            value="Bắt đầu một phòng chờ mới để mọi người cùng tham gia.",
            inline=False,
        )
        embed.add_field(
            name="`/join`",
            value="Tham gia vào phòng chờ đang mở trong kênh này.",
            inline=False,
        )
        embed.add_field(
            name="`/start`",
            value="Bắt đầu ván đấu. (Chỉ người tạo phòng chờ mới dùng được)",
            inline=False,
        )
        embed.add_field(
            name="`/hit`",
            value="Rút thêm một lá bài khi đến lượt của bạn.",
            inline=False,
        )
        embed.add_field(
            name="`/stand`",
            value="Dằn bài, không rút nữa và kết thúc lượt của bạn.",
            inline=False,
        )
        embed.add_field(
            name="`/myhand`",
            value="Xem bài hiện tại của bạn (chỉ mình bạn thấy).",
            inline=False,
        )
        embed.add_field(
            name="`/end`",
            value="Buộc kết thúc ván chơi hiện tại. (Chỉ người tạo phòng hoặc admin)",
            inline=False,
        )
        embed.set_footer(
            text="Hãy dùng slash command (gõ /) để xem danh sách lệnh. Chúc bạn chơi game vui vẻ!"
        )
        await self._send_message(ctx, embed=embed)

    @app_commands.command(name="help", description="Hiển thị bảng hướng dẫn các lệnh.")
    async def slash_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="♦️ Hướng dẫn chơi Xì Dách ♥️",
            description="Dưới đây là danh sách các slash command bạn có thể dùng:",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="`/blackjack`",
            value="Bắt đầu một phòng chờ mới để mọi người cùng tham gia.",
            inline=False,
        )
        embed.add_field(
            name="`/join`",
            value="Tham gia vào phòng chờ đang mở trong kênh này.",
            inline=False,
        )
        embed.add_field(
            name="`/start`",
            value="Bắt đầu ván đấu. (Chỉ người tạo phòng chờ mới dùng được)",
            inline=False,
        )
        embed.add_field(
            name="`/hit`",
            value="Rút thêm một lá bài khi đến lượt của bạn.",
            inline=False,
        )
        embed.add_field(
            name="`/stand`",
            value="Dằn bài, không rút nữa và kết thúc lượt của bạn.",
            inline=False,
        )
        embed.add_field(
            name="`/myhand`",
            value="Xem bài hiện tại của bạn (chỉ mình bạn thấy).",
            inline=False,
        )
        embed.add_field(
            name="`/end`",
            value="Buộc kết thúc ván chơi hiện tại. (Chỉ người tạo phòng hoặc admin)",
            inline=False,
        )
        embed.set_footer(
            text="Hãy dùng slash command (gõ /) để xem danh sách lệnh. Chúc bạn chơi game vui vẻ!"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
