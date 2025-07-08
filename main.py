# ==============================================================================
# File: main.py
# Mô tả: Điểm khởi đầu của ứng dụng.
# Thiết lập và chạy bot Discord.
# ==============================================================================
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from settings import LOG_LEVEL, COMMAND_PREFIX

# Import các thành phần đã tạo
from blackjack.use_cases import GameUseCase
from blackjack.adapters.memory_repository import MemoryGameRepository
from blackjack.adapters.discord_presenter import DiscordPresenter
from blackjack_cog import BlackjackCog

# Thiết lập logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("blackjack-bot")


# --- Dependency Injection Setup ---
# Đây là nơi chúng ta "tiêm" các phụ thuộc vào nhau.
# Ví dụ, UseCase cần một Repository, và Cog cần UseCase và Presenter.
def setup_dependencies() -> BlackjackCog:
    """Khởi tạo và kết nối các thành phần của ứng dụng."""
    game_repository = MemoryGameRepository()
    game_presenter = DiscordPresenter()
    game_use_case = GameUseCase(repo=game_repository)

    # Intents là cần thiết để bot có thể đọc tin nhắn và thông tin người dùng
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True  # Cần để lấy display_name

    # Xóa lệnh help mặc định để dùng lệnh tùy chỉnh trong Cog
    bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
    blackjack_cog = BlackjackCog(bot, use_case=game_use_case, presenter=game_presenter)
    return blackjack_cog


# --- Main Execution ---
async def main():
    # Tải biến môi trường từ file .env
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        logger.error("Lỗi: Vui lòng cung cấp DISCORD_TOKEN trong file .env")
        return

    # Thiết lập các thành phần
    blackjack_cog = setup_dependencies()

    @blackjack_cog.bot.event
    async def on_ready():
        logger.info(f"Bot đã đăng nhập với tên {blackjack_cog.bot.user}")
        logger.info("Bot đã sẵn sàng để nhận lệnh!")
        print("------")

    # Thêm Cog vào bot và chạy
    await blackjack_cog.bot.add_cog(blackjack_cog)
    logger.info("Đã thêm BlackjackCog vào bot.")
    await blackjack_cog.bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio

    try:
        logger.info("Starting bot...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot đang tắt.")
