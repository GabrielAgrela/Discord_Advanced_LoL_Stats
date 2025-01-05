import time
from collections import deque
import aiohttp
import asyncio
from disnake.ext import commands
import disnake
import os
from dotenv import load_dotenv
from pathlib import Path

class RiotAPIOperations(commands.Cog):
    def __init__(self, bot, account_region="euw1", match_region="europe"):
         # Load .env from the project root (one folder up from src)
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)
        self.API_KEY = os.getenv("RIOT_API_KEY")
        self.ACCOUNT_REGION = account_region
        self.MATCH_REGION = match_region
        self.rate_limiter = self.RateLimiter()
        self.bot = bot

    class RateLimiter:
        def __init__(self):
            self.short_window = deque(maxlen=20)  # 20 requests per 1s
            self.long_window = deque(maxlen=100)  # 100 requests per 2min
            self.method_cooldowns = {}  # Track per-method rate limits
            
        async def wait_if_needed(self):
            current_time = time.time()
            
            # Add additional buffer to prevent hitting limits
            buffer_time = 0.05  # 50ms buffer
            
            # Clean up old requests from windows
            while self.short_window and current_time - self.short_window[0] > 1:
                self.short_window.popleft()
            while self.long_window and current_time - self.long_window[0] > 120:
                self.long_window.popleft()
            
            # Wait if necessary
            if len(self.short_window) >= 19:  # Leave room for buffer
                sleep_time = 1 - (current_time - self.short_window[0]) + buffer_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            if len(self.long_window) >= 99:  # Leave room for buffer
                sleep_time = 120 - (current_time - self.long_window[0]) + buffer_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            # Add current request timestamp
            current_time = time.time()
            self.short_window.append(current_time)
            self.long_window.append(current_time)

    async def make_request(self, url, params=None, max_retries=3):
        """Helper function to make rate-limited requests with retry logic"""
        headers = {"X-Riot-Token": self.API_KEY}
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                await self.rate_limiter.wait_if_needed()
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Get retry-after header, default to 5 seconds if not present
                        retry_after = int(response.headers.get('Retry-After', 5))
                        print(f"Rate limited. Waiting {retry_after} seconds before retry...")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 404:
                        return None
                    else:
                        response.raise_for_status()
            
            # If we've exhausted all retries
            response.raise_for_status()

    async def get_acc_from_riot_id(self, game_name, tag_line):
        """
        Get the player's PUUID from their Riot ID (gameName#tagLine).
        Endpoint: /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
        """
        url = f"https://{self.MATCH_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return await self.make_request(url)
    
    async def get_current_game(self, puuid):
        url = f"https://{self.ACCOUNT_REGION}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        data = await self.make_request(url)
        return data
    
    async def get_match_ids(self, puuid, deep_fetch=False):
        """
        Get match IDs for a player.
        Args:
            puuid: Player's PUUID
            deep_fetch: Parameter kept for backwards compatibility but no longer used
        """
        stored_matches = await self.bot.get_cog("DatabaseOperations").get_stored_match_ids(puuid)
        all_match_ids = []
        new_match_ids = []
        start = 0
        chunk_size = 100  # Maximum allowed by the API
        max_matches = 1000  # Maximum number of matches to fetch
        
        while start < max_matches:
            url = f"https://{self.MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
            params = {
                "start": start,
                "count": chunk_size
            }
            
            match_ids = await self.make_request(url, params=params)            
            # If no more matches are returned, break the loop
            if not match_ids:
                break
                
            all_match_ids.extend(match_ids)
            # Track new matches that aren't in the database
            new_matches = [m_id for m_id in match_ids if m_id not in stored_matches]
            new_match_ids.extend(new_matches)
            
            print(f"Found {len(all_match_ids)} total matches ({len(new_match_ids)} new)")
            
            if len(new_match_ids) == 0:
                print(f"Skipping to next user.")
                return new_match_ids
            

            start += chunk_size
        
        return new_match_ids

    async def get_match_data(self, match_id):
        url = f"https://{self.MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        headers = {"X-Riot-Token": self.API_KEY}
        match_data = await self.make_request(url, headers)        
        # Store the match data in the database
        await self.bot.get_cog("DatabaseOperations").insert_match(match_data)

        #print id of the match
        print(f"Match ID: {match_id}")

        return match_data
    
    async def update_database(self, inter: disnake.ApplicationCommandInteraction = None):
        users = await self.bot.get_cog("DatabaseOperations").get_users()
        total_matches_updated = 0
        total_users = len(users)

        def create_progress_bar(current, total, width=20):
            filled = int(width * current / total)
            bar = "█" * filled + "░" * (width - filled)
            percent = int(100 * current / total)
            return f"\nProgress: [{bar}] {percent}% ({current}/{total} users)"

        # Get formatted message for scanning announcement
        formatted_message = await self.bot.get_cog("DataFormatter").format_update_database_scan_message(users)
        original_description = formatted_message["description"]
        final_description = original_description.replace("Scanning for", "Scanned")

        # Store the botlol channel reference and message for later use if inter is None
        status_channel = None
        status_message = None
        
        for guild in self.bot.guilds:
            channel = disnake.utils.get(guild.text_channels, name="botlol")
            if channel:
                status_channel = channel
                if not inter and not status_message:
                    status_message = await channel.send(embed=disnake.Embed(
                        title="Starting database update...",
                        description=original_description + create_progress_bar(0, total_users),
                        color=disnake.Color.blue()
                    ))
        
        for i, user in enumerate(users, 1):
            riot_id = user[1].strip()
            print(f"\nProcessing player: {riot_id}")
            
            # Update the description to bold the current user
            current_description = original_description.replace(f"• {riot_id}", f"-->{riot_id}")
            current_description += create_progress_bar(i, total_users)
            
            if "#" not in riot_id:
                print("Invalid Riot ID format. It should be gameName#tagLine.")
                continue
                
            try:
                game_name, tag_line = riot_id.split("#", 1)
                match_ids = await self.get_match_ids(user[2])
                
                if not match_ids:
                    print(f"No new matches found for {riot_id}!")
                    if inter:
                        await inter.edit_original_message(embed=disnake.Embed(
                            title=f"{riot_id} - No new matches",
                            description=current_description,
                            color=disnake.Color.blue()
                        ))
                    elif status_message:
                        await status_message.edit(embed=disnake.Embed(
                            title=f"{riot_id} - No new matches",
                            description=current_description,
                            color=disnake.Color.blue()
                        ))
                else:
                    print(f"Processing {len(match_ids)} new matches")
                    # Get formatted message for progress update
                    progress_message = await self.bot.get_cog("DataFormatter").format_update_database_progress_message(game_name, len(match_ids))
                    progress_description = progress_message["description"] + create_progress_bar(i, total_users)
                    
                    if inter:
                        await inter.edit_original_message(embed=disnake.Embed(
                            title=f"{riot_id} - Processing {len(match_ids)} matches",
                            description=progress_description,
                            color=disnake.Color.blue()
                        ))
                    elif status_message:
                        await status_message.edit(embed=disnake.Embed(
                            title=f"{riot_id} - Processing {len(match_ids)} matches",
                            description=progress_description,
                            color=disnake.Color.blue()
                        ))
                    
                    for m_id in match_ids:
                        match_data = await self.get_match_data(m_id)
                        if match_data:
                            total_matches_updated += 1
                        
            except Exception as e:
                print(f"Error processing {riot_id}: {str(e)}")
                if inter:
                    await inter.edit_original_message(embed=disnake.Embed(
                        title=f"{riot_id} - Error",
                        description=current_description,
                        color=disnake.Color.red()
                    ))
                elif status_message:
                    await status_message.edit(embed=disnake.Embed(
                        title=f"{riot_id} - Error",
                        description=current_description,
                        color=disnake.Color.red()
                    ))
                continue
        
        # Send final update
        final_description = final_description + create_progress_bar(total_users, total_users)
        final_color = disnake.Color.green() if total_matches_updated > 0 else disnake.Color.red()
        if inter:
            await inter.edit_original_message(embed=disnake.Embed(
                title=f"Update Complete - {total_matches_updated} new matches",
                description=final_description,
                color=final_color
            ))
        elif status_message:
            await status_message.edit(embed=disnake.Embed(
                title=f"Update Complete - {total_matches_updated} new matches",
                description=final_description,
                color=final_color
            ))
        
        return total_matches_updated
    

def setup(bot):
    bot.add_cog(RiotAPIOperations(bot))

