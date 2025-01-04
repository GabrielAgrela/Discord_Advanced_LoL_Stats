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
git clone https://github.com/GabrielAgrela/Discord_Advanced_LoL_Stats.git
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

To enable debugging:

1. In the Dockerfile, uncomment the debugging section:
```dockerfile
# Debugging
# RUN pip install debugpy
# ENTRYPOINT ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "src/bot.py"]
```

2. Rebuild and run the container:
```bash
docker-compose build
docker-compose up
```

3. The container will wait for a debugger connection on port 5678 before starting the bot
4. Connect your IDE's debugger to localhost:5678
5. Set breakpoints in your code and debug as needed

## Commands

- `/get_player_stats [summoner_name] [gamemode] [champion]` - Display detailed stats for a summoner. Gamemode can be ARAM, CLASSIC, CHERRY, etc.
- `/get_all_players_stats` - Show stats for all tracked players
- `/player_vs_player [username1] [username2] [champion] [gamemode]` - Compare two players' stats on a specific champion
- `/player_friends_stats [username]` - View stats when playing with friends
- `/update_database` - Update the database with new matches
- `/add_player_to_database [username] [tagline]` - Add a new player to track (e.g., username: "Felizberto", tagline: "EUW")

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