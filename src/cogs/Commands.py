from disnake.ext import commands
import disnake
import asyncio

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def get_player_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        summoner_name: str = "sopustos",
        gamemode: str = commands.Param(default="ARAM", choices=["ARAM", "CLASSIC", "CHERRY", "NEXUSBLITZ", "STRAWBERRY", "ULTBOOK", "URF"]),
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
                await self.send_message(title="No stats found", description=f"No {gamemode} stats found for {summoner_name} (or less than 4 games per champion)")
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
                await self.send_message(title="No stats found", description=f"No stats found")
            else:
                await inter.followup.send(embed=disnake.Embed(title="All Players Stats", description=await self.bot.get_cog("DataFormatter").format_get_all_players_stats(data), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")

    @commands.slash_command()
    async def player_vs_player(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        username1: str,
        username2: str,
        champion: str,
        gamemode: str = commands.Param(default="ARAM", choices=["ARAM", "CLASSIC", "CHERRY", "NEXUSBLITZ", "STRAWBERRY", "ULTBOOK", "URF"])
    ):
        """
        Get LoL stats for two players vs each other
        
        Parameters
        ----------
        username1: The first player to look up
        username2: The second player to look up
        champion: The champion to get stats for
        gamemode: The game mode to get stats for (default is ARAM)
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
                await self.send_message(title="No stats found", description=f"No {gamemode} stats found for {username1} (or less than 4 games per champion)")
                return
            data_user2 = await asyncio.wait_for(
                self.bot.get_cog("DatabaseOperations").get_player_stats(username2, gamemode, champion),
                timeout=10.0
            )
            if not data_user2:
                await self.send_message(title="No stats found", description=f"No {gamemode} stats found for {username2} (or less than 4 games per champion)")
                return
            await inter.followup.send(embed=disnake.Embed(title=f"{username1} vs {username2} {gamemode} Stats", description=await self.bot.get_cog("DataFormatter").format_player_vs_player(data_user1, data_user2, username1, username2), color=disnake.Color.blue()))
        except Exception as e:
            await inter.followup.send(f"Some error occurred: {e}")

    @commands.slash_command()
    async def player_friends_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        username: str
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
                await self.send_message(title="No stats found", description=f"No duo stats found for {username} (minimum 5 games together required)")
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
        await inter.followup.send(embed=disnake.Embed(title="Updating database", description=f"Updating database with {await self.bot.get_cog('RiotAPIOperations').update_database()} new matches found", color=disnake.Color.blue()))
        
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
        username: The player to add to the database. Ex: "sopustos" and the #/tagline being "EUW" 
        """
        if not await self.bot.is_botlol_channel(inter):
            return
        data = await self.bot.get_cog("RiotAPIOperations").get_acc_from_riot_id(username, tagline)
        await self.bot.get_cog("DatabaseOperations").insert_user(username, data["puuid"], data["gameName"], data["tagLine"])
        await inter.response.send_message(f"Added {username} to the database", ephemeral=True)

def setup(bot):
    bot.add_cog(Commands(bot)) 