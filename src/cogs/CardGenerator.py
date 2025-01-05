import disnake
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import os
from datetime import datetime
import math

class CardGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_path = "/app/src/assets/fonts"
        self.assets_path = "/app/src/assets"
        
        # Base dimensions that will be scaled
        self.base_width = 800
        self.base_height = 700
        
        # Define all dimensions as percentages of base dimensions
        self.dimensions = {
            'padding': 0.042375,           # 35/800
            'inner_padding': 0.04,     # 25/800
            'title_y_offset': 0.06,     # 50/600
            'stats_y_offset': 0.06,     # 100/600
            'stats_height': 0.1667,       # 100/600
            'champs_y_offset': 0.04,     # 45/600
            'table_y_offset': 0.04,     # 40/600
            'row_height': 0.0417,         # 25/600
            'header_offset': 0.04,
            'header_spacing': 0.05,       # 30/600
        }
        
        # Font sizes as percentages of base width
        self.font_sizes = {
            'title': 0.05,      # 40/800
            'header': 0.035,    # 28/800
            'text': 0.0275,     # 22/800
            'number': 0.05      # 40/800
        }
        
        # Define gamemode color themes
        self.gamemode_themes = {
            "ARAM": {
                "primary": (89, 155, 201),     # Ice blue
                "secondary": (48, 79, 124),
                "overlay_start": (32, 45, 58, 230),
                "overlay_end": (22, 31, 40, 250)
            },
            "CLASSIC": {
                "primary": (86, 171, 47),      # Forest green
                "secondary": (44, 88, 24),
                "overlay_start": (35, 46, 32, 230),
                "overlay_end": (24, 31, 22, 250)
            },
            "STRAWBERRY": {
                "primary": (255, 105, 180),    # Hot pink
                "secondary": (199, 21, 133),
                "overlay_start": (58, 32, 45, 230),
                "overlay_end": (40, 22, 31, 250)
            },
            "NEXUSBLITZ": {
                "primary": (255, 215, 0),      # Gold
                "secondary": (218, 165, 32),
                "overlay_start": (58, 49, 32, 230),
                "overlay_end": (40, 34, 22, 250)
            },
            "CHERRY": {
                "primary": (255, 99, 71),      # Tomato red
                "secondary": (205, 92, 92),
                "overlay_start": (58, 35, 32, 230),
                "overlay_end": (40, 24, 22, 250)
            },
            "ULTBOOK": {
                "primary": (147, 112, 219),    # Purple
                "secondary": (75, 0, 130),
                "overlay_start": (45, 32, 58, 230),
                "overlay_end": (31, 22, 40, 250)
            },
            "URF": {
                "primary": (255, 223, 0),      # Bright gold
                "secondary": (255, 165, 0),
                "overlay_start": (58, 54, 32, 230),
                "overlay_end": (40, 37, 22, 250)
            }
        }
            
    async def generate_player_card(self, summoner_name: str, gamemode: str, data: list, scale_factor: float = 1.0) -> disnake.File:
        """Generate a player card as an image file with optional scaling"""
        card = await self.create_player_card(summoner_name, gamemode, data, scale_factor)
        with io.BytesIO() as image_binary:
            card.save(image_binary, 'PNG')
            image_binary.seek(0)
            return disnake.File(fp=image_binary, filename='player_card.png')
            
    def create_rounded_rectangle(self, draw, coords, radius, fill, outline=None):
        """Draw a rounded rectangle"""
        x1, y1, x2, y2 = coords
        diameter = radius * 2
        
        # Draw the corners
        draw.ellipse([x1, y1, x1 + diameter, y1 + diameter], fill=fill, outline=outline)
        draw.ellipse([x2 - diameter, y1, x2, y1 + diameter], fill=fill, outline=outline)
        draw.ellipse([x1, y2 - diameter, x1 + diameter, y2], fill=fill, outline=outline)
        draw.ellipse([x2 - diameter, y2 - diameter, x2, y2], fill=fill, outline=outline)
        
        # Draw the middle rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=None)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=None)

    def get_winrate_color(self, winrate):
        """Return a color based on winrate"""
        if winrate >= 60:
            return (52, 211, 153)  # Green
        elif winrate >= 50:
            return (96, 165, 250)  # Blue
        else:
            return (248, 113, 113)  # Red

    def create_gradient_overlay(self, width, height, start_color, end_color):
        """Create a semi-transparent gradient overlay"""
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for y in range(height):
            r = int(start_color[0] + (end_color[0] - start_color[0]) * (y / height))
            g = int(start_color[1] + (end_color[1] - start_color[1]) * (y / height))
            b = int(start_color[2] + (end_color[2] - start_color[2]) * (y / height))
            a = int(start_color[3] + (end_color[3] - start_color[3]) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b, a))
            
        return overlay

    def prepare_background(self, width, height, gamemode, theme):
        """Prepare the background with gamemode image and overlay"""
        try:
            # Load background image
            bg_path = os.path.join(self.assets_path, "images", f"{gamemode}.png")
            background = Image.open(bg_path).convert('RGBA')
            
            # First, ensure the image is large enough
            scale = max(width / background.width, height / background.height)
            if scale > 1:
                new_width = int(background.width * scale)
                new_height = int(background.height * scale)
                background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Then center and crop
            bg_ratio = background.width / background.height
            card_ratio = width / height
            
            if bg_ratio > card_ratio:  # Image is wider than card
                new_height = height
                new_width = int(height * bg_ratio)
                offset_x = (new_width - width) // 2
                offset_y = 0
            else:  # Image is taller than card
                new_width = width
                new_height = int(width / bg_ratio)
                offset_x = 0
                offset_y = (new_height - height) // 2
            
            # Resize and crop to fit
            background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)
            background = background.crop((offset_x, offset_y, offset_x + width, offset_y + height))
            
            # Convert to RGB for final output
            return background.convert('RGB')
            
        except Exception as e:
            print(f"Error loading background image: {e}")
            # Fallback to gradient background
            background = Image.new('RGB', (width, height), theme["overlay_start"][:3])
            return background

    async def create_player_card(self, summoner_name, gamemode, data, scale_factor: float = 1.0):
        # Calculate actual dimensions based on scale factor
        width = int(self.base_width * scale_factor)
        height = int(self.base_height * scale_factor)
        
        # Calculate scaled dimensions
        padding = int(width * self.dimensions['padding'])
        inner_padding = int(width * self.dimensions['inner_padding'])
        
        theme = self.gamemode_themes.get(gamemode, self.gamemode_themes["CLASSIC"])
        
        # Create background with theme colors
        card = self.prepare_background(width, height, gamemode, theme)
        draw = ImageDraw.Draw(card)
        
        try:
            # Scale font sizes based on width
            title_font = ImageFont.truetype(os.path.join(self.font_path, 'BeaufortforLOL-Bold.ttf'), 
                                          int(width * self.font_sizes['title']))
            header_font = ImageFont.truetype(os.path.join(self.font_path, 'BeaufortforLOL-Bold.ttf'), 
                                           int(width * self.font_sizes['header']))
            text_font = ImageFont.truetype(os.path.join(self.font_path, 'Spiegel-Regular.ttf'), 
                                         int(width * self.font_sizes['text']))
            number_font = ImageFont.truetype(os.path.join(self.font_path, 'Spiegel-Regular.ttf'), 
                                           int(width * self.font_sizes['number']))
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            number_font = ImageFont.load_default()

        # Calculate layout dimensions
        card_width = width - (padding * 2)
        
        # Draw main container
        self.create_rounded_rectangle(
            draw,
            [padding, padding, width - padding, height - padding],
            int(15 * scale_factor),  # Scale the corner radius
            (30, 35, 40, 200)
        )
        
        # Draw title
        title_y = padding + int(height * self.dimensions['title_y_offset'])
        draw.text(
            (width/2, title_y),
            f"{summoner_name}'s {gamemode} Stats",
            font=title_font,
            fill=theme["primary"],
            anchor="mm"
        )
        
        # Get stats
        total_games = data[0][5]
        total_hours = data[0][9]
        total_pentas = data[0][13]
        
        # Draw stat boxes
        stats_y = title_y + int(height * self.dimensions['stats_y_offset'])
        stats_height = int(height * self.dimensions['stats_height'])
        
        # Calculate box widths
        total_padding = inner_padding * 2
        usable_width = card_width - total_padding
        box_width = (usable_width - total_padding) // 3
        
        stats_data = [
            [str(total_games), "Games"],
            [f"{total_hours:.1f}h", "Played"],
            [str(total_pentas), "Pentas"]
        ]
        
        start_x = padding + (card_width - (box_width * 3 + total_padding)) // 2
        
        for i, (value, label) in enumerate(stats_data):
            x = start_x + (box_width + inner_padding) * i
            
            self.create_rounded_rectangle(
                draw,
                [x, stats_y, x + box_width, stats_y + stats_height],
                int(10 * scale_factor),
                (40, 45, 50)
            )
            
            value_y = stats_y + (stats_height // 2) - int(10 * scale_factor)
            draw.text(
                (x + box_width//2, value_y),
                value,
                align="center",
                font=number_font,
                fill=theme["primary"],
                anchor="mm"
            )
            
            label_y = stats_y + (stats_height // 2) + int(20 * scale_factor)
            draw.text(
                (x + box_width//2, label_y),
                label,
                font=text_font,
                align="center",
                fill=(180, 180, 180),
                anchor="mm"
            )
        
        # Draw champions section
        champs_y = stats_y + stats_height + int(height * self.dimensions['champs_y_offset'])
        
        section_title_x = padding + inner_padding
        draw.text(
            (section_title_x, champs_y),
            "Top Champions",
            font=header_font,
            fill=theme["primary"],
            anchor="lm"
        )
        
        # Draw champion stats container
        table_y = champs_y + int(height * self.dimensions['table_y_offset'])
        table_height = height - table_y - padding - (inner_padding)
        
        table_container_x = padding + (inner_padding)
        table_container_width = width - (padding * 2) - (inner_padding * 2)
        
        self.create_rounded_rectangle(
            draw,
            [table_container_x, table_y,
             table_container_x + table_container_width, table_y + table_height],
            int(10 * scale_factor),
            (40, 45, 50)
        )
        
        # Draw table headers
        headers = ["Champion", "Games", "Win%", "KDA"]
        header_widths = [0.38, 0.17, 0.25, 0.20]
        table_content_x = table_container_x + inner_padding

        header_y = table_y + int(height * self.dimensions['header_offset'])
        content_width = table_container_width - (inner_padding * 2)
        
        current_x = table_content_x
        for header, width_prop in zip(headers, header_widths):
            col_width = int(content_width * width_prop)
            draw.text(
                (current_x, header_y),
                header,
                font=text_font,
                fill=(140, 140, 140),
                anchor="lm"
            )
            current_x += col_width
        
        # Draw champion rows
        row_height = int(height * self.dimensions['row_height'])
        start_y = header_y + int(height * self.dimensions['header_spacing'])
        
        for i, row in enumerate(data[:10]):
            current_x = table_content_x
            y = start_y + (row_height * i)
            
            # Champion name
            col_width = int(content_width * header_widths[0])
            draw.text((current_x, y), row[0][:15], font=text_font, fill=(255, 255, 255), anchor="lm")
            current_x += col_width
            
            # Games
            col_width = int(content_width * header_widths[1])
            draw.text((current_x, y), str(row[1]), font=text_font, fill=(200, 200, 200), anchor="lm")
            current_x += col_width
            
            # Winrate
            col_width = int(content_width * header_widths[2])
            winrate = row[2]
            winrate_color = self.get_winrate_color(winrate)
            draw.text((current_x, y), f"{winrate:.1f}%", font=text_font, fill=winrate_color, anchor="lm")
            current_x += col_width
            
            # KDA
            kda = row[4]
            kda_color = theme["primary"] if kda >= 4 else (200, 200, 200)
            draw.text((current_x, y), f"{kda:.2f}", font=text_font, fill=kda_color, anchor="lm")
        
        return card

def setup(bot):
    bot.add_cog(CardGenerator(bot)) 