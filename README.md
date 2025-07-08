# 🎮 Discord Blackjack Bot

A Discord bot for playing Blackjack (Xì Dách) with privacy-focused design - player cards are sent via DM while only current turn and dealer info are shown publicly.

[![Build status](https://github.com/diepthuyhan/discordbot-blackjack/actions/workflows/docker-build.yml/badge.svg?branch=master)](https://github.com/diepthuyhan/discordbot-blackjack/actions/workflows/docker-build.yml)

## ✨ Features

- **🎲 Full Blackjack Game**: Complete implementation with all standard rules
- **🔒 Privacy-First Design**: Player cards sent via DM, only public info on channel
- **👥 Multi-Player Support**: Multiple players can join and play together
- **⏰ Auto Timeout**: Waiting rooms auto-close after inactivity
- **🛡️ DM Validation**: Checks DM permissions before allowing players to join
- **🎨 Rich Embeds**: Beautiful Discord embeds for game display
- **🔧 Configurable**: Command prefix and settings via environment variables

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Discord Bot Token
- Docker (optional, for containerized deployment)

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token_here

# Optional (with defaults)
BLACKJACK_COMMAND_PREFIX=^
BLACKJACK_WAITING_ROOM_TIMEOUT=300
BLACKJACK_LOG_LEVEL=INFO
```

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/discord-bot-game-choi-bai.git
   cd discord-bot-game-choi-bai
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the bot**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -f _docker/Dockerfile -t discord-blackjack-bot .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name discord-blackjack-bot \
     -e DISCORD_TOKEN=your_token_here \
     -e BLACKJACK_COMMAND_PREFIX=^ \
     discord-blackjack-bot
   ```

## 🎮 Game Commands

| Command | Description |
|---------|-------------|
| `^help` | Show help and available commands |
| `^blackjack` or `^bj` | Create a new waiting room |
| `^join` | Join an existing waiting room |
| `^start` | Start the game (room creator only) |
| `^hit` | Draw a card (during your turn) |
| `^stand` | Stand with current hand (during your turn) |
| `^end` or `^stop` | Force end current game (creator/admin only) |

## 🏗️ Architecture

The project follows Clean Architecture principles with clear separation of concerns:

```
discord-bot-game-choi-bai/
├── blackjack/                 # Core game logic
│   ├── entities.py           # Game entities (Card, Deck, Hand, Player, Game)
│   ├── interfaces.py         # Abstract interfaces
│   ├── use_cases.py          # Business logic
│   └── adapters/             # External integrations
│       ├── discord_presenter.py  # Discord display logic
│       └── memory_repository.py  # In-memory data storage
├── blackjack_cog.py          # Discord.py integration
├── main.py                   # Application entry point
├── settings.py               # Configuration management
└── _docker/                  # Docker configuration
    └── Dockerfile
```

### Key Components

- **Entities**: Pure game logic, no external dependencies
- **Use Cases**: Business rules and game flow
- **Adapters**: Discord integration and data persistence
- **Cog**: Discord.py command handling

## 🔧 Configuration

### Command Prefix

Change the command prefix via environment variable:

```bash
export BLACKJACK_COMMAND_PREFIX=?
# Now commands become: ?blackjack, ?join, ?hit, etc.
```

### Waiting Room Timeout

Adjust how long waiting rooms stay open:

```bash
export BLACKJACK_WAITING_ROOM_TIMEOUT=600  # 10 minutes
```

### Log Level

Set logging verbosity:

```bash
export BLACKJACK_LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

## 🛡️ Privacy Features

### DM-Based Card Display

- **Public Channel**: Shows only current turn and dealer information
- **Private DM**: Each player receives their own cards and game status
- **Final Results**: Public display of game outcomes

### DM Permission Validation

- Bot checks DM permissions before allowing players to join
- Clear error messages guide users to enable DMs
- Prevents game disruption due to DM issues

## 🚀 GitHub Actions

The project includes automated CI/CD pipeline:

### Build Pipeline

1. **Linting**: Flake8 and Black code formatting checks
2. **Docker Build**: Multi-platform image building (AMD64, ARM64)
3. **Security Scan**: Trivy vulnerability scanning
4. **Registry Push**: Automatic deployment to container registry

### Workflow Features

- ✅ Code quality checks
- ✅ Multi-platform Docker builds
- ✅ Security vulnerability scanning
- ✅ Automated deployment
- ✅ Build status badges

## 🧪 Development

### Code Quality

The project uses several tools for code quality:

```bash
# Linting
flake8 .

# Code formatting
black .

# Type checking (if using mypy)
mypy .
```

### Testing

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=blackjack
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all functions
- Maintain test coverage
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join community discussions in GitHub Discussions
- **Wiki**: Check the project wiki for detailed documentation

## 🙏 Acknowledgments

- Discord.py community for the excellent framework
- Clean Architecture principles by Robert C. Martin
- All contributors and testers

---

**Happy Gaming! 🎲** 