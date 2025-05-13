import disnake
from disnake.ext import commands
import os
from pathlib import Path
from dotenv import load_dotenv

class LoLStatsBot(commands.InteractionBot):
    def __init__(self):
        intents = disnake.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        # Initialize botlol_channel_id to None, will be set in on_ready
        self.botlol_channel_id = None
        self.current_game_patch = "15.2.1"
        
        super().__init__(
            intents=intents,
            reload=True  # Enables hot-reloading of cogs during development
        )
        self.load_extensions()

    def load_extensions(self):
        """Loads all cogs from the cogs directory"""
        for cog in Path("./src/cogs").glob("*.py"):
            if cog.stem != "__init__":
                self.load_extension(f"src.cogs.{cog.stem}")
                print(f"Loaded extension {cog.stem}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
        # Create botlol channel in all guilds if it doesn't exist and store the first one's ID
        for guild in self.guilds:
            channel = next((channel for channel in guild.text_channels if channel.name == "botlol"), None)
            if not channel:
                channel = await guild.create_text_channel("botlol")
            if self.botlol_channel_id is None:
                self.botlol_channel_id = channel.id

        versions = await self.get_cog("RiotAPIOperations").get_versions()
        self.current_game_patch = versions[0] if versions else None
       # await self.get_cog("Loops").check_if_in_game()

    async def on_guild_join(self, guild: disnake.Guild):
        """Create botlol channel when bot joins a new guild"""
        if not any(channel.name == "botlol" for channel in guild.text_channels):
            await guild.create_text_channel("botlol")

    async def is_botlol_channel(self, inter: disnake.ApplicationCommandInteraction) -> bool:
        """Global check for botlol channel"""
        # First check if we're in a guild at all
        if not inter.guild:
            await inter.response.send_message("This command can only be used in the #botlol channel in a server!", ephemeral=True)
            return False
            
        channel = inter.channel
        
        # Get the actual channel object if we have a partial
        if isinstance(channel, disnake.PartialMessageable):
            channel = inter.guild.get_channel(channel.id)
            
        # Check if this is a guild channel
        if not isinstance(channel, disnake.TextChannel):
            await inter.response.send_message("This command can only be used in the #botlol channel in a server!", ephemeral=True)
            return False
            
        if channel.name != "botlol":
            await inter.response.send_message("This command can only be used in the #botlol channel!", ephemeral=True)
            return False
        return True

    async def send_message(self, guild: disnake.Guild, title: str, description: str) -> None:
        """
        Sends an embedded message to the botlol channel in the specified guild.
        
        Args:
            guild: The guild to send the message to
            title: The title of the embed
            description: The description of the embed
        """
        # Find the botlol channel
        botlol_channel = next((channel for channel in guild.text_channels if channel.name == "botlol"), None)
        
        if botlol_channel:
            # Create the embed
            embed = disnake.Embed(
                title=title,
                description=description,
                color=disnake.Color.blue()
            )
            
            # Send the message
            await botlol_channel.send(embed=embed)

def main():
    # Load .env from the project root (one folder up from src)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("No Discord token found in environment variables")
        
    bot = LoLStatsBot()
    bot.run(token)

if __name__ == "__main__":
    main() 