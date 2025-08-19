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
from ..Utils import translate


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
            
    def format_percentage(self, value: float) -> str:
        """Format percentage value, removing decimal if it ends in .0"""
        formatted = f"{value:.1f}"
        if formatted.endswith('.0'):
            return formatted[:-2]
        return formatted
            
    def get_winrate_color(self, winrate: float) -> tuple[int, int, int]:
        """Return RGB color tuple based on winrate percentage using specified gradient stops."""
        # Clamp input to [0, 100]
        value = max(0.0, min(100.0, float(winrate)))
        # Gradient stops: (percent, (r, g, b))
        stops = [
            (0.0,   (0, 0, 0)),          # black
            (25.0,  (255, 0, 0)),        # red
            (50.0,  (255, 255, 0)),      # yellow
            (75.0,  (0, 255, 0)),        # green
            (100.0, (51, 204, 255)),    # light blue
        ]
        # Interpolate between bounding stops
        for i in range(len(stops) - 1):
            left_pct, left_color = stops[i]
            right_pct, right_color = stops[i + 1]
            if left_pct <= value <= right_pct:
                span = right_pct - left_pct
                alpha = 0.0 if span == 0 else (value - left_pct) / span
                r = int(round(left_color[0] + (right_color[0] - left_color[0]) * alpha))
                g = int(round(left_color[1] + (right_color[1] - left_color[1]) * alpha))
                b = int(round(left_color[2] + (right_color[2] - left_color[2]) * alpha))
                return (r, g, b)
        # Fallback (should not occur due to clamping)
        return stops[-1][1]

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

        if name == "Fiddlesticks":
            name = "FiddleSticks"
        
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
        # If champion_name is None or empty, use Zed as default
        if not champion_name:
            champion_name = "Zed"
            
        name_variations = self.format_champion_name(translate(champion_name))
        
        # Try to load the requested champion image
        for name in name_variations:
            try:
                champion_image_path = os.path.join(self.assets_path, "gamedata", "img", "champion", image_type, f"{name}_0.jpg")
                if os.path.exists(champion_image_path):
                    with open(champion_image_path, "rb") as image_file:
                        return base64.b64encode(image_file.read()).decode()
            except Exception:
                continue
        
        # If the requested champion image is not found, try to load Zed as fallback
        try:
            zed_image_path = os.path.join(self.assets_path, "gamedata", "img", "champion", image_type, "Zed_0.jpg")
            if os.path.exists(zed_image_path):
                with open(zed_image_path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode()
        except Exception:
            pass
            
        # If all else fails, raise an error
        raise ValueError(f"Could not find champion image for {champion_name} in {image_type} and fallback to Zed failed")

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
            max_killing_spree_champion = self.load_champion_image(stat.max_killing_spree_champion, "centered")
            max_kda_champion = self.load_champion_image(stat.max_kda_champion, "centered")
            
            champions.append({
                'name': stat.champion_name[:15],
                'games': stat.champion_games,
                'pentas': stat.total_pentas,
                'damage_per_min': f"{stat.avg_damage_per_minute:.0f}",
                'avg_time_dead_pct': f"{stat.avg_time_dead_pct:.1f}%",
                'winrate': f"{self.format_percentage(winrate)}",
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
                'avg_kill_participation': f"{self.format_percentage(stat.avg_kill_participation)}",
                'avg_gold_per_min': f"{stat.avg_gold_per_min:.0f}",
                'avg_damage_taken_per_min': f"{stat.avg_damage_taken_per_min:.0f}"
            })
        
        # Read and encode background image
        bg_image_path = os.path.join(self.assets_path, "images", f"{gamemode}.png")
        try:
            with open(bg_image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode()
        except FileNotFoundError:
            encoded_image = None
            
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
            gamemode=translate(gamemode),
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
            
            # Set content and wait for it to load
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(500)

            # Get page dimensions
            dimensions = await page.evaluate('''() => {
                return {
                    width: document.documentElement.scrollWidth,
                    height: document.documentElement.scrollHeight
                }
            }''')
            
            # Set viewport to match content dimensions
            await page.set_viewport_size(dimensions)

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
            gamemode = players[0]['gameMode']
            theme = self.gamemode_themes.get(gamemode, self.gamemode_themes['CLASSIC'])

            # Find latest patch folder for profile icons
            gamedata_path = os.path.join(self.assets_path, "gamedata")
            patch_folders = [d for d in os.listdir(gamedata_path) if os.path.isdir(os.path.join(gamedata_path, d)) and d not in ['img']]
            latest_patch = sorted(patch_folders)[0] if patch_folders else "15.1.1"

            # Prepare player data with champion icons and stats
            is_arena = gamemode in ['CHERRY', 'ARENA']
            for player in players:
                # Load champion images
                player['champion_icon'] = self.load_champion_image(player['champion'], "tiles")
                # Background image behind summoner info uses centered crop
                player['champion_centered'] = self.load_champion_image(player['champion'], "centered")
                # Background image behind summoner info uses centered crop
                player['champion_splash'] = self.load_champion_image(player['champion'], "splash")
                
                stats = player['stats']
                # Read and encode profile icon
                profile_icon_id = stats.profile_icon
                
                # Find latest patch folder for profile icons
                gamedata_path = os.path.join(self.assets_path, "gamedata")
                patch_folders = [d for d in os.listdir(gamedata_path) if os.path.isdir(os.path.join(gamedata_path, d)) and d not in ['img']]
                latest_patch = sorted(patch_folders)[0] if patch_folders else "15.1.1"
                
                # Try to load the profile icon
                profile_icon_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon", f"{profile_icon_id}.png")
                try:
                    if os.path.exists(profile_icon_path):
                        with open(profile_icon_path, "rb") as img_file:
                            player['profile_icon'] = base64.b64encode(img_file.read()).decode('utf-8')
                    else:
                        # Try default profile icon 0
                        default_icon_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon", "0.png")
                        with open(default_icon_path, "rb") as img_file:
                            player['profile_icon'] = base64.b64encode(img_file.read()).decode('utf-8')
                except FileNotFoundError:
                    # If even default icon is missing, use an empty string
                    print(f"Warning: Could not find profile icon {profile_icon_id} or default icon")
                    player['profile_icon'] = ""
                
                # Format stats
                
                if stats:
                    player['games'] = stats.champion_games
                    player['winrate'] = f"{self.format_percentage(stats.winrate)}"
                    player['kda'] = f"{stats.average_kda:.2f}"
                    # For Cherry/Arena modes, show first place count instead of pentas
                    if is_arena:
                        player['pentas'] = stats.first_place_count
                        player['pentas_label'] = '1st Places'
                        player['avg_placement'] = f"{stats.avg_placement:.2f}"
                    else:
                        player['pentas'] = stats.total_pentas
                        player['pentas_label'] = 'Pentas'
                        player['avg_placement'] = None
                    player['damage_per_min'] = f"{stats.avg_damage_per_minute:.0f}"
                    # Arena dead% is unreliable; hide it by template logic
                    player['avg_time_dead_pct'] = f"{self.format_percentage(stats.avg_time_dead_pct)}"
                    player['summoner_level'] = stats.summoner_level
                    
                    # Add color coding for winrate and KDA
                    player['winrate_color'] = self.get_winrate_color(stats.winrate)
                    player['kda_color'] = self.get_kda_color(stats.average_kda, theme)
                else:
                    player['games'] = 0
                    player['winrate'] = "N/A"
                    player['kda'] = "N/A"
                    player['pentas'] = 0
                    player['pentas_label'] = 'Pentas'  # Default label
                    player['avg_placement'] = None
                    player['damage_per_min'] = "N/A"
                    player['avg_time_dead_pct'] = "N/A"
                    player['summoner_level'] = player.get('summonerLevel', 0)
                    player['winrate_color'] = (128, 128, 128)  # Gray for N/A
                    player['kda_color'] = (128, 128, 128)  # Gray for N/A

            # Read and encode background image
            bg_image_path = os.path.join(self.assets_path, "images", f"{gamemode}.png")
            try:
                with open(bg_image_path, "rb") as image_file:
                    background_image = base64.b64encode(image_file.read()).decode()
            except FileNotFoundError:
                background_image = None

            # Render template
            html_content = template.render(
                players=players,
                gamemode=translate(gamemode),
                theme=theme,
                background_image=background_image,
                is_arena=is_arena
            )

            # Set content and wait for it to load
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(500)

            # Get page dimensions
            dimensions = await page.evaluate('''() => {
                return {
                    width: document.documentElement.scrollWidth,
                    height: document.documentElement.scrollHeight
                }
            }''')
            
            # Set viewport to match content dimensions
            await page.set_viewport_size(dimensions)

            # Take screenshot
            screenshot = await page.screenshot(
                type='png',
                full_page=True
            )

            await browser.close()
            
            # Return as discord file
            return disnake.File(fp=io.BytesIO(screenshot), filename='live_players.png')

    async def generate_finished_game_card(self, game_id):
        """Generate individual cards for each tracked player in a finished game."""
        db_ops = self.bot.get_cog("DatabaseOperations")
        riot_ops = self.bot.get_cog("RiotAPIOperations")
        
        # Get match information from database
        match_info = await db_ops.get_match_info(game_id)
        if not match_info:
            raise ValueError(f"Match with game_id {game_id} not found in database")
        
        gamemode, game_duration, game_end, game_creation = match_info
        
        # Get all participants data
        participants = await db_ops.get_match_participants(game_id)
        if not participants:
            raise ValueError(f"No participants found for game_id {game_id}")
        
        # Add game_duration to each participant
        for p in participants:
            p['game_duration'] = game_duration
        
        # Get tracked users from database
        tracked_users = await db_ops.get_users()
        tracked_summoner_ids = [user.puuid for user in tracked_users]
        
        # Separate participants into teams
        team1 = []
        team2 = []
        team1_kills = 0
        team2_kills = 0
        team1_gold = 0
        team2_gold = 0
        team1_damage = 0
        team2_damage = 0
        
        # Process all participants for team stats
        for p in participants:
            # Load champion icon using the load_champion_image method
            champion = p.get('champion_name', 'Zed')
            try:
                champion_icon = self.load_champion_image(champion, "tiles")
            except ValueError as e:
                print(f"Warning: Could not load champion image for {champion}: {e}")
                # Try with Zed as fallback
                champion_icon = self.load_champion_image("Zed", "tiles")
            
            # Load profile icon
            profile_icon_id = p.get('profile_icon', 0)
            
            # Find latest patch folder for profile icons
            gamedata_path = os.path.join(self.assets_path, "gamedata")
            patch_folders = [d for d in os.listdir(gamedata_path) if os.path.isdir(os.path.join(gamedata_path, d)) and d not in ['img']]
            latest_patch = sorted(patch_folders)[0] if patch_folders else "15.1.1"
            
            # Try to load the profile icon
            profile_icon_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon", f"{profile_icon_id}.png")
            
            try:
                if os.path.exists(profile_icon_path):
                    with open(profile_icon_path, "rb") as img_file:
                        profile_icon_img = base64.b64encode(img_file.read()).decode('utf-8')
                else:
                    # Try default profile icon 0
                    default_icon_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon", "0.png")
                    with open(default_icon_path, "rb") as img_file:
                        profile_icon_img = base64.b64encode(img_file.read()).decode('utf-8')
            except FileNotFoundError:
                # If even default icon is missing, use an empty string
                print(f"Warning: Could not find profile icon {profile_icon_id} or default icon")
                profile_icon_img = ""
            
            # Add champion icon and profile icon to participant data
            p['champion_icon'] = champion_icon
            p['profile_icon_img'] = profile_icon_img
            
            # Calculate KDA
            if p['deaths'] == 0:
                p['kda'] = p['kills'] + p['assists']
            else:
                p['kda'] = round((p['kills'] + p['assists']) / p['deaths'], 2)
            
            # Add to appropriate team
            if p['team_id'] == 100:
                team1.append(p)
                team1_kills += p.get('kills', 0)
                team1_gold += p.get('gold_earned', 0)
                team1_damage += p.get('total_damage_to_champions', 0)
            else:
                team2.append(p)
                team2_kills += p.get('kills', 0)
                team2_gold += p.get('gold_earned', 0)
                team2_damage += p.get('total_damage_to_champions', 0)
        
        # Identify tracked players and prepare their data
        tracked_players = []
        for p in participants:
            if p['puuid'] in tracked_summoner_ids:
                # Load champion splash art for banner using the load_champion_image method
                champion = p.get('champion_name', 'Zed')
                try:
                    p['champion_splash'] = self.load_champion_image(champion, "centered")
                except ValueError as e:
                    print(f"Warning: Could not load champion splash for {champion}: {e}")
                    # Try with Zed as fallback
                    p['champion_splash'] = self.load_champion_image("Zed", "centered")
                
                # Get player stats for comparison
                player_stats = await db_ops.get_player_stats(p['riot_id_game_name'], gamemode, champion)
                
                # Get first player stats object if available
                player_stat = player_stats[0] if player_stats else None
                
                # Calculate combat efficiency (skip time-dead in Arena due to unreliable values)
                damage_dealt = p.get('total_damage_to_champions', 0)
                damage_mitigated = p.get('damage_self_mitigated', 0)
                if gamemode in ['CHERRY', 'ARENA']:
                    time_dead_pct = 0
                else:
                    time_dead_pct = p.get('total_time_spent_dead', 0) / p.get('game_duration', 1800) * 100 if p.get('game_duration', 1800) > 0 else 0
                
                # Calculate combat efficiency score: (damage dealt + damage mitigated) / (1 + time dead percentage)
                combat_efficiency = (damage_dealt + damage_mitigated) / (1 + time_dead_pct/10) if time_dead_pct > 0 else damage_dealt + damage_mitigated
                
                # Normalize to a 0-100 scale for easier understanding
                normalized_efficiency = min(100, combat_efficiency / 1000)
                
                # Store the combat efficiency value
                p['combat_efficiency'] = normalized_efficiency
                
                # Normalize kill participation to percentage (0-100) before any classification/comparison
                if 'kill_participation' in p:
                    current_kp = p.get('kill_participation', 0)
                    if current_kp <= 1:
                        p['kill_participation'] = current_kp * 100
                    else:
                        p['kill_participation'] = current_kp

                # Process player stats for tracked players
                p['performance'] = {
                    'kda': p.get('kda', 0),
                    'kda_class': self._classify_stat(p.get('kda', 0), getattr(player_stat, 'average_kda', 2.5), 1.5),
                    'dmg_class': self._classify_stat(p.get('total_damage_to_champions', 0), getattr(player_stat, 'avg_damage_per_minute', 500) * (p.get('game_duration', 1800) / 60), 5000),
                    'kp_class': self._classify_stat(p.get('kill_participation', 0), getattr(player_stat, 'avg_kill_participation', 50), 15),
                    # Compare CS against expected CS for the game duration based on avg CS per minute
                    'cs_class': self._classify_stat(
                        p.get('total_minions_killed', 0),
                        (getattr(player_stat, 'avg_cs_per_min', 5.0) * (p.get('game_duration', 1800) / 60)),
                        30
                    ),
                    'gold_class': self._classify_stat(p.get('gold_earned', 0), getattr(player_stat, 'avg_gold_per_min', 350) * (p.get('game_duration', 1800) / 60), 2000),
                    'efficiency_class': self._classify_stat(normalized_efficiency, 50, 15)
                }
                
                # Calculate comparisons to average
                comparison = {}
                
                # Initialize all comparison keys with default values
                comparison['kda_percent'] = 0
                comparison['dmg_percent'] = 0
                comparison['cs_percent'] = 0
                comparison['gold_percent'] = 0
                comparison['efficiency_percent'] = 0
                comparison['kp'] = 0
                comparison['kda'] = 0
                comparison['damage'] = 0
                comparison['efficiency'] = 0
                
                # Default values for comparison if player_stat is None
                default_avg_kda = 2.5
                default_avg_dpm = 500
                default_avg_cs_per_min = 5.0
                default_avg_gold_per_min = 350
                default_avg_efficiency = 50
                default_avg_kp = 50
                
                # Get game duration in minutes for calculations
                game_duration_minutes = p.get('game_duration', 1800) / 60
                
                if player_stat:
                    # Calculate percentage differences from average
                    avg_kda = getattr(player_stat, 'average_kda', default_avg_kda)
                    if avg_kda > 0:
                        comparison['kda_percent'] = ((p.get('kda', 0) - avg_kda) / avg_kda) * 100
                    else:
                        comparison['kda_percent'] = 100 if p.get('kda', 0) > 0 else 0
                    
                    avg_dpm = getattr(player_stat, 'avg_damage_per_minute', default_avg_dpm)
                    if avg_dpm > 0:
                        expected_damage = avg_dpm * game_duration_minutes
                        actual_damage = p.get('total_damage_to_champions', 0)
                        comparison['dmg_percent'] = ((actual_damage - expected_damage) / expected_damage) * 100 if expected_damage > 0 else 0
                    
                    avg_cs_per_min = getattr(player_stat, 'avg_cs_per_min', default_avg_cs_per_min)
                    expected_cs = avg_cs_per_min * game_duration_minutes
                    if expected_cs > 0:
                        comparison['cs_percent'] = ((p.get('total_minions_killed', 0) - expected_cs) / expected_cs) * 100
                    
                    avg_gold_per_min = getattr(player_stat, 'avg_gold_per_min', default_avg_gold_per_min)
                    if avg_gold_per_min > 0:
                        expected_gold = avg_gold_per_min * game_duration_minutes
                        actual_gold = p.get('gold_earned', 0)
                        comparison['gold_percent'] = ((actual_gold - expected_gold) / expected_gold) * 100 if expected_gold > 0 else 0
                    else:
                        comparison['gold_percent'] = 100 if p.get('gold_earned', 0) > 0 else 0
                    
                    # Derive an average normalized combat efficiency from per-minute averages
                    avg_time_dead_pct = getattr(player_stat, 'avg_time_dead_pct', 15)
                    avg_mitigated_per_min = getattr(player_stat, 'avg_damage_taken_per_min', 500)
                    avg_expected_damage = avg_dpm * game_duration_minutes
                    avg_expected_mitigated = avg_mitigated_per_min * game_duration_minutes
                    avg_combat_efficiency = (avg_expected_damage + avg_expected_mitigated) / (1 + (avg_time_dead_pct / 10)) if avg_time_dead_pct > 0 else (avg_expected_damage + avg_expected_mitigated)
                    avg_normalized_efficiency = min(100, avg_combat_efficiency / 1000)
                    if avg_normalized_efficiency > 0:
                        comparison['efficiency_percent'] = ((normalized_efficiency - avg_normalized_efficiency) / avg_normalized_efficiency) * 100
                    else:
                        comparison['efficiency_percent'] = 100 if normalized_efficiency > 0 else 0
                    
                    # Calculate raw differences
                    comparison['kda'] = p.get('kda', 0) - avg_kda
                    comparison['damage'] = p.get('total_damage_to_champions', 0) - (avg_dpm * game_duration_minutes)
                    comparison['efficiency'] = normalized_efficiency - avg_normalized_efficiency
                    
                    # Add kill participation comparison
                    # kill_participation already normalized to percentage above
                    player_kp = p.get('kill_participation', 0)
                    
                    avg_kp = getattr(player_stat, 'avg_kill_participation', default_avg_kp)
                    comparison['kp'] = player_kp - avg_kp
                else:
                    # If no player_stat is available, use reasonable defaults for comparison
                    # This ensures we show some comparison values even for new players
                    current_kda = p.get('kda', 0)
                    comparison['kda_percent'] = ((current_kda - default_avg_kda) / default_avg_kda) * 100 if current_kda > 0 else 0
                    
                    expected_damage = default_avg_dpm * game_duration_minutes
                    actual_damage = p.get('total_damage_to_champions', 0)
                    comparison['dmg_percent'] = ((actual_damage - expected_damage) / expected_damage) * 100 if expected_damage > 0 else 0
                    
                    expected_cs = default_avg_cs_per_min * game_duration_minutes
                    comparison['cs_percent'] = ((p.get('total_minions_killed', 0) - expected_cs) / expected_cs) * 100 if expected_cs > 0 else 0
                    
                    expected_gold = default_avg_gold_per_min * game_duration_minutes
                    actual_gold = p.get('gold_earned', 0)
                    comparison['gold_percent'] = ((actual_gold - expected_gold) / expected_gold) * 100 if expected_gold > 0 else 0
                    
                    comparison['efficiency_percent'] = ((normalized_efficiency - default_avg_efficiency) / default_avg_efficiency) * 100
                    
                    comparison['kda'] = p.get('kda', 0) - default_avg_kda
                    comparison['damage'] = p.get('total_damage_to_champions', 0) - expected_damage
                    comparison['efficiency'] = normalized_efficiency - default_avg_efficiency
                    
                    # kill_participation already normalized to percentage above
                    player_kp = p.get('kill_participation', 0)
                    
                    comparison['kp'] = player_kp - default_avg_kp
                
                # Cap percentage values to prevent extreme outliers
                for key in ['kda_percent', 'dmg_percent', 'cs_percent', 'gold_percent', 'efficiency_percent']:
                    if key in comparison:
                        comparison[key] = max(min(comparison[key], 200), -100)  # Cap between -100% and +200%

                # Ensure all required fields exist for the template
                p['name'] = p.get('riot_id_game_name', 'Unknown')
                p['champion'] = p.get('champion_name', 'Unknown')
                p['win'] = p.get('wins', False)
                p['kills'] = p.get('kills', 0)
                p['deaths'] = p.get('deaths', 0)
                p['assists'] = p.get('assists', 0)
                p['damage'] = p.get('total_damage_to_champions', 0)
                p['damage_mitigated'] = p.get('damage_self_mitigated', 0)
                # For Arena: hide dead% downstream; keep 0 here to avoid misleading values
                if gamemode in ['CHERRY', 'ARENA']:
                    p['time_dead_pct'] = 0
                else:
                    p['time_dead_pct'] = p.get('total_time_spent_dead', 0) / p.get('game_duration', 1800) * 100 if p.get('game_duration', 1800) > 0 else 0
                
                # Calculate DPM (Damage Per Minute)
                game_minutes = p.get('game_duration', 1800) / 60
                p['dpm'] = round(p.get('total_damage_to_champions', 0) / game_minutes) if game_minutes > 0 else 0
                
                # kill_participation already normalized above
                
                p['cs'] = p.get('total_minions_killed', 0)
                p['gold'] = p.get('gold_earned', 0)
                p['vision_score'] = p.get('vision_score', 0)
                
                p['comparison'] = comparison
                
                # Prepare data for insights
                player_data = {
                    'champion': p.get('champion_name', 'this champion'),
                    'kills': p.get('kills', 0),
                    'assists': p.get('assists', 0),
                    'deaths': p.get('deaths', 0),
                    'kda': p.get('kda', 0),
                    'damage': p.get('total_damage_to_champions', 0),
                    'dpm': p.get('dpm', 0),
                    'game_duration': p.get('game_duration', 1800),
                    'kill_participation': p.get('kill_participation', 0),
                    'vision_score': p.get('vision_score', 0),
                    'cs': p.get('total_minions_killed', 0),
                    'gold': p.get('gold_earned', 0),
                    'damage_mitigated': p.get('damage_mitigated', 0),
                    'time_dead_pct': p.get('time_dead_pct', 0),
                    'gamemode': gamemode,
                    'placement': p.get('placement')
                }
                p['insights'] = await self._generate_champion_insights(player_data, player_stat)
                
                tracked_players.append(p)
        
        # Identify premade players (other tracked players in the game, regardless of team)
        for player in tracked_players:
            premades = []
            
            # Find other tracked players in the game
            for other_player in tracked_players:
                if other_player != player:  # Don't include the player themselves
                    premades.append({
                        'name': other_player['name'],
                        'champion': other_player['champion'],
                        'champion_icon': other_player.get('champion_icon', ''),
                        'profile_icon': other_player.get('profile_icon_img', '')
                    })
            
            # Add premades to player data
            player['premades'] = premades
        
        # Format game duration
        minutes = game_duration // 60
        seconds = game_duration % 60
        formatted_duration = f"{minutes}:{seconds:02d}"
        
        # Define gamemode-based background images
        gamemode_backgrounds = {
            "CLASSIC": "CLASSIC.png",
            "ARAM": "ARAM.png",
            "URF": "URF.png",
            "CHERRY": "CHERRY.png",
            "ARENA": "CHERRY.png",
            "NEXUSBLITZ": "NEXUSBLITZ.png",
            "SWIFTPLAY": "SWIFTPLAY.png",
            "STRAWBERRY": "STRAWBERRY.png"
        }
        
        # Default to Summoner's Rift if gamemode not found
        background_file = gamemode_backgrounds.get(gamemode, "CLASSIC.png")
        background_path = os.path.join(self.assets_path, "images", background_file)
        
        # Read and encode background image
        try:
            with open(background_path, "rb") as img_file:
                background_image = base64.b64encode(img_file.read()).decode('utf-8')
        except FileNotFoundError:
            # If file not found, set background_image to None
            print(f"Warning: Could not find background image for gamemode {gamemode}")
            background_image = None
        
        # Prepare theme colors
        theme = self.gamemode_themes.get(gamemode, {
            'primary': 'rgb(86, 171, 47)',      # Default to forest green
            'overlay_start': 'rgba(35, 46, 32, 0.9)',
            'overlay_end': 'rgba(24, 31, 22, 0.95)'
        })
        
        # List to store individual player cards
        player_cards = []
        
        # Generate individual cards for each tracked player
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            # Load the template
            template_loader = jinja2.FileSystemLoader(searchpath="src/assets/templates")
            template_env = jinja2.Environment(
                loader=template_loader,
                undefined=jinja2.Undefined  # Use default behavior for undefined values
            )
            template = template_env.get_template("finished_game_card.html")
            
            for player in tracked_players:
                # Create a page for this player's card
                page = await browser.new_page(viewport={"width": 1200, "height": 1000})
                
                # Render the template with only this player's data
                try:
                    html_content = template.render(
                        tracked_players=[player],  # Only include the current player
                        team1=team1,
                        team2=team2,
                        team1_kills=team1_kills,
                        team2_kills=team2_kills,
                        team1_gold=team1_gold or 0,
                        team2_gold=team2_gold or 0,
                        team1_damage=team1_damage or 0,
                        team2_damage=team2_damage or 0,
                        gamemode=gamemode or "Unknown",
                        gamemode_display=translate(gamemode or "Unknown"),
                        game_duration=formatted_duration,
                        background_image=background_image,
                        theme=theme
                    )
                except Exception as e:
                    print(f"Error rendering template for player {player['name']}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Set the content in the page
                await page.set_content(html_content)
                
                # Take a screenshot
                screenshot = await page.screenshot(full_page=True)
                
                # Create a Discord file for this player
                player_name = player['name'].replace(' ', '_')
                player_cards.append(disnake.File(
                    io.BytesIO(screenshot), 
                    filename=f"{player_name}_{player['champion']}_game.png"
                ))
                
                # Close the page
                await page.close()
            
            # Close the browser
            await browser.close()
        
        # If no cards were generated, raise an error
        if not player_cards:
            raise ValueError("No player cards could be generated")
        
        # Return the list of Discord files
        return player_cards

    def _classify_stat(self, value, avg, threshold):
        """Classify a stat as highlight, positive, or negative based on comparison to average."""
        if value > avg + (threshold * 1.5):
            return 'highlight'
        elif value > avg + (threshold * 0.5):
            return 'positive'
        elif value < avg - (threshold * 0.5):
            return 'negative'
        else:
            return 'neutral'

    async def _generate_champion_insights(self, player, player_stat, champion_stats=None):
        """Generate insights for a player based on their performance compared to champion averages."""
        insights = []
        
        # Handle case where player_stat might be a list
        if isinstance(player_stat, list) and player_stat:
            player_stat = player_stat[0]
        
        # If champion_stats is None, use player_stat as fallback
        if not champion_stats:
            champion_stats = player_stat
            champion_specific = False
        else:
            champion_specific = True
        
        # Get champion name
        champion_name = player.get('champion', 'this champion')
        
        # Try to get global champion stats if available
        db_ops = self.bot.get_cog("DatabaseOperations")
        gamemode = player.get('gamemode', 'CLASSIC')
        global_champion_stats = None
        
        if db_ops and champion_name:
            try:
                global_champion_stats = await db_ops.get_champion_global_stats(champion_name, gamemode)
            except Exception as e:
                print(f"Error getting global champion stats: {e}")
        
        # Check if this is one of their first games on this champion
        champion_games = getattr(champion_stats, 'champion_games', 0) if champion_specific else 0
        if champion_games < 3 and champion_specific:
            insights.append({
                'type': 'neutral',
                'icon': 'fas fa-baby',
                'text': f"This is one of your first games with {champion_name}! Keep practicing."
            })
        
        # KDA insights
        deaths = player.get('deaths', 0)
        kda = player.get('kda', 0)
        if deaths == 0:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-medal',
                'text': 'Perfect game with no deaths!'
            })
        
        # Use global stats if available, otherwise fall back to player stats
        if global_champion_stats:
            avg_kda = getattr(global_champion_stats, 'average_kda', 2.5)
            avg_dpm = getattr(global_champion_stats, 'avg_damage_per_minute', 500)
            avg_kp = getattr(global_champion_stats, 'avg_kill_participation', 50)
            avg_time_dead = getattr(global_champion_stats, 'avg_time_dead_pct', 15)
            avg_cs_per_min = getattr(global_champion_stats, 'avg_cs_per_min', 5)
            avg_gold_per_min = getattr(global_champion_stats, 'avg_gold_per_min', 350)
            avg_damage_taken_per_min = getattr(global_champion_stats, 'avg_damage_taken_per_min', 500)
            comparison_text = f"the average for {champion_name} in this game mode"
        else:
            avg_kda = getattr(champion_stats, 'average_kda', 2.5) if champion_specific else getattr(player_stat, 'average_kda', 2.5)
            avg_dpm = getattr(champion_stats, 'avg_damage_per_minute', 500) if champion_specific else getattr(player_stat, 'avg_damage_per_minute', 500)
            avg_kp = getattr(champion_stats, 'avg_kill_participation', 50) if champion_specific else getattr(player_stat, 'avg_kill_participation', 50)
            avg_time_dead = getattr(champion_stats, 'avg_time_dead_pct', 15) if champion_specific else getattr(player_stat, 'avg_time_dead_pct', 15)
            avg_cs_per_min = getattr(champion_stats, 'avg_cs_per_min', 5) if champion_specific else getattr(player_stat, 'avg_cs_per_min', 5)
            avg_gold_per_min = getattr(champion_stats, 'avg_gold_per_min', 350) if champion_specific else getattr(player_stat, 'avg_gold_per_min', 350)
            avg_damage_taken_per_min = getattr(champion_stats, 'avg_damage_taken_per_min', 500) if champion_specific else getattr(player_stat, 'avg_damage_taken_per_min', 500)
            comparison_text = f"your average with {champion_name}" if champion_specific else "your overall average"
        
        kda_diff = kda - avg_kda
        kda_percent = (kda / avg_kda - 1) * 100 if avg_kda > 0 else 0
        
        if kda > avg_kda * 1.5 and kda > 3:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-chart-line',
                'text': f'Exceptional KDA of {kda:.2f}, {kda_percent:.1f}% above {comparison_text}!'
            })
        elif kda_diff < -1 and champion_games > 2 and champion_specific:
            insights.append({
                'type': 'negative',
                'icon': 'fas fa-arrow-down',
                'text': f'KDA of {kda:.2f} is {-kda_percent:.1f}% below {comparison_text}.'
            })
        
        # Damage insights
        damage = player.get('damage', 0)
        dpm = player.get('dpm', 0)
        game_duration = player.get('game_duration', 1800)
        game_duration_minutes = game_duration / 60
        
        dpm_diff = dpm - avg_dpm
        dpm_percent = (dpm / avg_dpm - 1) * 100 if avg_dpm > 0 else 0
        
        if dpm_percent > 30 and dpm > 150:  # Adjusted threshold for DPM
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-fire',
                'text': f'Dealt {dpm:,} DPM, {dpm_percent:.1f}% higher than {comparison_text}!'
            })
        elif dpm_percent < -25 and champion_games > 2 and champion_specific:
            insights.append({
                'type': 'negative',
                'icon': 'fas fa-fire-extinguisher',
                'text': f'DPM output was {-dpm_percent:.1f}% lower than {comparison_text}.'
            })
        
        # Kill participation insights
        kill_participation = player.get('kill_participation', 0)
        kp_diff = kill_participation - avg_kp
        kp_percent = (kill_participation / avg_kp - 1) * 100 if avg_kp > 0 else 0
        
        if kp_diff > 15:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-handshake',
                'text': f'Your kill participation was {kp_diff:.1f}% higher than {comparison_text}.'
            })
        elif kp_diff < -15 and champion_games > 2 and champion_specific:
            insights.append({
                'type': 'negative',
                'icon': 'fas fa-user-slash',
                'text': f'Lower team involvement than usual with {kill_participation:.1f}% kill participation.'
            })
        
        # Combat Efficiency insights
        damage_dealt = player.get('damage', 0)
        damage_mitigated = player.get('damage_mitigated', 0)
        time_dead_pct = player.get('time_dead_pct', 0)
        
        # Calculate combat efficiency score: (damage dealt + damage mitigated) / (1 + time dead percentage)
        # This rewards high damage output and mitigation while penalizing time spent dead
        combat_efficiency = (damage_dealt + damage_mitigated) / (1 + time_dead_pct/10) if time_dead_pct > 0 else damage_dealt + damage_mitigated
        
        # Normalize to a 0-100 scale for easier understanding
        normalized_efficiency = min(100, combat_efficiency / 1000)
        
        # Get average combat efficiency for comparison using per-minute averages scaled by this game's length
        avg_damage = avg_dpm * game_duration_minutes
        avg_mitigated = avg_damage_taken_per_min * game_duration_minutes
        if gamemode in ['CHERRY', 'ARENA']:
            # Arena: ignore avg_time_dead due to unreliable values
            avg_combat_efficiency = (avg_damage + avg_mitigated)
        else:
            avg_combat_efficiency = (avg_damage + avg_mitigated) / (1 + avg_time_dead/10) if avg_time_dead > 0 else (avg_damage + avg_mitigated)
        avg_normalized_efficiency = min(100, avg_combat_efficiency / 1000)
        
        efficiency_diff = normalized_efficiency - avg_normalized_efficiency
        efficiency_percent = (normalized_efficiency / avg_normalized_efficiency - 1) * 100 if avg_normalized_efficiency > 0 else 0
        
        if gamemode in ['CHERRY', 'ARENA']:
            # Arena insights: prefer DPM/gold/placement cues; avoid efficiency comparisons
            if player.get('placement') and player.get('placement') <= 2:
                insights.append({
                    'type': 'positive',
                    'icon': 'fas fa-trophy',
                    'text': f"Top finish in Arena (place {int(player.get('placement'))}). Great job!"
                })
        elif efficiency_diff > 10:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-fist-raised',
                'text': f'Your combat efficiency was {efficiency_percent:.1f}% higher than {comparison_text}.'
            })
        elif efficiency_diff < -10 and champion_games > 2 and champion_specific:
            insights.append({
                'type': 'negative',
                'icon': 'fas fa-dizzy',
                'text': f'Combat efficiency was lower than {comparison_text}.'
            })
        elif time_dead_pct < 5 and damage_dealt > avg_damage * 1.2:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-fist-raised',
                'text': f'Great combat presence! You dealt high damage while staying alive.'
            })
        elif time_dead_pct > 25 and gamemode not in ['CHERRY', 'ARENA']:
            insights.append({
                'type': 'negative',
                'icon': 'fas fa-skull',
                'text': f'You spent {time_dead_pct:.1f}% of the game dead, reducing your combat impact.'
            })
        
        # CS insights
        cs = player.get('cs', 0)
        cs_per_min = cs / game_duration_minutes if game_duration_minutes > 0 else 0
        cs_diff = cs_per_min - avg_cs_per_min
        cs_percent = (cs_per_min / avg_cs_per_min - 1) * 100 if avg_cs_per_min > 0 else 0
        
        if cs_diff > 1:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-coins',
                'text': f'CS per minute was {cs_percent:.1f}% higher than {comparison_text}.'
            })
        elif cs_diff < -1.5 and champion_games > 2 and champion_specific:
            insights.append({
                'type': 'negative',
                'icon': 'fas fa-coins',
                'text': f'Farming efficiency was lower than {comparison_text}.'
            })
        
        # Gold insights
        gold = player.get('gold', 0)
        gold_per_min = gold / game_duration_minutes if game_duration_minutes > 0 else 0
        gold_diff = gold_per_min - avg_gold_per_min
        gold_percent = (gold_per_min / avg_gold_per_min - 1) * 100 if avg_gold_per_min > 0 else 0
        
        if gold_diff > 50:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-money-bill-wave',
                'text': f'Gold income was {gold_percent:.1f}% per minute higher than {comparison_text}.'
            })
        
        # Personal record insights
        if champion_games > 5 and kda > avg_kda * 1.5 and champion_specific:
            insights.append({
                'type': 'positive',
                'icon': 'fas fa-trophy',
                'text': f'This might be one of your best performances with {champion_name} yet!'
            })
        
        # If we don't have enough insights, add a neutral one
        if len(insights) < 2:
            insights.append({
                'type': 'neutral',
                'icon': 'fas fa-info-circle',
                'text': f'Played {champion_name} with a {kda:.2f} KDA ratio.'
            })
        
        return insights[:3]  # Limit to 3 insights

    async def generate_champion_card(self, champion_name: str, gamemode: str) -> disnake.File:
        """Generate a champion card showing top players' stats for a specific champion"""
        # Get all users from the database
        db_ops = self.bot.get_cog('DatabaseOperations')
        users = await db_ops.get_users(active="TRUE")
        
        # Get stats for each user for this champion
        all_player_stats = []
        for user in users:
            stats = await db_ops.get_player_stats(
                username=user.riot_id_game_name,
                gamemode=gamemode,
                champion=champion_name,
                min_games=1  # Only include players who have played this champion
            )
            if stats and stats[0].champion_games > 0:  # Only include if they have games on this champion
                stats[0].name = user.riot_id_game_name
                stats[0].profile_icon = stats[0].profile_icon  # This is already in the stats
                all_player_stats.append(stats[0])
        
        # Sort by number of games played
        all_player_stats.sort(key=lambda x: x.champion_games, reverse=True)
        
        # Take top 5 by games and then sort them by winrate
        top_5_players = all_player_stats[:5]
        top_5_players.sort(key=lambda x: x.winrate, reverse=True)
        
        # Prepare template data
        theme = self.gamemode_themes.get(gamemode, self.gamemode_themes["CLASSIC"])
        
        # Prepare player data
        players = []
        for stat in top_5_players:  # Using the sorted top 5 players
            winrate = stat.winrate
            kda = stat.average_kda
            
            # Read and encode profile icon
            profile_icon_path = os.path.join(self.assets_path, "gamedata", self.bot.current_game_patch, "img", "profileicon", f"{stat.profile_icon}.png")
            try:
                with open(profile_icon_path, "rb") as image_file:
                    encoded_profile_icon = base64.b64encode(image_file.read()).decode()
            except FileNotFoundError:
                encoded_profile_icon = None
            
            players.append({
                'name': stat.name,
                'games': stat.champion_games,
                'pentas': stat.total_pentas,
                'damage_per_min': f"{stat.avg_damage_per_minute:.0f}",
                'avg_time_dead_pct': f"{self.format_percentage(stat.avg_time_dead_pct)}%",
                'winrate': f"{self.format_percentage(winrate)}",
                'winrate_color': self.get_winrate_color(winrate),
                'kda': f"{kda:.2f}",
                'kda_color': self.get_kda_color(kda, theme),
                'max_killing_spree': stat.max_killing_spree,
                'max_kda': f"{stat.max_kda:.1f}",
                'total_first_bloods': stat.total_first_bloods,
                'total_objectives': stat.total_objectives,
                'avg_kill_participation': f"{self.format_percentage(stat.avg_kill_participation)}",
                'avg_gold_per_min': f"{stat.avg_gold_per_min:.0f}",
                'avg_damage_taken_per_min': f"{stat.avg_damage_taken_per_min:.0f}",
                'profile_icon': encoded_profile_icon
            })
            
        if not players:
            raise ValueError(f"No players found with games on {champion_name} in {gamemode} mode")
            
        # Read and encode champion images
        champion_image = self.load_champion_image(champion_name, "tiles")
        champion_loading = self.load_champion_image(champion_name, "loading")
        
        # Read and encode background image
        bg_image_path = os.path.join(self.assets_path, "images", f"{gamemode}.png")
        try:
            with open(bg_image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode()
        except FileNotFoundError:
            encoded_image = None
        
        # Calculate aggregate stats
        total_games = sum(stat.champion_games for stat in top_5_players)
        total_pentas = sum(stat.total_pentas for stat in top_5_players)
        # Calculate weighted average winrate and format to one decimal place
        avg_winrate = sum(stat.winrate * stat.champion_games for stat in top_5_players) / total_games if total_games > 0 else 0
        avg_winrate = round(avg_winrate, 1)
        
        # Render template
        template = self.jinja_env.get_template('champion_card.html')
        html_content = template.render(
            champion_name=champion_name,
            gamemode=translate(gamemode),
            theme_color=theme['primary'],
            total_games=total_games,
            total_pentas=total_pentas,
            total_winrate=avg_winrate,
            total_winrate_color=self.get_winrate_color(avg_winrate),
            players=players,
            background_image=encoded_image,
            champion_image=champion_image,
            champion_loading=champion_loading
        )
        
        # Use playwright to render HTML to image
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 600, 'height': 100})
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            
            # Wait for background image and fonts to load
            await page.wait_for_timeout(500)
            
            # Set content and wait for it to load
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(500)

            # Get page dimensions
            dimensions = await page.evaluate('''() => {
                return {
                    width: document.documentElement.scrollWidth,
                    height: document.documentElement.scrollHeight
                }
            }''')
            
            # Set viewport to match content dimensions
            await page.set_viewport_size(dimensions)

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
            return disnake.File(fp=output, filename='champion_card.png')

    async def generate_leaderboard_card(self, guild_name: str, gamemode: str, limit: int, min_games: int, kda_data: list, winrate_data: list, dpm_data: list) -> disnake.File:
        """Generate a leaderboard card as an image file."""

        # 1. Get theme and background
        # Use the raw gamemode key for theme/image lookup
        gamemode_png_name = translate(gamemode)
        theme = self.gamemode_themes.get(gamemode, self.gamemode_themes["CLASSIC"])
        bg_image_path = os.path.join(self.assets_path, "images", f"{gamemode_png_name}.png")
        try:
            with open(bg_image_path, "rb") as image_file:
                background_image = base64.b64encode(image_file.read()).decode()
        except FileNotFoundError:
            print(f"Warning: Could not find background image for gamemode {gamemode}")
            background_image = None # Template can handle None

        # 2. Find latest patch for profile icons
        gamedata_path = os.path.join(self.assets_path, "gamedata")
        patch_folders = [d for d in os.listdir(gamedata_path) if os.path.isdir(os.path.join(gamedata_path, d)) and d not in ['img']]
        # Sort folders numerically/lexicographically if possible, assuming version format like X.Y.Z
        try:
            # Attempt to sort by version numbers
             patch_folders.sort(key=lambda v: [int(x) for x in v.split('.')], reverse=True)
             latest_patch = patch_folders[0] if patch_folders else "15.1.1"
        except ValueError:
             # Fallback to simple sort if version format is unexpected
             latest_patch = sorted(patch_folders, reverse=False)[0] if patch_folders else "15.1.1"
             
        print(f"Using latest patch folder for icons: {latest_patch}")
        profile_icon_base_path = os.path.join(self.assets_path, "gamedata", latest_patch, "img", "profileicon")

        # Helper function to load icon (modified to handle potential errors)
        def _load_icon(icon_id):
            if icon_id is None: # Handle cases where icon_id might be missing
                icon_id = 0 # Default to 0
                
            profile_icon_path = os.path.join(profile_icon_base_path, f"{icon_id}.png")
            default_icon_path = os.path.join(profile_icon_base_path, "0.png")
            
            try:
                target_path = profile_icon_path if os.path.exists(profile_icon_path) else default_icon_path
                if os.path.exists(target_path):
                     with open(target_path, "rb") as img_file:
                         return base64.b64encode(img_file.read()).decode('utf-8')
                else:
                     print(f"Warning: Profile icon {icon_id} and default icon 0 not found in {profile_icon_base_path}")
                     return "" # Return empty string if neither found
            except Exception as e:
                print(f"Error loading profile icon {icon_id} (fallback 0): {e}")
                return "" # Return empty string on error

        # 3. Process leaderboard data (add icons and colors)
        processed_kda = []
        if kda_data:
            # Data is a list of tuples: (name, kda, games, profile_icon_id)
            for player_tuple in kda_data:
                name, kda, total_games, profile_icon_id = player_tuple
                player_dict = {
                    'name': name,
                    'kda': kda,
                    'total_games': total_games,
                    'profile_icon': _load_icon(profile_icon_id),
                    'kda_color': self.get_kda_color(kda, theme)
                }
                processed_kda.append(player_dict)

        processed_winrate = []
        if winrate_data:
            # Data is a list of tuples: (name, winrate, games, profile_icon_id)
            for player_tuple in winrate_data:
                name, raw_winrate, total_games, profile_icon_id = player_tuple
                player_dict = {
                    'name': name,
                    'winrate': self.format_percentage(raw_winrate),
                    'total_games': total_games,
                    'profile_icon': _load_icon(profile_icon_id),
                    'winrate_color': self.get_winrate_color(raw_winrate)
                }
                processed_winrate.append(player_dict)

        processed_dpm = []
        if dpm_data:
            # Data is a list of tuples: (name, dpm, games, profile_icon_id)
            for player_tuple in dpm_data:
                name, dpm, total_games, profile_icon_id = player_tuple
                player_dict = {
                    'name': name,
                    'dpm': dpm,
                    'total_games': total_games,
                    'profile_icon': _load_icon(profile_icon_id)
                }
                processed_dpm.append(player_dict)

        # 4. Render template
        template = self.jinja_env.get_template('leaderboard_card.html')
        html_content = template.render(
            guild_name=guild_name,
            gamemode=translate(gamemode),
            limit=limit,
            min_games=min_games,
            theme=theme,
            background_image=background_image,
            kda_data=processed_kda,
            winrate_data=processed_winrate,
            dpm_data=processed_dpm
        )

        # 5. Use playwright to render HTML to image
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # Increase initial viewport height significantly
            page = await browser.new_page(viewport={'width': 1200, 'height': 850}) 
            await page.set_content(html_content)

            # Wait for network idle and a short timeout for rendering stability
            try:
                await page.wait_for_load_state('networkidle', timeout=10000) 
                await page.wait_for_timeout(500) # Extra buffer for rendering
            except Exception as e:
                 print(f"Playwright timeout or error during load state: {e}")
                 await browser.close()
                 raise RuntimeError(f"Playwright failed during page load: {e}")

            # Find the main card element
            element_handle = await page.query_selector('.card')
            if not element_handle:
                 print("DEBUG: .card element NOT found in template.") # DEBUG
                 await browser.close()
                 raise RuntimeError("Could not find .card element for screenshotting.")
            else:
                print("DEBUG: .card element found. Attempting element screenshot...") # DEBUG
                # Screenshot the element directly
                try:
                    image_bytes = await page.screenshot(type='png')
                    print("DEBUG: Element screenshot successful.") # DEBUG
                except Exception as e:
                    print(f"DEBUG: Error taking element screenshot: {e}. Falling back to viewport screenshot.") # DEBUG
                    # Fallback to viewport screenshot if element screenshot fails
                    image_bytes = await page.screenshot(type='png')

            await browser.close()

        # 6. Save to BytesIO and return Disnake File
        if not image_bytes:
             raise RuntimeError("Failed to generate leaderboard image bytes.")
             
        output = io.BytesIO(image_bytes)
        output.seek(0)
        return disnake.File(fp=output, filename='leaderboard_card.png')

def setup(bot):
    bot.add_cog(CardGenerator(bot)) 