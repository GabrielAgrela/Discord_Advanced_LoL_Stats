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

- Python 3.8+
- Docker (optional, for containerized deployment)
- Discord Bot Token
- Riot Games API Key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Discord_Advanced_LoL_Stats.git
cd Discord_Advanced_LoL_Stats
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables:
```env
DISCORD_TOKEN=your_discord_bot_token
RIOT_API_KEY=your_riot_api_key
```

## Running the Bot

### Standard Method
```bash
python src/bot.py
```

### Using Docker
```bash
docker-compose up -d
```

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