# Discord Advanced LoL Stats Bot

A Discord bot that provides advanced League of Legends statistics and analytics for server members. Track your progress, compare stats, and get detailed insights about your gameplay.

## Features

- Real-time player statistics
- Match history analysis
- Performance tracking and trends
- Player comparisons
- Automated stat updates
- Database persistence for historical data

## Prerequisites

- Docker and Docker Compose
- Discord Bot Token
- Riot Games API Key

## Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Discord_Advanced_LoL_Stats.git
cd Discord_Advanced_LoL_Stats
```

2. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables:
```env
DISCORD_TOKEN=your_discord_bot_token
RIOT_API_KEY=your_riot_api_key
```

## Running the Bot

### Production Mode
```bash
docker-compose up -d
```

To view logs:
```bash
docker-compose logs -f
```

To stop the bot:
```bash
docker-compose down
```

### Development/Debug Mode

The bot includes a built-in debugger configuration. To use it:

1. Run in debug mode:
```bash
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up
```

2. The debugger will be available on port 5678. You can connect to it using:
   - VS Code's Python debugger
   - PyCharm's Python Remote Debug
   - Any other debugger that supports Python's debugpy

3. To set breakpoints:
   - Add `breakpoint()` in your code where you want to pause execution
   - Or use your IDE's breakpoint interface

4. When a breakpoint is hit, you can:
   - Inspect variables
   - Step through code
   - Evaluate expressions
   - View the call stack

## Commands

- `/stats [summoner_name]` - Display summoner statistics
- `/match [summoner_name]` - Show recent match details
- `/compare [summoner1] [summoner2]` - Compare two players' stats
- `/track [summoner_name]` - Start tracking a player's statistics

## Project Structure

```
Discord_Advanced_LoL_Stats/
├── src/
│   ├── bot.py
│   └── cogs/
│       ├── Commands.py
│       ├── DatabaseOperations.py
│       ├── DataFormatter.py
│       ├── Loops.py
│       └── RiotAPIOperations.py
├── docker-compose.yml
├── docker-compose.debug.yml
├── Dockerfile
└── requirements.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Riot Games API
- discord.py library
- All contributors and users of the bot 