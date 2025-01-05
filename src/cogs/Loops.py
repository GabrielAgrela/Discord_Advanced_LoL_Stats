import time
from collections import deque
import aiohttp
import asyncio
from disnake.ext import commands
import disnake

class Loops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_if_in_game(self):
        while True:
            users = await self.bot.get_cog("DatabaseOperations").get_users()
            active_players = []
            processed_users = set()  # Keep track of processed users

            # Collect data for all users in games
            for user in users:
                if user[1] in processed_users:  # Skip if user was already processed
                    continue

                try:
                    game_data = await self.bot.get_cog("RiotAPIOperations").get_current_game(user[2])
                    if game_data:
                        # Process all tracked users in this game
                        for participant in game_data['participants']:
                            # Find if this participant is one of our tracked users
                            tracked_user = next((u for u in users if u[2] == participant['puuid']), None)
                            if tracked_user and str(tracked_user[5]) != str(game_data['gameId']):
                                champion = await self.bot.get_cog("DatabaseOperations").get_champion(participant['championId'])
                                
                                # Get player stats for this champion/gamemode
                                stats = await self.bot.get_cog("DatabaseOperations").get_player_stats(tracked_user[3], game_data['gameMode'], champion.replace(" ", "").replace("'", ""))
                                
                                # Extract relevant stats or use defaults if no stats available
                                if stats:
                                    games = stats[0][1]
                                    winrate = f"{stats[0][2]:.1f}"
                                    kda = f"{stats[0][4]:.2f}"
                                    pentas = stats[0][12] if len(stats[0]) > 12 else 0
                                else:
                                    games = 0
                                    winrate = "N/A"
                                    kda = "N/A"
                                    pentas = 0

                                active_players.append({
                                    'name': tracked_user[3],
                                    'champion': champion,
                                    'gameMode': game_data['gameMode'],
                                    'games': games,
                                    'winrate': winrate,
                                    'kda': kda,
                                    'pentas': pentas
                                })

                                await self.bot.get_cog("DatabaseOperations").update_user(tracked_user[1], last_game_played=game_data['gameId'])
                                processed_users.add(tracked_user[1])  # Mark this user as processed

                except Exception as e:
                    print(f"Error checking if {user[3]} is in a game: {e}")
                await asyncio.sleep(0.1)

            # If there are active players, create and send the table
            if active_players:
                # Get formatted table from DataFormatter
                table = await self.bot.get_cog("DataFormatter").format_active_players(active_players)
                
                # Find the botlol channel
                for guild in self.bot.guilds:
                    if guild.id != user[6]:
                        continue
                    channel = disnake.utils.get(guild.text_channels, name="botlol")
                    if channel:
                        embed = disnake.Embed(
                            title="🎮 Live Game(s)",
                            description=table,
                            color=disnake.Color.blue()
                        )
                        await channel.send(embed=embed)
                
                # Update database with new matches
                num_matches_updated = await self.bot.get_cog("RiotAPIOperations").update_database()
                await asyncio.sleep(200)

            await asyncio.sleep(10)

def setup(bot):
    bot.add_cog(Loops(bot))

