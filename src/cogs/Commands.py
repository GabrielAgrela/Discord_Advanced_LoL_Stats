from disnake.ext import commands
import disnake
import asyncio

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._player_names_cache = []
        self._last_cache_update = 0

    async def _get_player_names(self, inter: disnake.ApplicationCommandInteraction):
        # Update cache every 5 minutes
        current_time = asyncio.get_event_loop().time()
        if not self._player_names_cache or current_time - self._last_cache_update > 300:
            users = await self.bot.get_cog("DatabaseOperations").get_users(inter.guild.id)
            self._player_names_cache = [user[3] for user in users]  # username is at index 0
            self._last_cache_update = current_time
        return self._player_names_cache

    async def player_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str) -> list[str]:
        """Autocomplete function for player names"""
        try:
            player_names = await self._get_player_names(inter)
            filtered_names = [name for name in player_names if string.lower() in name.lower()]
            filtered_names.sort()  # Sort alphabetically
            return filtered_names[:25]
        except Exception as e:
            print(f"Error in autocomplete: {e}")
            return []

    @staticmethod
    async def _autocomplete_wrapper(inter: disnake.ApplicationCommandInteraction, string: str) -> list[str]:
        """Static wrapper for autocomplete to work with disnake's expectations"""
        try:
            cog = inter.bot.get_cog("Commands")
            if cog:
                return await cog.player_autocomplete(inter, string)
            return []
        except Exception as e:
            print(f"Error in autocomplete wrapper: {e}")
            return []

    @commands.slash_command()
    async def get_player_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        summoner_name: str = commands.Param(autocomplete=_autocomplete_wrapper),
        gamemode: str = commands.Param(choices=["ARAM", "CLASSIC", "CHERRY", "NEXUSBLITZ", "STRAWBERRY", "ULTBOOK", "URF"]),
        champion: str = commands.Param(default=None)
    ):
        """
        Get LoL stats for a summoner
        
        Parameters
        ----------
        summoner_name: The summoner name to look up
        gamemode: The game mode to get stats for
        champion: The champion to get stats for if you want to filter by a specific champion
        """
        if not await self.bot.is_botlol_channel(inter):
            return
            
        await inter.response.defer()
        try:
            data = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(summoner_name, gamemode, champion),
                timeout=10.0
            )
            if not data:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No {gamemode} stats found for {summoner_name} (or less than 4 games per champion)", color=disnake.Color.red()))
            else:
                await inter.followup.send(embed=disnake.Embed(title=f"{summoner_name} {gamemode} Stats", description=await self.bot.get_cog("DataFormatter").format_get_player_stats(data), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")

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
            data = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_all_players_stats(),
                timeout=10.0
            )
            if not data:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No stats found"))
            else:
                await inter.followup.send(embed=disnake.Embed(title="All Players Stats", description=await self.bot.get_cog("DataFormatter").format_get_all_players_stats(data), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")

    @commands.slash_command()
    async def player_vs_player(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        username1: str = commands.Param(autocomplete=_autocomplete_wrapper),
        username2: str = commands.Param(autocomplete=_autocomplete_wrapper),
        gamemode: str = commands.Param(default="ARAM", choices=["ARAM", "CLASSIC", "CHERRY", "NEXUSBLITZ", "STRAWBERRY", "ULTBOOK", "URF"]),
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
        
        await inter.response.defer()
        try:
            data_user1 = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(username1, gamemode, champion),
                timeout=10.0
            )
            if not data_user1:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No {gamemode} stats found for {username1} (or less than 4 games per champion)", color=disnake.Color.red()))
                return
            data_user2 = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(username2, gamemode, champion),
                timeout=10.0
            )
            if not data_user2:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No {gamemode} stats found for {username2} (or less than 4 games per champion)", color=disnake.Color.red()))
                return
            await inter.followup.send(embed=disnake.Embed(title=f"{username1} vs {username2} {gamemode} Stats", description=await self.bot.get_cog("DataFormatter").format_player_vs_player(data_user1, data_user2, username1, username2), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")

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
            data = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_friend_stats(username),
                timeout=10.0
            )
            if not data:
                await inter.followup.send(embed=disnake.Embed(title="No stats found", description=f"No duo stats found for {username} (minimum 5 games together required)", color=disnake.Color.red()))
                return
            await inter.followup.send(embed=disnake.Embed(title=f"{username} Friends Stats", description=await self.bot.get_cog("DataFormatter").format_player_friends_data(data, username), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")

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
        total_matches = await self.bot.get_cog('RiotAPIOperations').update_database(inter)
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
        await self.bot.get_cog("DatabaseOperations").insert_user(full_name, data["puuid"], data["gameName"], data["tagLine"])
        await inter.response.send_message(f"Added {full_name} to the database", ephemeral=True)

    @commands.slash_command()
    async def generate_card(
        self,
        inter: disnake.ApplicationCommandInteraction,
        summoner_name: str = commands.Param(autocomplete=_autocomplete_wrapper),
        gamemode: str = commands.Param(choices=["ARAM", "CLASSIC", "CHERRY", "NEXUSBLITZ", "STRAWBERRY", "ULTBOOK", "URF"])
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
        
        try:
            # Get player stats
            data = await self.bot.get_cog("DatabaseOperations").get_player_stats(summoner_name, gamemode)
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

def setup(bot):
    bot.add_cog(Commands(bot)) 