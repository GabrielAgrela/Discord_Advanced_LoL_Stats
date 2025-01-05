import disnake
from disnake.ext import commands
import os
from datetime import datetime
import math
from playwright.async_api import async_playwright
import jinja2
import io
import base64

class CardGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.template_path = "/app/src/cogs/templates"
        self.assets_path = "/app/src/assets"
        
        # Define gamemode color themes
        self.gamemode_themes = {
            "ARAM": {
                "primary": "rgb(89, 155, 201)",     # Ice blue
                "overlay_start": "rgba(32, 45, 58, 0.9)",
                "overlay_end": "rgba(22, 31, 40, 0.95)"
            },
            "CLASSIC": {
                "primary": "rgb(86, 171, 47)",      # Forest green
                "overlay_start": "rgba(35, 46, 32, 0.9)",
                "overlay_end": "rgba(24, 31, 22, 0.95)"
            },
            "STRAWBERRY": {
                "primary": "rgb(255, 105, 180)",    # Hot pink
                "overlay_start": "rgba(58, 32, 45, 0.9)",
                "overlay_end": "rgba(40, 22, 31, 0.95)"
            },
            "NEXUSBLITZ": {
                "primary": "rgb(255, 215, 0)",      # Gold
                "overlay_start": "rgba(58, 49, 32, 0.9)",
                "overlay_end": "rgba(40, 34, 22, 0.95)"
            },
            "CHERRY": {
                "primary": "rgb(255, 99, 71)",      # Tomato red
                "overlay_start": "rgba(58, 35, 32, 0.9)",
                "overlay_end": "rgba(40, 24, 22, 0.95)"
            },
            "ULTBOOK": {
                "primary": "rgb(147, 112, 219)",    # Purple
                "overlay_start": "rgba(45, 32, 58, 0.9)",
                "overlay_end": "rgba(31, 22, 40, 0.95)"
            },
            "URF": {
                "primary": "rgb(255, 223, 0)",      # Bright gold
                "overlay_start": "rgba(58, 54, 32, 0.9)",
                "overlay_end": "rgba(40, 37, 22, 0.95)"
            }
        }
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_path),
            autoescape=True
        )
            
    def get_winrate_color(self, winrate):
        """Return RGB color tuple based on winrate percentage"""
        if winrate <= 40:
            return (255, 0, 0)
        elif winrate >= 60:
            return (0, 255, 0)
        else:
            t = (winrate - 40) / 20
            if t <= 0.5:
                t2 = t * 2
                t3 = t2 * t2 * t2
                return (255, int(255 * t3), 0)
            else:
                t2 = (t - 0.5) * 2
                green = 255
                red = int(255 * (1 - (t2 * t2)))
                return (red, green, 0)

    def get_kda_color(self, kda, theme):
        """Return RGB color tuple based on KDA value"""
        t = min(kda, 6.0) / 6.0
        
        if t <= 0.5:
            t2 = t * 2
            return (255, int(255 * (t2 * t2)), 0)
        else:
            t2 = (t - 0.5) * 2
            return (int(255 * (1 - t2)), 255, 0)

    async def generate_player_card(self, summoner_name: str, gamemode: str, data: list) -> disnake.File:
        """Generate a player card as an image file"""
        # Prepare template data
        theme = self.gamemode_themes.get(gamemode, self.gamemode_themes["CLASSIC"])
        
        total_games = data[0][5]
        total_hours = data[0][9]
        total_pentas = data[0][13]
        
        # Prepare champion data
        champions = []
        for row in data[:10]:
            winrate = row[2]
            kda = row[4]
            champions.append({
                'name': row[0][:15],
                'games': row[1],
                'pentas': row[12],
                'winrate': f"{winrate:.1f}",
                'winrate_color': self.get_winrate_color(winrate),
                'kda': f"{kda:.2f}",
                'kda_color': self.get_kda_color(kda, theme)
            })
        
        # Read and encode background image
        bg_image_path = os.path.join(self.assets_path, "images", f"{gamemode}.png")
        with open(bg_image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()
        
        # Render template
        template = self.jinja_env.get_template('player_card.html')
        html_content = template.render(
            summoner_name=summoner_name,
            gamemode=gamemode,
            theme_color=theme['primary'],
            total_games=total_games,
            total_hours=int(total_hours),
            total_pentas=total_pentas,
            champions=champions,
            background_image=encoded_image
        )
        
        # Use playwright to render HTML to image
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 600, 'height': 100})
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            
            # Wait for background image and fonts to load
            await page.wait_for_timeout(500)
            
            # Get the actual content height
            content_height = await page.evaluate('document.body.scrollHeight')
            
            # Resize viewport to match content
            await page.set_viewport_size({'width': 600, 'height': content_height})
            
            # Take screenshot of the entire content
            screenshot = await page.screenshot()
            await browser.close()
            
            # Convert to discord file
            image_binary = io.BytesIO(screenshot)
            return disnake.File(fp=image_binary, filename='player_card.png')

def setup(bot):
    bot.add_cog(CardGenerator(bot)) 