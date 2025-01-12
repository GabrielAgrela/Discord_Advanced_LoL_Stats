import disnake
from disnake.ext import commands
import os
from datetime import datetime
import math
from playwright.async_api import async_playwright
import jinja2
import io
import base64
from typing import List
from PIL import Image, ImageFilter, ImageDraw
from ..models.models import PlayerStats


class CardGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.template_path = "/app/src/assets/templates"
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
            
    def get_winrate_color(self, winrate: float) -> tuple[int, int, int]:
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

    def get_kda_color(self, kda: float, theme: dict) -> tuple[int, int, int]:
        """Return RGB color tuple based on KDA value"""
        t = min(kda, 6.0) / 6.0
        
        if t <= 0.5:
            t2 = t * 2
            return (255, int(255 * (t2 * t2)), 0)
        else:
            t2 = (t - 0.5) * 2
            return (int(255 * (1 - t2)), 255, 0)

    def format_champion_name(self, name):
        # Remove special characters and spaces, keeping letters and numbers
        name = ''.join(c for c in name if c.isalnum())
        
        # Generate variations
        variations = [
            name,  # Original (cleaned)
            name.lower(),  # all lowercase
            name.capitalize(),  # First letter capital
            ''.join(word.capitalize() for word in name.lower()),  # CamelCase
        ]
        return list(set(variations))  # Remove duplicates

    def load_champion_image(self, champion_name, image_type="tiles"):
        """
        Load champion image with support for different image types/paths
        image_type can be: tiles, centered, splash
        """
        name_variations = self.format_champion_name(champion_name)
        
        success = False
        for name in name_variations:
            try:
                champion_image_path = os.path.join(self.assets_path, "gamedata", "img", "champion", image_type, f"{name}_0.jpg")
                if os.path.exists(champion_image_path):
                    with open(champion_image_path, "rb") as image_file:
                        return base64.b64encode(image_file.read()).decode()
            except Exception:
                continue
        
        raise ValueError(f"Could not find champion image for {champion_name} in {image_type}")

    async def generate_player_card(self, summoner_name: str, gamemode: str, data: List[PlayerStats]) -> disnake.File:
        """Generate a player card as an image file"""
        # Prepare template data
        theme = self.gamemode_themes.get(gamemode, self.gamemode_themes["CLASSIC"])
        
        first_stat = data[0]
        total_games = first_stat.total_games_overall
        total_hours = first_stat.total_hours_played
        total_pentas = first_stat.total_pentas_overall
        total_winrate = first_stat.total_winrate
        
        # Prepare champion data
        champions = []
        for stat in data[:10]:  # Only show top 5 champions
            winrate = stat.winrate
            kda = stat.average_kda
            
            # Read and encode champion images with different types
            encoded_champion_image = self.load_champion_image(stat.champion_name, "centered")
            max_killing_spree_champion = self.load_champion_image(stat.max_killing_spree_champion, "splash")
            max_kda_champion = self.load_champion_image(stat.max_kda_champion, "splash")
            
            champions.append({
                'name': stat.champion_name[:15],
                'games': stat.champion_games,
                'pentas': stat.total_pentas,
                'damage_per_min': f"{stat.avg_damage_per_minute:.0f}",
                'avg_time_dead_pct': f"{stat.avg_time_dead_pct:.1f}%",
                'winrate': f"{winrate:.1f}",
                'winrate_color': self.get_winrate_color(winrate),
                'kda': f"{kda:.2f}",
                'kda_color': self.get_kda_color(kda, theme),
                'image': encoded_champion_image,
                'max_killing_spree': stat.max_killing_spree,
                'max_kda': f"{stat.max_kda:.1f}",
                'max_killing_spree_image': max_killing_spree_champion,
                'max_kda_image': max_kda_champion,
                'total_first_bloods': stat.total_first_bloods,
                'total_objectives': stat.total_objectives,
                'avg_vision_score': f"{stat.avg_vision_score:.1f}",
                'avg_kill_participation': f"{stat.avg_kill_participation:.1f}",
                'avg_gold_per_min': f"{stat.avg_gold_per_min:.0f}",
                'avg_damage_taken_per_min': f"{stat.avg_damage_taken_per_min:.0f}"
            })
        
        # Read and encode background image
        bg_image_path = os.path.join(self.assets_path, "images", f"{gamemode}.png")
        with open(bg_image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()
            
        # Read and encode profile icon - find latest patch folder
        gamedata_path = os.path.join(self.assets_path, "gamedata")
        patch_folders = [d for d in os.listdir(gamedata_path) if os.path.isdir(os.path.join(gamedata_path, d)) and d not in ['img']]
        latest_patch = sorted(patch_folders)[0] if patch_folders else "15.1.1"  # Fallback to 15.1.1 if no folders found
        
        profile_icon_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon", f"{data[0].profile_icon}.png")
        with open(profile_icon_path, "rb") as image_file:
            encoded_profile_icon = base64.b64encode(image_file.read()).decode()
        
        # Render template
        template = self.jinja_env.get_template('player_card.html')
        html_content = template.render(
            summoner_name=summoner_name,
            gamemode=gamemode,
            theme_color=theme['primary'],
            total_games=total_games,
            total_hours=int(total_hours),
            total_pentas=total_pentas,
            total_winrate=total_winrate,
            total_winrate_color=self.get_winrate_color(total_winrate),
            champions=champions,
            background_image=encoded_image,
            profile_icon=encoded_profile_icon,
            summoner_level=data[0].summoner_level
        )
        
        # Use playwright to render HTML to image
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 600, 'height': 100})
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            
            # Wait for background image and fonts to load
            await page.wait_for_timeout(500)
            
            # Resize viewport to match content
            await page.set_viewport_size({'width': 1500, 'height': 1300})
            
            # Take screenshot of the entire content
            screenshot = await page.screenshot()
            await browser.close()

            # Convert bytes to BytesIO and process image
            img_byte_arr = io.BytesIO(screenshot)
            image = Image.open(img_byte_arr)
            
            # Create a mask for rounded corners
            mask = Image.new('L', (image.width, image.height), 0)
            radius = 100  # Increased corner radius
            
            # Draw the rounded rectangle on the mask
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([(0, 0), (image.width-1, image.height-1)], radius=radius, fill=255)
            
            # Create output image with transparency
            output_image = Image.new('RGBA', image.size, (0, 0, 0, 0))
            output_image.paste(image, mask=mask)
            
            # Save to BytesIO
            output = io.BytesIO()
            output_image.save(output, format='PNG')
            output.seek(0)
            
            # Return as discord file
            return disnake.File(fp=output, filename='player_card.png')

    async def generate_live_players_card(self, players: list) -> disnake.File:
        """Generate a card showing all currently active players."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create Jinja2 environment
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.template_path)
            )
            template = env.get_template('live_players_card.html')

            # Get the first player's gamemode for theming
            theme = self.gamemode_themes.get(players[0]['gameMode'], self.gamemode_themes['CLASSIC'])

            # Find latest patch folder for profile icons
            gamedata_path = os.path.join(self.assets_path, "gamedata")
            patch_folders = [d for d in os.listdir(gamedata_path) if os.path.isdir(os.path.join(gamedata_path, d)) and d not in ['img']]
            latest_patch = sorted(patch_folders)[0] if patch_folders else "15.1.1"  # Fallback to 15.1.1 if no folders found

            # Prepare player data with champion icons and stats
            for player in players:
                # Load champion image (tiles for live players card)
                player['champion_icon'] = self.load_champion_image(player['champion'], "tiles")
                
                stats = player['stats']
                # Read and encode profile icon
                profile_icon_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon", f"{stats.profile_icon}.png")
                with open(profile_icon_path, "rb") as image_file:
                    player['profile_icon'] = base64.b64encode(image_file.read()).decode()
                
                # Format stats
                
                if stats:
                    player['games'] = stats.champion_games
                    player['winrate'] = f"{stats.winrate:.1f}"
                    player['kda'] = f"{stats.average_kda:.2f}"
                    player['pentas'] = stats.total_pentas
                    player['damage_per_min'] = f"{stats.avg_damage_per_minute:.0f}"
                    player['avg_time_dead_pct'] = f"{stats.avg_time_dead_pct:.1f}"
                    player['summoner_level'] = stats.summoner_level
                    
                    # Add color coding for winrate and KDA
                    player['winrate_color'] = self.get_winrate_color(stats.winrate)
                    player['kda_color'] = self.get_kda_color(stats.average_kda, theme)
                else:
                    player['games'] = 0
                    player['winrate'] = "N/A"
                    player['kda'] = "N/A"
                    player['pentas'] = 0
                    player['damage_per_min'] = "N/A"
                    player['avg_time_dead_pct'] = "N/A"
                    player['summoner_level'] = player.get('summonerLevel', 0)
                    player['winrate_color'] = (128, 128, 128)  # Gray for N/A
                    player['kda_color'] = (128, 128, 128)  # Gray for N/A

            # Read and encode background image
            bg_image_path = os.path.join(self.assets_path, "images", f"{players[0]['gameMode']}.png")
            with open(bg_image_path, "rb") as image_file:
                background_image = base64.b64encode(image_file.read()).decode()

            # Render template
            html_content = template.render(
                players=players,
                theme=theme,
                background_image=background_image
            )

            # Set content and viewport
            await page.set_content(html_content)
            await page.set_viewport_size({"width": 1500, "height": 1300})
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(500)

            # Take screenshot
            screenshot = await page.screenshot(
                type='png',
                full_page=True
            )

            await browser.close()

            # Convert bytes to BytesIO and process image
            img_byte_arr = io.BytesIO(screenshot)
            image = Image.open(img_byte_arr)
            
            # Create a mask for rounded corners
            mask = Image.new('L', (image.width, image.height), 0)
            radius = 50  # Increased corner radius
            
            # Draw the rounded rectangle on the mask
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([(0, 0), (image.width-1, image.height-1)], radius=radius, fill=255)
            
            # Create output image with transparency
            output_image = Image.new('RGBA', image.size, (0, 0, 0, 0))
            output_image.paste(image, mask=mask)
            
            # Save to BytesIO
            output = io.BytesIO()
            output_image.save(output, format='PNG')
            output.seek(0)
            
            # Return as discord file
            return disnake.File(
                fp=output,
                filename=f'live_players_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            )

def setup(bot):
    bot.add_cog(CardGenerator(bot)) 