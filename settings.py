import os
from dotenv import load_dotenv

load_dotenv()

# Timeout phòng chờ (giây)
WAITING_ROOM_TIMEOUT = int(os.getenv("BLACKJACK_WAITING_ROOM_TIMEOUT", 300))

# Log level
LOG_LEVEL = os.getenv("BLACKJACK_LOG_LEVEL", "INFO")

# Command prefix
COMMAND_PREFIX = os.getenv("BLACKJACK_COMMAND_PREFIX", "/")

# Timeout cho lượt chơi của người chơi (giây)
PLAYER_TURN_TIMEOUT = int(os.getenv("BLACKJACK_PLAYER_TURN_TIMEOUT", 60))
