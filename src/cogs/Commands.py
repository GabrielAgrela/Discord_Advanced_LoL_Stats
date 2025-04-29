from disnake.ext import commands
import disnake
import asyncio
from typing import List, Optional, Tuple
from ..models.models import User, PlayerStats, PlayerFriendStats
from ..Utils import translate

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._player_names_cache = []
        self._last_cache_update = 0

    async def _get_player_names(self, inter: disnake.ApplicationCommandInteraction) -> List[str]:
        # Update cache every 5 minutes
        current_time = asyncio.get_event_loop().time()
        if not self._player_names_cache or current_time - self._last_cache_update > 300:
            users: List[User] = await self.bot.get_cog("DatabaseOperations").get_users(inter.guild.id)
            self._player_names_cache = [user.riot_id_game_name for user in users]
            self._last_cache_update = current_time
        return self._player_names_cache

    async def player_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str) -> List[str]:
        """Autocomplete function for player names"""
        try:
            player_names = await self._get_player_names(inter)
            filtered_names = [name for name in player_names if string.lower() in name.lower()]
            filtered_names.sort()  # Sort alphabetically
            return filtered_names[:25]
        except Exception as e:
            print(f"Error in autocomplete: {e}")
            if inter.channel:
                await inter.channel.send(f"Error in autocomplete: {e}")
            return []

    async def champion_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str) -> List[str]:
        """Autocomplete function for champion names"""
        try:
            champion_names = await self.bot.get_cog("DatabaseOperations").get_champion_names()
            filtered_names = [name for name in champion_names if string.lower() in name.lower()]
            filtered_names.sort()  # Sort alphabetically
            return filtered_names[:25]
        except Exception as e:
            print(f"Error in champion autocomplete: {e}")
            if inter.channel:
                await inter.channel.send(f"Error in champion autocomplete: {e}")
            return []

    @staticmethod
    async def _autocomplete_wrapper(inter: disnake.ApplicationCommandInteraction, string: str) -> List[str]:
        """Static wrapper for autocomplete to work with disnake's expectations"""
        try:
            cog = inter.bot.get_cog("Commands")
            if cog:
                return await cog.player_autocomplete(inter, string)
            return []
        except Exception as e:
            print(f"Error in autocomplete wrapper: {e}")
            if inter.channel:
                await inter.channel.send(f"Error in autocomplete: {e}")
            return []

    @staticmethod
    async def _champion_autocomplete_wrapper(inter: disnake.ApplicationCommandInteraction, string: str) -> List[str]:
        """Static wrapper for champion autocomplete to work with disnake's expectations"""
        try:
            cog = inter.bot.get_cog("Commands")
            if cog:
                return await cog.champion_autocomplete(inter, string)
            return []
        except Exception as e:
            print(f"Error in champion autocomplete wrapper: {e}")
            if inter.channel:
                await inter.channel.send(f"Error in champion autocomplete: {e}")
            return []

    @commands.slash_command()
    async def get_player_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        gamemode: str = commands.Param(choices=["ARAM", "Summoner's Rift", "Arena", "Nexus Blitz", "Swarm", "Ultimate Book", "URF"]),
        summoner_name: str = commands.Param(autocomplete=_autocomplete_wrapper),
        champion: str = commands.Param(default=None),
        sort_by: str = commands.Param(
            choices=["champion_games", "winrate", "kda", "dpm", "time_dead", "pentas"],
            default="champion_games",
            description="Sort results by this stat"
        ),
        sort_order: str = commands.Param(
            choices=["ASC", "DESC"],
            default="DESC",
            description="Sort order (ascending or descending)"
        )
    ):
        """
        Get LoL stats for a summoner
        
        Parameters
        ----------
        summoner_name: The summoner name to look up
        gamemode: The game mode to get stats for
        champion: The champion to get stats for if you want to filter by a specific champion
        sort_by: Sort results by this stat (games, winrate, kda, dpm, time dead, or pentas)
        sort_order: Sort order (ascending or descending)
        """
        if not await self.bot.is_botlol_channel(inter):
            return
            
        gamemode = translate(gamemode)
        await inter.response.defer()
        try:
            data: List[PlayerStats] = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(
                    summoner_name, 
                    gamemode, 
                    champion,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                timeout=10.0
            )
            if not data:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No {gamemode} stats found for {summoner_name} (or less than 4 games per champion)", color=disnake.Color.red()))
            else:
                await inter.followup.send(embed=disnake.Embed(title=f"{summoner_name} {gamemode} Stats", description=await self.bot.get_cog("DataFormatter").format_get_player_stats(data), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")
            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in get_player_stats: {e}")

    @commands.slash_command()
    async def get_all_players_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction
    ):
        """
        Get LoL stats for all players in the database
        """
        if not await self.bot.is_botlol_channel(inter):
            return
            
        await inter.response.defer()
        try:
            data: List[User] = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_all_players_stats(),
                timeout=10.0
            )
            if not data:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No stats found"))
            else:
                await inter.followup.send(embed=disnake.Embed(title="All Players Stats", description=await self.bot.get_cog("DataFormatter").format_get_all_players_stats(data), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")
            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in get_all_players_stats: {e}")

    @commands.slash_command()
    async def compare_players(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        gamemode: str = commands.Param(choices=["ARAM", "Summoner's Rift", "Arena", "Nexus Blitz", "Swarm", "Ultimate Book", "URF"]),
        username1: str = commands.Param(autocomplete=_autocomplete_wrapper),
        username2: str = commands.Param(autocomplete=_autocomplete_wrapper),
        champion: str = commands.Param(default=None)
    ):
        """
        Get LoL stats for two players vs each other
        
        Parameters
        ----------
        username1: The first player to look up
        username2: The second player to look up
        gamemode: The game mode to get stats for (default is ARAM)
        champion: The champion to get stats for (optional)
        """
        if not await self.bot.is_botlol_channel(inter):
            return
        
        gamemode = translate(gamemode)
        await inter.response.defer()
        try:
            data_user1: List[PlayerStats] = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(username1, gamemode, champion, limit=300),
                timeout=10.0
            )
            if not data_user1:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No {gamemode} stats found for {username1} (or less than 4 games per champion)", color=disnake.Color.red()))
                return
            data_user2: List[PlayerStats] = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(username2, gamemode, champion, limit=300),
                timeout=10.0
            )
            if not data_user2:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No {gamemode} stats found for {username2} (or less than 4 games per champion)", color=disnake.Color.red()))
                return
            await inter.followup.send(embed=disnake.Embed(title=f"{username1} vs {username2} {gamemode} Stats", description=await self.bot.get_cog("DataFormatter").format_player_vs_player(data_user1, data_user2, username1, username2, champion), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")
            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in compare_players: {e}")

    @commands.slash_command()
    async def player_friends_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        username: str = commands.Param(autocomplete=_autocomplete_wrapper)
    ):
        """
        Get LoL stats for a player's friends
        
        Parameters
        ----------
        username: The player to look up
        """
        if not await self.bot.is_botlol_channel(inter):
            return
        await inter.response.defer()
        try:
            data: List[PlayerFriendStats] = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_friend_stats(username),
                timeout=10.0
            )
            if not data:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No duo stats found for {username} (minimum 5 games together required)", color=disnake.Color.red()))
                return
            await inter.followup.send(embed=disnake.Embed(title=f"{username} Friends Stats", description=await self.bot.get_cog("DataFormatter").format_player_friends_data(data, username), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")
            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in player_friends_stats: {e}")

    @commands.slash_command()
    async def update_database(
        self, 
        inter: disnake.ApplicationCommandInteraction
    ):
        """
        Look for new matches for all players in the database and update the database
        """
        if not await self.bot.is_botlol_channel(inter):
            return
        await inter.response.defer()
        total_matches = await self.bot.get_cog('RiotAPIOperations').update_database(inter=inter, announce=True)
        #await inter.edit_original_message(embed=disnake.Embed(title="Updated Database", description=f"Added {total_matches} new matches", color=disnake.Color.blue()))
        
    @commands.slash_command()
    async def add_player_to_database(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        username: str,
        tagline: str
    ):
        """
        Add a player to the database
        
        Parameters
        ----------
        username: The player to add to the database. Ex: "felizbreto" and the #/tagline being "EUW" 
        """
        if not await self.bot.is_botlol_channel(inter):
            return
        data = await self.bot.get_cog("RiotAPIOperations").get_acc_from_riot_id(username, tagline)
        full_name = f"{data['gameName']}#{data['tagLine']}"
        await self.bot.get_cog("DatabaseOperations").insert_user(full_name, data["puuid"], data["gameName"], data["tagLine"], inter)
        await inter.response.send_message(f"Added {full_name} to the database", ephemeral=True)

    @commands.slash_command()
    async def generate_card(
        self,
        inter: disnake.ApplicationCommandInteraction,
        gamemode: str = commands.Param(choices=["ARAM", "Summoner's Rift", "Arena", "Nexus Blitz", "Swarm", "Ultimate Book", "URF"]),
        summoner_name: str = commands.Param(autocomplete=_autocomplete_wrapper),
        sort_by: str = commands.Param(
            choices=["champion games", "winrate", "kda", "dpm", "time dead", "pentas"],
            default="champion games",
            description="Sort results by this stat"
        ),
        sort_order: str = commands.Param(
            choices=["ASC", "DESC"],
            default="DESC",
            description="Sort order (ascending or descending)"
        ),
        min_games: int = commands.Param(
            default=4,
            description="Minimum number of games required per champion"
        )
    ):
        """
        Generate a player card with stats
        
        Parameters
        ----------
        summoner_name: The summoner name to generate a card for
        gamemode: The game mode to show stats for
        """
        if not await self.bot.is_botlol_channel(inter):
            return
            
        await inter.response.defer()
        gamemode = translate(gamemode)

        try:
            # Get player stats
            data: List[PlayerStats] = await self.bot.get_cog("DatabaseOperations").get_player_stats(
                summoner_name, 
                gamemode, 
                sort_by=sort_by,
                sort_order=sort_order,
                min_games=min_games
            )
            if not data:
                await inter.followup.send(
                    embed=disnake.Embed(
                        title="No stats found",
                        description=f"No {gamemode} stats found for {summoner_name}",
                        color=disnake.Color.red()
                    )
                )
                return
                
            # Generate the card using CardGenerator cog
            card_file = await self.bot.get_cog("CardGenerator").generate_player_card(summoner_name, gamemode, data)
            await inter.followup.send(file=card_file)
                
        except Exception as e:
            await inter.followup.send(f"Error generating card: {str(e)}")
            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error in generate_card: {str(e)}")

    @commands.slash_command()
    async def generate_champion_card(
        self,
        inter: disnake.ApplicationCommandInteraction,
        gamemode: str = commands.Param(choices=["ARAM", "Summoner's Rift", "Arena", "Nexus Blitz", "Swarm", "Ultimate Book", "URF"]),
        champion: str = commands.Param(autocomplete=_champion_autocomplete_wrapper)

    ):
        """
        Generate a champion card with stats
        
        Parameters
        ----------
        champion: The champion to generate a card for
        gamemode: The game mode to show stats for
        """
        if not await self.bot.is_botlol_channel(inter):
            return
        
        await inter.response.defer()
        gamemode = translate(gamemode)
        card_file = await self.bot.get_cog("CardGenerator").generate_champion_card(champion, gamemode)
        await inter.followup.send(file=card_file)

    @commands.slash_command()
    async def apply_lol_update(
        self,
        inter: disnake.ApplicationCommandInteraction
    ):
        """
        Populate the champions table with the latest data from Riot (requires admin permissions).
        """
        # Add permission check if needed
        if not await self.bot.is_botlol_channel(inter):
            return
        if not inter.author.guild_permissions.administrator:
             await inter.response.send_message("You need administrator permissions to run this command.", ephemeral=True)
             return

        await inter.response.defer()
        try:
            champions_added = await self.bot.get_cog('RiotAPIOperations').apply_lol_update(inter=inter)
            # The status is now handled by editing the original message within RiotAPIOperations
            # if champions_added is not None:
            #      await inter.followup.send(f"Successfully added/updated {champions_added} champions in the database.")
            # else:
            #      await inter.followup.send("Failed to fetch or insert champion data. Check bot logs.")
        except Exception as e:
            print(f"Error populating champions table: {e}")
            # Try to update the original message with the error, otherwise send a followup
            error_embed = disnake.Embed(title="LoL Data Update Error", description=f"An unexpected error occurred: {str(e)}", color=disnake.Color.red())
            try:
                await inter.edit_original_message(embed=error_embed)
            except:
                try:
                    await inter.followup.send(embed=error_embed)
                except Exception as followup_e:
                     print(f"Failed to send error followup for apply_lol_update: {followup_e}")

    # --- Leaderboard Command (Combined) ---
    @commands.slash_command(name="generate_leaderboard")
    async def generate_leaderboard(
        self,
        inter: disnake.ApplicationCommandInteraction,
        gamemode: str = commands.Param(choices=["ARAM", "Summoner's Rift", "Arena", "Nexus Blitz", "Swarm", "Ultimate Book", "URF"]),
        period: str = commands.Param(default="All Time", choices=["Weekly", "Monthly", "All Time"], description="Time period for stats"),
        limit: int = commands.Param(default=10, min_value=1, max_value=25, description="Number of players to display per board"),
        min_games: int = commands.Param(default=1, min_value=1, description="Minimum games for Win Rate board")
    ):
        """Displays KDA, Win Rate, and Pentakills leaderboards for tracked players as a card."""
        if not await self.bot.is_botlol_channel(inter):
            return
        if not inter.guild:
            await inter.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Use the original gamemode string for card generation theme/background lookup
        gamemode_raw = gamemode 
        gamemode_translated = translate(gamemode)
        await inter.response.defer() # Defer initial response
        
        db_cog = self.bot.get_cog("DatabaseOperations")
        card_gen_cog = self.bot.get_cog("CardGenerator")

        try:
            # Fetch data for all leaderboards, passing the period
            kda_data = await db_cog.get_leaderboard_kda(
                gamemode_translated, inter.guild.id, period=period, limit=limit
            )
            winrate_data = await db_cog.get_leaderboard_winrate(
                gamemode_translated, inter.guild.id, period=period, min_games=min_games, limit=limit
            )
            dpm_data = await db_cog.get_leaderboard_dpm(
                gamemode_translated, inter.guild.id, period=period, limit=limit
            )

            # Check if there is any data to display
            if not kda_data and not winrate_data and not dpm_data:
                 no_data_embed = disnake.Embed(
                    title=f"{inter.guild.name} - {gamemode} Leaderboards ({period})",
                    description=f"No tracked players found with relevant stats in {gamemode} for this server and period (min {min_games} games for Win Rate).",
                    color=disnake.Color.orange()
                 )
                 await inter.followup.send(embed=no_data_embed)
                 return

            # Generate the leaderboard card
            card_file = await card_gen_cog.generate_leaderboard_card(
                guild_name=inter.guild.name,
                gamemode=gamemode_raw, # Pass the raw gamemode key
                limit=limit,
                min_games=min_games,
                kda_data=kda_data,
                winrate_data=winrate_data,
                dpm_data=dpm_data # Pass dpm_data instead of pentakills_data
            )
            
            # Send the generated card
            await inter.followup.send(file=card_file)

        except Exception as e:
            print(f"Error generating leaderboard card: {e}") # Updated error message context
            # Also log the traceback for more detailed debugging
            import traceback
            traceback.print_exc()
            await inter.followup.send(f"An error occurred while generating the leaderboard card.")

def setup(bot):
    bot.add_cog(Commands(bot)) 