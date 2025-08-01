import time
from collections import deque
import aiohttp
import asyncio
from disnake.ext import commands
import disnake
import psutil
import datetime

class Loops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.check_if_in_game())
        self.bot.loop.create_task(self.update_cpu_status())
        self.bot.loop.create_task(self.process_pending_matches())
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
       
        while True:
            try:
                """Checks if tracked users are in game and announces their games."""
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
                            #debug print the game data
                            print(game_data)
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
                            
                            game_mode_finished = message_info.get('game_mode') # Get game_mode
                            skip_deletion = False  # Flag to control message deletion

                            # Initial message edit
                            await message.edit(embed=disnake.Embed(
                                title="🎮 Game Over - Processing...", # Changed title and description
                                description="Please wait while we process match data...",
                                color=disnake.Color.gold()
                            ))
                            
                            update_result = 0 
                            description_for_next_step = ""

                            if game_mode_finished != 'BRAWL':
                                # First update database with new match data and wait for it to complete
                                # This is crucial - we need to await this call to ensure the database is updated
                                update_result = await self.bot.get_cog("RiotAPIOperations").update_database(announce=True)
                                description_for_next_step = f"Database updated with {update_result} new matches. Generating player cards..."
                            else:
                                # For BRAWL games, skip database update
                                description_for_next_step = "Skipped database update for BRAWL game. Generating player cards..."
                            
                            # Update the message to show we're now generating cards
                            await message.edit(embed=disnake.Embed(
                                title="🎮 Game Over - Generating Stats...",
                                description=f"{description_for_next_step}\n\nResults will be posted in the thread attached to this message.",
                                color=disnake.Color.gold()
                            ))
                            
                            # Create or get a thread attached to this live game message and post results there
                            thread = None
                            target_channel = channel
                            try:
                                if hasattr(message, "thread") and message.thread and not message.thread.archived:
                                    thread = message.thread
                                else:
                                    thread_name = f"Match {game_id}"
                                    thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)
                                target_channel = thread
                                # Try to remove the system "started a thread" message
                                try:
                                    await asyncio.sleep(5)
                                    async for recent_msg in channel.history(limit=20):
                                        if (
                                            recent_msg.type == disnake.MessageType.thread_created and (
                                                (recent_msg.thread and recent_msg.thread.id == thread.id) or
                                                (thread.name and thread.name in (recent_msg.content or ""))
                                            )
                                        ) or (
                                            (recent_msg.author and self.bot.user and recent_msg.author.id == self.bot.user.id) and
                                            ("started a thread" in (recent_msg.content or "")) and
                                            (thread.name and thread.name in (recent_msg.content or ""))
                                        ):
                                            try:
                                                await recent_msg.delete()
                                                await message.edit(embed=None)
                                            except Exception as de:
                                                print(f"Could not delete system thread message for game {game_id}: {de}")
                                            break
                                except Exception as e:
                                    print(f"Failed to delete system thread message for game {game_id}: {e}")
                            except Exception as e:
                                print(f"Error creating or accessing thread for game {game_id}: {e}")
                            
                            # Then generate finished game card
                            try:
                                # Ensure game_id includes the server prefix (e.g., "EUW1_" + game_id)
                                # The match ID should be prefixed with the region for the Riot API
                                match_region = self.bot.get_cog("RiotAPIOperations").ACCOUNT_REGION.upper()
                                full_game_id = f"{match_region}_{game_id}" if not game_id.startswith(f"{match_region}_") else game_id
                                
                                # Get match information from the database
                                match_info = await self.bot.get_cog("DatabaseOperations").get_match_info(full_game_id)
                                match_participants = await self.bot.get_cog("DatabaseOperations").get_match_participants(full_game_id)
                                
                                if match_info and match_participants:
                                    game_start_date = match_info[3] # Used for timestamp

                                    # Common: Prepare participant list (summary embed removed)
                                    tracked_users = await self.bot.get_cog("DatabaseOperations").get_users()
                                    tracked_puuids = {user.puuid for user in tracked_users}
                                    tracked_participants_list = [
                                        f"{p['riot_id_game_name']} ({p['champion_name']})"
                                        for p in match_participants if p['puuid'] in tracked_puuids
                                    ]

                                    if game_mode_finished == "CUSTOM":
                                        await message.edit(embed=disnake.Embed(
                                            title="🎮 Custom Game Over",
                                            description="Stats generation skipped for custom games.",
                                            color=disnake.Color.orange()
                                        ))
                                        # No summary or cards for CUSTOM games.

                                    elif game_mode_finished == "BRAWL":
                                        await message.edit(embed=disnake.Embed(
                                            title="🎮 BRAWL Game Over",
                                            description="Database update and player card generation skipped for BRAWL games.",
                                            color=disnake.Color.blue() 
                                        ))
                                        # No player cards for BRAWL games.

                                    else: # Regular game (not CUSTOM, not BRAWL)
                                        # Generate and send player cards only (no summary embed)
                                        player_cards = await self.bot.get_cog("CardGenerator").generate_finished_game_card(full_game_id)
                                        for card_file in player_cards:
                                            await target_channel.send(file=card_file)
                                else:
                                    # Handle cases where match data couldn't be fetched
                                    if game_mode_finished == 'CHERRY':
                                        # For CHERRY matches, add to pending queue instead of showing error
                                        print(f"Queuing CHERRY match {full_game_id} with message ID {message.id} in channel {channel.id}")
                                        await self.bot.get_cog("DatabaseOperations").add_pending_match(
                                            full_game_id, game_mode_finished, channel.id, message.id
                                        )
                                        queue_embed = disnake.Embed(
                                            title="⏳ CHERRY Match Queued",
                                            description=f"Match {full_game_id} has been added to the processing queue.\nCHERRY matches may take longer to become available in the API.",
                                            color=disnake.Color.orange()
                                        )
                                        await message.edit(embed=queue_embed)
                                        print(f"Successfully queued CHERRY match {full_game_id} and updated message {message.id}")
                                        # Don't delete the message - it will be updated when the match is processed
                                        skip_deletion = True
                                    else:
                                        # For non-CHERRY matches, show error as before
                                        error_embed = disnake.Embed(
                                            title="❌ Error Fetching Match Data",
                                            description=f"Could not retrieve details for game {full_game_id}.",
                                            color=disnake.Color.red()
                                        )
                                        await message.edit(embed=error_embed)
                                        await target_channel.send(embed=error_embed) # Also inform the thread/channel

                            except Exception as e:
                                print(f"Error generating finished game card for game {game_id}: {e}")
                                error_embed = disnake.Embed(
                                    title="❌ Error Generating Game Stats",
                                    description=f"Could not generate game stats: {str(e)}",
                                    color=disnake.Color.red()
                                )
                                try: # Attempt to edit the original message first
                                    await message.edit(embed=error_embed)
                                except disnake.NotFound: # If message is already deleted, just send to channel
                                    pass 
                                await target_channel.send(embed=error_embed)
                            
                            # Do not delete the original message; keep it as the parent of the thread with results
                            # (Previously deleted the message after a short delay.)
                        except Exception as e:
                            print(f"Error processing finished game {game_id}: {e}")
                            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error processing finished game {game_id}: {e}")
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

                            # Skip generating live cards for unsupported BRAWL mode
                            if game_info.get('gameMode') == 'BRAWL':
                                print(f"Skipping live game card generation for BRAWL game {game_id}")
                                continue
                            
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
                                        'channel_id': channel.id,
                                        'game_mode': game_info['gameMode']
                                    }
                
            except Exception as e:
                print(f"Error in check_if_in_game loop: {e}")
                await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in check_if_in_game loop: {e}")
            await asyncio.sleep(60)

    async def process_pending_matches(self):
        """Periodically process pending CHERRY matches that failed to fetch initially"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Clean up old pending matches (older than 7 days)
                await self.bot.get_cog("DatabaseOperations").cleanup_old_pending_matches(7)
                
                # Get all pending matches
                pending_matches = await self.bot.get_cog("DatabaseOperations").get_pending_matches()
                
                for match_data in pending_matches:
                    match_id, game_mode, channel_id, message_id, attempts, created_at, last_attempt = match_data
                    print(f"Processing pending match {match_id} (attempt {attempts + 1}) with message ID {message_id} in channel {channel_id}")
                    
                    try:
                        # Try to fetch the match data from the API again
                        match_data = await self.bot.get_cog("RiotAPIOperations").get_match_data(match_id)
                        
                        if match_data:
                            # Match data was successfully fetched and stored in database
                            # Now get the processed data from database
                            match_info = await self.bot.get_cog("DatabaseOperations").get_match_info(match_id)
                            match_participants = await self.bot.get_cog("DatabaseOperations").get_match_participants(match_id)
                        
                        if match_data and match_info and match_participants:
                            # Match data is now available, process it
                            try:
                                channel = await self.bot.fetch_channel(channel_id)
                                message = await channel.fetch_message(message_id)
                                
                                # Validate that this is actually a CHERRY match queued message
                                # Check if the message has an embed with the expected title
                                is_valid_queued_message = (
                                    message.embeds and 
                                    len(message.embeds) > 0 and 
                                    message.embeds[0].title and
                                    "CHERRY Match Queued" in message.embeds[0].title
                                )
                                
                                if not is_valid_queued_message:
                                    print(f"Warning: Message {message_id} for match {match_id} doesn't appear to be a CHERRY queued message. Skipping deletion.")
                                    # Still process the match but don't delete the message
                                    should_delete_message = False
                                else:
                                    should_delete_message = True
                                    # Update message to show we're processing
                                    await message.edit(embed=disnake.Embed(
                                        title="🎮 CHERRY Match Found - Processing...",
                                        description="Match data is now available. Generating player cards...\n\nResults will be posted in the thread attached to this message.",
                                        color=disnake.Color.green()
                                    ))
                                
                                # Prepare participant list (summary embed removed)
                                game_start_date = match_info[3]
                                tracked_users = await self.bot.get_cog("DatabaseOperations").get_users()
                                tracked_puuids = {user.puuid for user in tracked_users}
                                tracked_participants_list = [
                                    f"{p['riot_id_game_name']} ({p['champion_name']})"
                                    for p in match_participants if p['puuid'] in tracked_puuids
                                ]
                                
                                # Create or get a thread for posting results
                                thread = None
                                target_channel = channel
                                try:
                                    if hasattr(message, "thread") and message.thread and not message.thread.archived:
                                        thread = message.thread
                                    else:
                                        thread_name = f"Match {match_id}"
                                        thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)
                                    target_channel = thread
                                    # Try to remove the system "started a thread" message
                                    try:
                                        await asyncio.sleep(0.5)
                                        async for recent_msg in channel.history(limit=20):
                                            if (
                                                recent_msg.type == disnake.MessageType.thread_created and (
                                                    (recent_msg.thread and recent_msg.thread.id == thread.id) or
                                                    (thread.name and thread.name in (recent_msg.content or ""))
                                                )
                                            ) or (
                                                (recent_msg.author and self.bot.user and recent_msg.author.id == self.bot.user.id) and
                                                ("started a thread" in (recent_msg.content or "")) and
                                                (thread.name and thread.name in (recent_msg.content or ""))
                                            ):
                                                try:
                                                    await recent_msg.delete()
                                                except Exception as de:
                                                    print(f"Could not delete system thread message for match {match_id}: {de}")
                                                break
                                    except Exception as e:
                                        print(f"Failed to delete system thread message for match {match_id}: {e}")
                                except Exception as e:
                                    print(f"Error creating or accessing thread for match {match_id}: {e}")
                                
                                # Generate player cards
                                player_cards = await self.bot.get_cog("CardGenerator").generate_finished_game_card(match_id)
                                
                                # Update the queued message to no longer include summary; just post the cards in the thread
                                for card_file in player_cards:
                                    await target_channel.send(file=card_file)
                                
                                # Remove from pending queue
                                await self.bot.get_cog("DatabaseOperations").remove_pending_match(match_id)
                                
                                print(f"Successfully processed pending CHERRY match: {match_id}")
                                
                            except disnake.NotFound:
                                # Message or channel was deleted, remove from queue
                                await self.bot.get_cog("DatabaseOperations").remove_pending_match(match_id)
                                print(f"Message/channel not found for pending match {match_id}, removed from queue")
                                
                        else:
                            # Match data still not available, update attempt counter
                            await self.bot.get_cog("DatabaseOperations").update_pending_match_attempt(match_id)
                            print(f"Match {match_id} still not available, attempt {attempts + 1}")
                            
                            # If we've tried too many times, remove from queue and notify
                            if attempts >= 9:  # 10 attempts total (0-9)
                                try:
                                    channel = await self.bot.fetch_channel(channel_id)
                                    message = await channel.fetch_message(message_id)
                                    
                                    # Validate that this is actually a CHERRY match queued message
                                    is_valid_queued_message = (
                                        message.embeds and 
                                        len(message.embeds) > 0 and 
                                        message.embeds[0].title and
                                        ("CHERRY Match Queued" in message.embeds[0].title or 
                                         "CHERRY Match Found" in message.embeds[0].title)
                                    )
                                    
                                    if is_valid_queued_message:
                                        failure_embed = disnake.Embed(
                                            title="❌ CHERRY Match Processing Failed",
                                            description=f"Match {match_id} could not be processed after multiple attempts.\nThis may be due to API limitations or the match being unavailable.",
                                            color=disnake.Color.red()
                                        )
                                        await message.edit(embed=failure_embed)
                                        
                                        # Delete message after a delay
                                        await asyncio.sleep(10)
                                        await message.delete()
                                        print(f"Deleted failed CHERRY match message for {match_id}")
                                    else:
                                        print(f"Warning: Message {message_id} for failed match {match_id} doesn't appear to be a CHERRY queued message. Skipping deletion.")
                                    
                                except disnake.NotFound:
                                    print(f"Message for failed match {match_id} was already deleted")
                                except Exception as e:
                                    print(f"Error handling failed match message for {match_id}: {e}")
                                
                                await self.bot.get_cog("DatabaseOperations").remove_pending_match(match_id)
                                print(f"Removed pending match {match_id} after {attempts + 1} failed attempts")
                    
                    except Exception as e:
                        print(f"Error processing pending match {match_id}: {e}")
                        # Don't remove from queue on error, let it retry
                        await self.bot.get_cog("DatabaseOperations").update_pending_match_attempt(match_id)
                        
            except Exception as e:
                print(f"Error in process_pending_matches loop: {e}")
                
            # Check every 2 minutes
            await asyncio.sleep(120)

def setup(bot):
    bot.add_cog(Loops(bot))

