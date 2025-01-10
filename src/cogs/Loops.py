import time
from collections import deque
import aiohttp
import asyncio
from disnake.ext import commands
import disnake
import psutil

class Loops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.check_if_in_game())
        self.bot.loop.create_task(self.update_cpu_status())
        self.live_game_messages = {}  # Store message IDs for each game

    async def update_cpu_status(self):
        """Updates the bot's status with peak CPU usage every 5 seconds."""
        await self.bot.wait_until_ready()
        # Initialize CPU percent without blocking
        psutil.cpu_percent()
        while not self.bot.is_closed():
            # Track peak CPU usage over 5 seconds
            peak_cpu = 0
            for _ in range(5):
                # Get CPU percent without interval (non-blocking)
                cpu_percent = psutil.cpu_percent()
                peak_cpu = max(peak_cpu, cpu_percent)
                await asyncio.sleep(1)
            
            await self.bot.change_presence(
                activity=disnake.Activity(
                    type=disnake.ActivityType.watching,
                    name=f"CPU Usage: {peak_cpu}%"
                )
            )

    async def check_if_in_game(self):
        """Checks if tracked users are in game and announces their games."""
        while True:
            try:
                users = await self.bot.get_cog("DatabaseOperations").get_users(active="TRUE")
                active_players = []
                processed_users = set()  # Keep track of processed users
                current_game_ids = set()  # Track current active game IDs

                # Collect data for all users in games
                for user in users:
                    if user.username in processed_users:  # Skip if user was already processed
                        continue

                    try:
                        game_data = await self.bot.get_cog("RiotAPIOperations").get_current_game(user.puuid)
                        if game_data:
                            current_game_ids.add(str(game_data['gameId']))
                            # Only process if this game hasn't been announced yet
                            if str(game_data['gameId']) != str(user.last_game_played):
                                # Process all tracked users in this game
                                for participant in game_data['participants']:
                                    # Find if this participant is one of our tracked users
                                    tracked_user = next((u for u in users if u.puuid == participant['puuid']), None)
                                    if tracked_user:
                                        champion = await self.bot.get_cog("DatabaseOperations").get_champion(participant['championId'])
                                        
                                        # Get player stats for this champion/gamemode
                                        stats = await self.bot.get_cog("DatabaseOperations").get_player_stats(
                                            tracked_user.riot_id_game_name, 
                                            game_data['gameMode'], 
                                            champion.replace(" ", "").replace("'", "")
                                        )
                                        
                                        # Extract relevant stats or use defaults if no stats available
                                        if stats:
                                            games = stats[0].champion_games
                                            winrate = f"{stats[0].winrate:.1f}"
                                            kda = f"{stats[0].average_kda:.2f}"
                                            pentas = stats[0].total_pentas
                                        else:
                                            games = 0
                                            winrate = "N/A"
                                            kda = "N/A"
                                            pentas = 0

                                        active_players.append({
                                            'name': tracked_user.riot_id_game_name,
                                            'champion': champion,
                                            'gameMode': game_data['gameMode'],
                                            'games': games,
                                            'winrate': winrate,
                                            'kda': kda,
                                            'pentas': pentas,
                                            'guild_id': tracked_user.guild_id,
                                            'game_id': str(game_data['gameId'])
                                        })

                                        await self.bot.get_cog("DatabaseOperations").update_user(
                                            tracked_user.username, 
                                            last_game_played=game_data['gameId']
                                        )
                                        processed_users.add(tracked_user.username)

                    except Exception as e:
                        print(f"Error checking if {user.riot_id_game_name} is in a game: {e}")
                    await asyncio.sleep(0.1)

                # Clean up messages for games that are no longer active
                games_to_remove = []
                for game_id, message_info in self.live_game_messages.items():
                    if game_id not in current_game_ids:
                        try:
                            channel = await self.bot.fetch_channel(message_info['channel_id'])
                            message = await channel.fetch_message(message_info['message_id'])
                            # edit title saying game is over, but keep the table and after 5 seconds delete the message
                            await message.edit(embed=disnake.Embed(
                                title="🎮 Game Over - Deleting in 30 seconds",
                                description=message.embeds[0].description,
                                color=disnake.Color.red()
                            ))
                            await asyncio.sleep(30)
                            await message.delete()
                        except Exception as e:
                            print(f"Error deleting message for game {game_id}: {e}")
                        games_to_remove.append(game_id)
                
                for game_id in games_to_remove:
                    self.live_game_messages.pop(game_id)

                # If there are active players, create and send the table
                if active_players:
                    # Update database with new matches in a separate task
                    self.bot.loop.create_task(self.bot.get_cog("RiotAPIOperations").update_database(announce=True))
                    
                    # Get formatted table from DataFormatter
                    table = await self.bot.get_cog("DataFormatter").format_active_players(active_players)
                    
                    # Find the botlol channel
                    for guild in self.bot.guilds:
                        if active_players[0]['guild_id'] != str(guild.id):
                            continue
                        channel = disnake.utils.get(guild.text_channels, name="botlol")
                        if channel:
                            embed = disnake.Embed(
                                title="🎮 Live Game(s)",
                                description=table,
                                color=disnake.Color.blue()
                            )
                            message = await channel.send(embed=embed)
                            # Store the message info for later cleanup
                            for player in active_players:
                                self.live_game_messages[player['game_id']] = {
                                    'message_id': message.id,
                                    'channel_id': channel.id
                                }
                    
                    await asyncio.sleep(10)

                await asyncio.sleep(10)
            except Exception as e:
                print(f"Error in check_if_in_game loop: {e}")
                await asyncio.sleep(10)

def setup(bot):
    bot.add_cog(Loops(bot))

