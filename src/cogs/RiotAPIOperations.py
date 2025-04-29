import time
from collections import deque
import aiohttp
import asyncio
from disnake.ext import commands
import disnake
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
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
            
        async def wait_if_needed(self, url = None, params = None):
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
                    print(f"Sleeping long for {sleep_time} seconds for {url} {params}")
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
                try:
                    await self.rate_limiter.wait_if_needed(url, params)
                    
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
                        elif response.status == 503:
                            print(f"Service unavailable. Attempt {attempt + 1}/{max_retries}")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        elif response.status == 504:
                            print(f"Timeout. Attempt {attempt + 1}/{max_retries}")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        elif response.status == 500:
                            print(f"Internal server error. Attempt {attempt + 1}/{max_retries}")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            response.raise_for_status()
                except aiohttp.ClientConnectorError as e:
                    print(f"Connection error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None
                except Exception as e:
                    print(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise
            
            return None

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
                        
            if len(new_match_ids) == 0:
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
            
            # Update the description to bold the current user
            current_description = original_description.replace(f"• {user.riot_id_game_name}", f"-->{riot_id}")
            current_description += create_progress_bar(i, total_users)
                
            try:
                match_ids = await self.get_match_ids(user.puuid)
                
                if not match_ids:
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
                await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error processing {riot_id}: {str(e)}")
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
                await inter.delete_original_message()
            elif status_message:
                await status_message.edit(embed=disnake.Embed(
                    title=f"Update Complete - {total_matches_updated} new matches",
                    description=final_description,
                    color=final_color
                ))
                await status_message.delete()
        
        return total_matches_updated
    
    async def _clean_gamedata_directory(self) -> Tuple[bool, Optional[str]]:
        """Cleans the gamedata directory. Returns (success, error_msg)."""
        import shutil
        gamedata_path = Path(__file__).parent.parent / 'assets' / 'gamedata'
        gamedata_path.mkdir(parents=True, exist_ok=True) # Ensure base path exists

        if gamedata_path.exists():
            try:
                if any(gamedata_path.iterdir()): 
                    shutil.rmtree(gamedata_path)
                gamedata_path.mkdir(parents=True, exist_ok=True) # Recreate after removal
            except Exception as e:
                error_msg = f"Error cleaning old game data directory: {str(e)}"
                print(error_msg)
                return False, error_msg
        return True, None

    async def _download_gamedata_archive(self, version: str) -> Tuple[bool, Optional[str]]:
        """Downloads the game data archive. Returns (success, error_msg)."""
        import aiofiles
        import aiohttp
        gamedata_path = Path(__file__).parent.parent / 'assets' / 'gamedata'
        url = f"https://ddragon.leagueoflegends.com/cdn/dragontail-{version}.tgz"
        tgz_path = gamedata_path / f"dragontail-{version}.tgz"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(tgz_path, 'wb') as f:
                            await f.write(await response.read())
                    else:
                        error_msg = f"Failed to download game data archive. Status: {response.status}"
                        print(error_msg)
                        return False, error_msg
        except aiohttp.ClientConnectorError as e:
            error_msg = f"Network error during download: {str(e)}"
            print(f"Network error downloading archive: {e}")
            return False, error_msg
        except Exception as e:
             error_msg = f"Error during download: {str(e)}"
             print(f"Error downloading archive: {e}")
             return False, error_msg
        return True, None

    async def _extract_gamedata_archive(self, version: str) -> Tuple[bool, Optional[str]]:
        """Extracts the game data archive. Returns (success, error_msg)."""
        import tarfile
        gamedata_path = Path(__file__).parent.parent / 'assets' / 'gamedata'
        tgz_path = gamedata_path / f"dragontail-{version}.tgz"
        try:
            with tarfile.open(tgz_path, 'r:gz') as tar:
                tar.extractall(path=gamedata_path)
        except Exception as e:
             error_msg = f"Error extracting game data archive: {str(e)}"
             print(error_msg)
             return False, error_msg
        return True, None
        
    async def _cleanup_gamedata_archive(self, version: str) -> Tuple[bool, Optional[str]]:
        """Deletes the downloaded tgz file. Returns (success, error_msg)."""
        gamedata_path = Path(__file__).parent.parent / 'assets' / 'gamedata'
        tgz_path = gamedata_path / f"dragontail-{version}.tgz"
        try:
            if tgz_path.exists():
                 tgz_path.unlink()
        except Exception as e:
             # Non-critical, log warning but proceed
             error_msg = f"Warning: Could not delete downloaded archive file: {e}"
             print(error_msg)
             return False, error_msg # Treat warning as non-fatal for now
        return True, None

    async def get_versions(self) -> List[str]:
        url = "https://ddragon.leagueoflegends.com/api/versions.json"
        data = await self.make_request(url)
        return data if data else []

    async def apply_lol_update(self, inter: disnake.ApplicationCommandInteraction) -> int:
        """
        Fetches latest LoL data, updating a status message with progress steps.
        """
        step_index = 0
        data_formatter = self.bot.get_cog("DataFormatter") # Get formatter cog
        status_embed = disnake.Embed(
            title="LoL Data Update",
            # Call DataFormatter for the initial description
            description=await data_formatter.format_apply_update_steps(step_index),
            color=disnake.Color.blue()
        )

        # --- Send Initial Message ---
        try:
            await inter.edit_original_message(embed=status_embed)
        except disnake.NotFound:
            await inter.followup.send(embed=status_embed)
        except Exception as e:
            print(f"Error sending initial status for apply_lol_update: {e}")
            return 0

        # --- Step 0: Get Versions ---
        latest_version = None
        try:
            versions = await self.get_versions()
            latest_version = versions[0] if versions else None
            if not latest_version:
                error_msg = "Could not fetch latest LoL version list."
                # Call DataFormatter to format description with error
                status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
                status_embed.color = disnake.Color.red()
                await inter.edit_original_message(embed=status_embed)
                return 0
            status_embed.title = f"LoL Data Update ({latest_version})"
        except Exception as e:
            error_msg = f"Unexpected error fetching versions: {str(e)}"
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0

        # --- Step 1: Cleaning --- 
        step_index = 1
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        success, error_msg = await self._clean_gamedata_directory()
        if not success:
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0
            
        # --- Step 2: Downloading --- 
        step_index = 2
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        success, error_msg = await self._download_gamedata_archive(latest_version)
        if not success:
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0

        # --- Step 3: Extracting --- 
        step_index = 3
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        success, error_msg = await self._extract_gamedata_archive(latest_version)
        if not success:
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0
            
        # --- Step 4: Cleanup Archive --- 
        step_index = 4
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        success, error_msg = await self._cleanup_gamedata_archive(latest_version)
        if not success:
            print(error_msg)
            # Call DataFormatter to format description with warning
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg + " (Continuing anyway)")
            await inter.edit_original_message(embed=status_embed)
            # Don't return 0 here

        # --- Step 5: Fetch Champion JSON --- 
        step_index = 5
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        
        url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
        champions_data_dict = None
        try:
            champions_data_dict = await self.make_request(url)
            if not champions_data_dict:
                error_msg = "Error fetching champion JSON data (no data received)."
                # Call DataFormatter to format description with error
                status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
                status_embed.color = disnake.Color.red()
                await inter.edit_original_message(embed=status_embed)
                return 0
        except Exception as e:
            error_msg = f"Error during champion JSON request: {str(e)}"
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0
            
        # --- Step 6: Process Champions --- 
        step_index = 6
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        champions_to_insert = []
        try:
            for champ_key, champ_data in champions_data_dict['data'].items():
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
                champions_to_insert.append(champion)
        except KeyError as e:
            error_msg = f"Data structure error processing champion data (KeyError: {e}). Check Data Dragon format."
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0
        except Exception as e:
            error_msg = f"Unexpected error processing champion data: {str(e)}"
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0
            
        # --- Step 7: Insert Champions --- 
        step_index = 7
        # Call DataFormatter to format description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index)
        await inter.edit_original_message(embed=status_embed)
        champions_added = 0
        try:
            champions_added = await self.bot.get_cog("DatabaseOperations").insert_champions(champions_to_insert)
            if champions_added is None: # Assume None means DB error
                 error_msg = "Database operation failed during champion insertion."
                 # Call DataFormatter to format description with error
                 status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
                 status_embed.color = disnake.Color.red()
                 await inter.edit_original_message(embed=status_embed)
                 return 0
        except Exception as e:
            error_msg = f"Error inserting champions into database: {str(e)}"
            # Call DataFormatter to format description with error
            status_embed.description = await data_formatter.format_apply_update_steps(step_index, error=error_msg)
            status_embed.color = disnake.Color.red()
            await inter.edit_original_message(embed=status_embed)
            return 0

        # --- Step 8: Complete --- 
        step_index = 8
        final_message = f"\n\nSuccessfully added/updated **{champions_added}** champions."
        # Call DataFormatter to format final description
        status_embed.description = await data_formatter.format_apply_update_steps(step_index) + final_message
        status_embed.color = disnake.Color.green()
        await inter.edit_original_message(embed=status_embed)
        
        return champions_added

def setup(bot):
    bot.add_cog(RiotAPIOperations(bot))

