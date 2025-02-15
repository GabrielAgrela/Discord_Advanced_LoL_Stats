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
            try:
                # Track peak CPU usage over 5 seconds
                peak_cpu = 0
                for _ in range(5):
                    # Get CPU percent without interval (non-blocking)
                    cpu_percent = psutil.cpu_percent()
                    peak_cpu = max(peak_cpu, cpu_percent)
                    await asyncio.sleep(1)
                
                try:
                    await self.bot.change_presence(
                        activity=disnake.Activity(
                            type=disnake.ActivityType.watching,
                            name=f"CPU Usage: {peak_cpu}%"
                        )
                    )
                except (ConnectionResetError, disnake.ConnectionClosed):
                    # If connection is reset, wait a bit and let the bot reconnect
                    await asyncio.sleep(30)
                    continue
                    
            except Exception as e:
                print(f"Error in update_cpu_status: {e}")
                await asyncio.sleep(30)  # Wait longer on general errors
                continue

    async def check_if_in_game(self):
        """Checks if tracked users are in game and announces their games."""
        while True:
            try:
                users = await self.bot.get_cog("DatabaseOperations").get_users(active="TRUE")
                processed_users = set()  # Keep track of processed users
                current_game_ids = set()  # Track current active game IDs
                games_data = {}  # Dictionary to store players grouped by game ID

                # Collect data for all users in games
                for user in users:
                    if user.username in processed_users:  # Skip if user was already processed
                        continue

                    try:
                        game_data = await self.bot.get_cog("RiotAPIOperations").get_current_game(user.puuid)
                        if game_data and game_data['gameId']:  # Only process if game_data is not None
                            game_id = str(game_data['gameId'])
                            current_game_ids.add(game_id)
                            
                            # Initialize game data if not exists
                            if game_id not in games_data:
                                games_data[game_id] = {
                                    'players': [],
                                    'gameMode': game_data['gameMode'],
                                    'guild_id': user.guild_id
                                }

                            # Process all tracked users in this game
                            for participant in game_data['participants']:
                                # Find if this participant is one of our tracked users
                                tracked_user = next((u for u in users if u.puuid == participant['puuid']), None)
                                if tracked_user:
                                    champion = await self.bot.get_cog("DatabaseOperations").get_champion(participant['championId'])
                                    
                                    stats = await self.bot.get_cog("DatabaseOperations").get_player_stats(
                                        tracked_user.riot_id_game_name, 
                                        game_data['gameMode'], 
                                        champion.replace(" ", "").replace("'", "")
                                    )

                                    # Only add to players list and update last_game_played if not announced yet
                                    if game_id != str(tracked_user.last_game_played):
                                        games_data[game_id]['players'].append({
                                            'name': tracked_user.riot_id_game_name,
                                            'champion': champion,
                                            'gameMode': game_data['gameMode'],
                                            'stats': stats[0] if stats else None,
                                            'guild_id': tracked_user.guild_id,
                                            'game_id': game_id
                                        })
                                        
                                        await self.bot.get_cog("DatabaseOperations").update_user(
                                            tracked_user.username, 
                                            last_game_played=game_id
                                        )
                                    processed_users.add(tracked_user.username)

                    except Exception as e:
                        print(f"Error checking if {user.riot_id_game_name} is in a game: {e}")
                        await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error checking if {user.riot_id_game_name} is in a game: {e}")
                # Clean up messages for games that are no longer active
                games_to_remove = []
                for game_id, message_info in self.live_game_messages.items():
                    if game_id not in current_game_ids:
                        try:
                            channel = await self.bot.fetch_channel(message_info['channel_id'])
                            message = await channel.fetch_message(message_info['message_id'])
                            await message.edit(embed=disnake.Embed(
                                title="🎮 Game Over - Deleting in 30 seconds",
                                color=disnake.Color.red()
                            ))
                            self.bot.loop.create_task(self.bot.get_cog("RiotAPIOperations").update_database(announce=True))
                            await asyncio.sleep(30)
                            await message.delete()
                        except Exception as e:
                            print(f"Error deleting message for game {game_id}: {e}")
                            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error deleting message for game {game_id}: {e}")
                        games_to_remove.append(game_id)
                
                for game_id in games_to_remove:
                    self.live_game_messages.pop(game_id)

                # Process each game and send one message per game
                for game_id, game_info in games_data.items():
                    if game_id not in self.live_game_messages:  # Only send if we haven't announced this game yet
                        players = game_info['players']
                        if players:
                            # Sort players by winrate
                            players.sort(key=lambda x: x['stats'].winrate if x['stats'] else 0, reverse=True)
                            
                            # Find the botlol channel
                            for guild in self.bot.guilds:
                                if game_info['guild_id'] != str(guild.id):
                                    continue
                                channel = disnake.utils.get(guild.text_channels, name="botlol")
                                if channel:
                                    # Send initial embed
                                    initial_embed = disnake.Embed(
                                        title="🎮 Live Game Found!",
                                        description="Generating player statistics... Please wait.",
                                        color=disnake.Color.blue()
                                    )
                                    message = await channel.send(embed=initial_embed)
                                    
                                    # Generate live players card
                                    card = await self.bot.get_cog("CardGenerator").generate_live_players_card(players)
                                    
                                    # Edit the message with the card
                                    await message.edit(embed=None, file=card)
                                    
                                    # Store the message info for later cleanup
                                    self.live_game_messages[game_id] = {
                                        'message_id': message.id,
                                        'channel_id': channel.id
                                    }
                
            except Exception as e:
                print(f"Error in check_if_in_game loop: {e}")
                await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in check_if_in_game loop: {e}")
            await asyncio.sleep(60)

def setup(bot):
    bot.add_cog(Loops(bot))

