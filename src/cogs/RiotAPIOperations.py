import time
from collections import deque
import aiohttp
import asyncio
from disnake.ext import commands
import disnake
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..models.models import User, Match, Participant

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
                    print(f"Sleeping for {sleep_time} seconds")
                    await asyncio.sleep(sleep_time)
                    
            if len(self.long_window) >= 99:  # Leave room for buffer
                sleep_time = 120 - (current_time - self.long_window[0]) + buffer_time
                if sleep_time > 0:
                    print(f"Sleeping for {sleep_time} seconds")
                    await asyncio.sleep(sleep_time)
            
            # Add current request timestamp
            current_time = time.time()
            self.short_window.append(current_time)
            self.long_window.append(current_time)

    async def make_request(self, url: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> Optional[Dict[str, Any]]:
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

    async def get_acc_from_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict[str, Any]]:
        """
        Get the player's PUUID from their Riot ID (gameName#tagLine).
        Endpoint: /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
        """
        url = f"https://{self.MATCH_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return await self.make_request(url)
    
    async def get_current_game(self, puuid: str) -> Optional[Dict[str, Any]]:
        url = f"https://{self.ACCOUNT_REGION}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        data = await self.make_request(url)
        return data
    
    async def get_match_ids(self, puuid: str, deep_fetch: bool = False) -> List[str]:
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

    async def get_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        url = f"https://{self.MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = await self.make_request(url)
        if match_data:
            # Convert match data to Match model
            match = Match(
                match_id=match_data['metadata']['matchId'],
                game_duration=match_data['info']['gameDuration'],
                game_version=match_data['info']['gameVersion'],
                game_mode=match_data['info']['gameMode'],
                game_type=match_data['info']['gameType'],
                game_creation=str(match_data['info']['gameCreation']),
                game_end=str(match_data['info']['gameEndTimestamp'])
            )
            
            # Store the match data in the database
            await self.bot.get_cog("DatabaseOperations").insert_match(match_data)
            print(f"Match ID: {match_id}")
            return match_data
        return None
    
    async def update_database(self, inter: disnake.ApplicationCommandInteraction = None, announce: bool = False) -> int:
        users: List[User] = await self.bot.get_cog("DatabaseOperations").get_users(active="TRUE")
        total_matches_updated = 0
        total_users = len(users)

        def create_progress_bar(current: int, total: int, width: int = 20) -> str:
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
                if not inter and not status_message and announce:
                    status_message = await channel.send(embed=disnake.Embed(
                        title="Starting database update...",
                        description=original_description + create_progress_bar(0, total_users),
                        color=disnake.Color.blue()
                    ))
        
        for i, user in enumerate(users, 1):
            riot_id = f"{user.riot_id_game_name}#{user.riot_id_tagline}"
            print(f"\nProcessing player: {riot_id}")
            
            # Update the description to bold the current user
            current_description = original_description.replace(f"• {user.riot_id_game_name}", f"-->{riot_id}")
            current_description += create_progress_bar(i, total_users)
                
            try:
                match_ids = await self.get_match_ids(user.puuid)
                
                if not match_ids:
                    print(f"No new matches found for {riot_id}!")
                    if announce:
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
                    progress_message = await self.bot.get_cog("DataFormatter").format_update_database_progress_message(user.riot_id_game_name, len(match_ids))
                    progress_description = progress_message["description"] + create_progress_bar(i, total_users)
                    
                    if announce:
                        if inter:
                            await inter.edit_original_message(embed=disnake.Embed(
                                title=f"{riot_id} - Processing {len(match_ids)} matches",
                                description=current_description,
                                color=disnake.Color.blue()
                            ))
                        elif status_message:
                            await status_message.edit(embed=disnake.Embed(
                                title=f"{riot_id} - Processing {len(match_ids)} matches",
                                description=current_description,
                                color=disnake.Color.blue()
                            ))
                    
                    for m_id in match_ids:
                        match_data = await self.get_match_data(m_id)
                        if match_data:
                            total_matches_updated += 1
                        
            except Exception as e:
                print(f"Error processing {riot_id}: {str(e)}")
                continue
        
        # Send final update
        final_description = final_description + create_progress_bar(total_users, total_users)
        final_color = disnake.Color.green() if total_matches_updated > 0 else disnake.Color.red()
        if announce:
            if inter:
                message = await inter.edit_original_message(embed=disnake.Embed(
                    title=f"Update Complete - {total_matches_updated} new matches",
                    description=final_description,
                    color=final_color
                ))
                await asyncio.sleep(60)
                await inter.delete_original_message()
            elif status_message:
                await status_message.edit(embed=disnake.Embed(
                    title=f"Update Complete - {total_matches_updated} new matches",
                    description=final_description,
                    color=final_color
                ))
                await asyncio.sleep(60)
                await status_message.delete()
        
        return total_matches_updated
    
    async def download_game_data(self, version: str) -> None:
        """
        Downloads and extracts game data for a specific version.
        Args:
            version: The game version (e.g., '15.1.1')
        """
        import shutil
        import tarfile
        import aiofiles
        import os

        # Create gamedata directory if it doesn't exist
        gamedata_path = Path(__file__).parent.parent / 'assets' / 'gamedata'
        gamedata_path.mkdir(parents=True, exist_ok=True)

        # Clean existing contents
        if gamedata_path.exists():
            shutil.rmtree(gamedata_path)
            gamedata_path.mkdir(parents=True)

        # Download the file
        url = f"https://ddragon.leagueoflegends.com/cdn/dragontail-{version}.tgz"
        tgz_path = gamedata_path / f"dragontail-{version}.tgz"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(tgz_path, 'wb') as f:
                        await f.write(await response.read())

                    # Extract the contents
                    with tarfile.open(tgz_path, 'r:gz') as tar:
                        tar.extractall(path=gamedata_path)

                    # Delete the tgz file
                    tgz_path.unlink()
                else:
                    print(f"Failed to download game data. Status: {response.status}")

    async def get_versions(self) -> List[str]:
        url = "https://ddragon.leagueoflegends.com/api/versions.json"
        data = await self.make_request(url)
        return data if data else []  # Return empty list if data is None

    async def populate_champions_table(self) -> int:
        """
        Fetches champion data from Data Dragon API and populates the champions table.
        Returns the number of champions added/updated.
        """
        versions = await self.get_versions()
        if not versions:
            print("Error fetching version data")
            return 0
        
        await self.download_game_data(versions[0])

        url = f"https://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/en_US/champion.json"
        champions_data = []

        try:
            data = await self.make_request(url)
            if not data:
                print("Error fetching champion data")
                return 0
                
            # Process each champion's data
            for champ_key, champ_data in data['data'].items():
                stats = champ_data['stats']
                champion = {
                    'id': int(champ_data['key']),
                    'name': champ_data['name'],
                    'title': champ_data['title'],
                    'image_full': champ_data['image']['full'],
                    'image_sprite': champ_data['image']['sprite'],
                    'image_group': champ_data['image']['group'],
                    'tags': ','.join(champ_data['tags']),
                    'partype': champ_data['partype'],
                    'stats_hp': stats['hp'],
                    'stats_hpperlevel': stats['hpperlevel'],
                    'stats_mp': stats['mp'],
                    'stats_mpperlevel': stats['mpperlevel'],
                    'stats_movespeed': stats['movespeed'],
                    'stats_armor': stats['armor'],
                    'stats_armorperlevel': stats['armorperlevel'],
                    'stats_spellblock': stats['spellblock'],
                    'stats_spellblockperlevel': stats['spellblockperlevel'],
                    'stats_attackrange': stats['attackrange'],
                    'stats_hpregen': stats['hpregen'],
                    'stats_hpregenperlevel': stats['hpregenperlevel'],
                    'stats_mpregen': stats['mpregen'],
                    'stats_mpregenperlevel': stats['mpregenperlevel'],
                    'stats_crit': stats['crit'],
                    'stats_critperlevel': stats['critperlevel'],
                    'stats_attackdamage': stats['attackdamage'],
                    'stats_attackdamageperlevel': stats['attackdamageperlevel'],
                    'stats_attackspeedperlevel': stats['attackspeedperlevel'],
                    'stats_attackspeed': stats['attackspeed']
                }
                champions_data.append(champion)

            # Insert the processed data into the database
            return await self.bot.get_cog("DatabaseOperations").insert_champions(champions_data)

        except Exception as e:
            print(f"Error in populate_champions_table: {e}")
            return 0

def setup(bot):
    bot.add_cog(RiotAPIOperations(bot))

