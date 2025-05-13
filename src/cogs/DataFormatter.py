from datetime import datetime
import disnake
from disnake.ext import commands
from typing import List, Tuple, Optional
from ..models.models import PlayerStats, PlayerFriendStats, User, UserStats

# Define the steps for the LoL update process
UPDATE_STEPS = [
    "Fetching latest LoL version",
    "Cleaning old game data directory",
    "Downloading game data archive (.tgz)",
    "Extracting game data archive",
    "Cleaning up downloaded archive",
    "Fetching latest champion data (JSON)",
    "Processing champion data",
    "Inserting champion data into database",
    "Update Complete"
]

class DataFormatter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.UPDATE_STEPS = UPDATE_STEPS # Store steps if needed instance-wise, or keep module-level

    async def format_get_player_stats(self, data: List[PlayerStats]) -> str:
        if not data:
            return "No data available."
            
        # Get overall stats from the first row
        first_stat = data[0]
        total_games = first_stat.total_games_overall
        unique_champs = first_stat.unique_champions_played
        unique_ratio = first_stat.unique_champ_ratio
        oldest_game = first_stat.oldest_game
        total_hours = first_stat.total_hours_played
        total_pentas = first_stat.total_pentas_overall

        # Create the stats table with wider columns
        table = "```\nChampion Stats:\n"
        table += f"{'Champion':<15} {'Games':<8} {'Win%':<8} {'DPM':<8} {'KDA':<5} {'x4':<2} {'x5':<2}\n"
        table += "-" * 55 + "\n"  # Increased separator length
        
        for stat in data:
            champ = stat.champion_name[:14] if "Strawberry_" not in stat.champion_name else stat.champion_name.replace("Strawberry_", "")[:14]
            games = str(stat.champion_games)
            winrate = f"{stat.winrate:.1f}"
            dpm = str(int(stat.avg_damage_per_minute))
            kda = f"{stat.average_kda:.2f}"
            quadras = str(stat.total_quadras)
            pentas = str(stat.total_pentas)
            
            table += f"{champ:<15} {games:<8} {winrate:<8} {dpm:<8} {kda:<5} {quadras:2} {pentas:2}\n"
        
        table += "```"

        # Create overall stats description
        description = f"**Overall Stats in the last ~1 or 2 years:**\n"
        description += f"• Total Games: {total_games}\n"
        description += f"• Unique Champions: {unique_champs}\n"
        description += f"• Champion Variety: {unique_ratio:.1f}%\n"
        description += f"• Total Hours: {int(total_hours)}\n"
        description += f"• Total Pentas: {total_pentas}\n"
        description += f"• Latest Game Fetched: {oldest_game}\n\n"
        description += table

        return description
    
    async def format_get_all_players_stats(self, data: List[UserStats]) -> str:
        # Create the stats table
        table = "```\nPlayer Time Stats:\n"
        table += f"{'Player':<15} {'Hours':<6} {'2025h':<6} {'Games':<5} {' WR':<4} {'Avg(m)':<8} {'Pentas':<5}\n"
        table += "-" * 55 + "\n"
        
        for user in data:
            name = user.riot_id_game_name[:14]
            total_hours = f"{user.total_hours_played:.1f}"
            hours_2024 = f"{user.total_hours_2024:.1f}"
            games = str(user.games_played)
            avg_minutes = f"{user.avg_minutes_per_game:.1f}"
            pentas = str(user.total_pentas)
            winrate = f"{user.winrate:.1f}"
            
            table += f"{name:<15} {total_hours:<6} {hours_2024:<6} {games:<5} {winrate:<4} {avg_minutes:<8} {pentas:5}\n"
        
        table += "```"

        # Create description with the table
        description = f"**League of Legends Time Stats**\n"
        description += table

        return description
    
    async def format_player_vs_player(self, data_user1: List[PlayerStats], data_user2: List[PlayerStats], username1: str, username2: str, champion: str = None) -> str:
        if not data_user1 or not data_user2:
            return "No data available for one or both players."

        # Get overall stats from the first row for both players
        first_stat1 = data_user1[0]
        first_stat2 = data_user2[0]
        total_games1, total_hours1 = first_stat1.total_games_overall, first_stat1.total_hours_played
        total_games2, total_hours2 = first_stat2.total_games_overall, first_stat2.total_hours_played

        # Create the table header
        table = "```\n"
        table += f"{'Stat':<20} {username1:<15} {username2:<15}\n"
        table += "-" * 50 + "\n"

        if champion:
            # Find champion-specific stats for both players
            champ_stats1 = next((stat for stat in data_user1 if stat.champion_name == champion), None)
            champ_stats2 = next((stat for stat in data_user2 if stat.champion_name == champion), None)

            if champ_stats1 or champ_stats2:
                # Use champion-specific stats
                games1 = champ_stats1.champion_games if champ_stats1 else 0
                games2 = champ_stats2.champion_games if champ_stats2 else 0
                winrate1 = champ_stats1.winrate if champ_stats1 else 0
                winrate2 = champ_stats2.winrate if champ_stats2 else 0
                dpm1 = champ_stats1.avg_damage_per_minute if champ_stats1 else 0
                dpm2 = champ_stats2.avg_damage_per_minute if champ_stats2 else 0
                kda1 = champ_stats1.average_kda if champ_stats1 else 0
                kda2 = champ_stats2.average_kda if champ_stats2 else 0
                triples1 = champ_stats1.total_triples if champ_stats1 else 0
                triples2 = champ_stats2.total_triples if champ_stats2 else 0
                quadras1 = champ_stats1.total_quadras if champ_stats1 else 0
                quadras2 = champ_stats2.total_quadras if champ_stats2 else 0
                pentas1 = champ_stats1.total_pentas if champ_stats1 else 0
                pentas2 = champ_stats2.total_pentas if champ_stats2 else 0

                table += f"Champion Stats for {champion}:\n"
        else:
            # Use overall stats
            games1, games2 = total_games1, total_games2
            winrate1 = first_stat1.total_winrate
            winrate2 = first_stat2.total_winrate
            # Calculate weighted averages for DPM and KDA
            dpm1 = sum(stat.avg_damage_per_minute * stat.champion_games for stat in data_user1) / total_games1 if total_games1 > 0 else 0
            dpm2 = sum(stat.avg_damage_per_minute * stat.champion_games for stat in data_user2) / total_games2 if total_games2 > 0 else 0
            kda1 = sum(stat.average_kda * stat.champion_games for stat in data_user1) / total_games1 if total_games1 > 0 else 0
            kda2 = sum(stat.average_kda * stat.champion_games for stat in data_user2) / total_games2 if total_games2 > 0 else 0
            triples1 = sum(stat.total_triples for stat in data_user1)
            triples2 = sum(stat.total_triples for stat in data_user2)
            quadras1 = sum(stat.total_quadras for stat in data_user1)
            quadras2 = sum(stat.total_quadras for stat in data_user2)
            pentas1 = sum(stat.total_pentas for stat in data_user1)
            pentas2 = sum(stat.total_pentas for stat in data_user2)

            table += f"Overall Stats:\n"

        # Add comparison stats
        table += f"{'Games':<20} {games1:<15} {games2:<15}\n"
        table += f"{'Total Hours':<20} {total_hours1:<15.1f} {total_hours2:<15.1f}\n"
        table += f"{'Win Rate %':<20} {winrate1:<15.1f} {winrate2:<15.1f}\n"
        table += f"{'DPM':<20} {int(dpm1):<15} {int(dpm2):<15}\n"
        table += f"{'KDA':<20} {kda1:<15.2f} {kda2:<15.2f}\n"
        table += f"{'Triple Kills':<20} {triples1:<15} {triples2:<15}\n"
        table += f"{'Quadra Kills':<20} {quadras1:<15} {quadras2:<15}\n"
        table += f"{'Penta Kills':<20} {pentas1:<15} {pentas2:<15}\n"

        table += "```"
        return table
    
    async def format_player_friends_data(self, data: List[PlayerFriendStats], username: str) -> str:
        # Create the stats table
        table = "```\nDuo Queue Stats:\n"
        table += f"{'Friend':<15} {'Games':<8} {'Wins':<8} {'Win%':<8}\n"
        table += "-" * 42 + "\n"
        
        total_games = 0
        weighted_winrate = 0
        
        for friend_stat in data:
            name = friend_stat.teammate_name[:14]
            games = str(friend_stat.games_together)
            wins = str(friend_stat.wins_together)
            winrate = f"{friend_stat.win_rate:.1f}"
            
            total_games += friend_stat.games_together
            weighted_winrate += friend_stat.games_together * friend_stat.win_rate
            
            table += f"{name:<15} {games:<8} {wins:<8} {winrate:<8}\n"
        
        avg_winrate = weighted_winrate / total_games if total_games > 0 else 0
        table += "-" * 42 + "\n"
        table += f"Average Win Rate: {avg_winrate:.1f}%\n"
        table += "```"

        # Create description with the table
        description = f"**Showing duo stats for {username}**\n"
        description += f"Total duo games analyzed: {total_games}\n\n"
        description += table

        return description

    async def format_active_players(self, active_players: List[dict]) -> str:
        # Sort players by winrate (handling N/A cases)
        def get_winrate_value(player):
            # Convert "N/A" to -1 for sorting purposes
            wr = player['winrate']
            return -1 if wr == "N/A" else float(wr)
        
        active_players.sort(key=get_winrate_value, reverse=True)
        
        table = "```"
        table += f"{'Player':<15} {'Champion':<10} {'Mode':<5} {'Games':<6} {'Win%':<6} {'KDA':<5} {'x5':<3}\n"
        table += "-" * 56 + "\n"
        
        for player in active_players:
            name = player['name'][:14]
            champ = player['champion'][:10]
            mode = player['gameMode'][:5]
            games = str(player['games'])
            winrate = player['winrate']
            kda = player['kda']
            pentas = str(player['pentas'])
            
            table += f"{name:<15} {champ:<10} {mode:<5} {games:<6} {winrate:<6} {kda:<5} {pentas:<3}\n"
        
        table += "```"
        return table

    async def format_update_database_scan_message(self, users: List[User]) -> dict:
        table = "```\n"  # Start code block for better formatting
        for user in users:
            table += f"• {user.riot_id_game_name}\n"
        table += "```"  # End code block
        return {
            "title": "🎮 Looking for New Matches",
            "description": f"Scanning for new matches from:\n{table}"
        }

    async def format_update_database_progress_message(self, game_name: str, match_count: int) -> dict:
        return {
            "title": "🎮 Updating Database",
            "description": f"Adding {match_count} matches to the database found for {game_name}"
        }

    async def format_leaderboard_kda(self, data: List[Tuple[str, float, int]]) -> str:
        """Formats KDA leaderboard data into a string for embeds."""
        if not data:
            return "No data to display."
        
        description = ""
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, (name, kda, games) in enumerate(data, start=1):
            rank_icon = rank_icons.get(i, f"**{i}.**")
            safe_name = disnake.utils.escape_markdown(name)
            description += f"{rank_icon} `{safe_name}` - KDA: **{kda:.2f}** ({games} games)\n"
        return description

    async def format_leaderboard_winrate(self, data: List[Tuple[str, float, int]]) -> str:
        """Formats Win Rate leaderboard data into a string for embeds."""
        if not data:
            return "No data to display."
        
        description = ""
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, (name, winrate, games) in enumerate(data, start=1):
            rank_icon = rank_icons.get(i, f"**{i}.**")
            safe_name = disnake.utils.escape_markdown(name)
            description += f"{rank_icon} `{safe_name}` - Win Rate: **{winrate:.1f}%** ({games} games)\n"
        return description

    async def format_leaderboard_pentakills(self, data: List[Tuple[str, int, int]]) -> str:
        """Formats Pentakills leaderboard data into a string for embeds."""
        if not data:
            return "No data to display."
        
        description = ""
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, (name, pentas, games) in enumerate(data, start=1):
            rank_icon = rank_icons.get(i, f"**{i}.**")
            safe_name = disnake.utils.escape_markdown(name)
            pentas_text = "Pentakill" if pentas == 1 else "Pentakills"
            description += f"{rank_icon} `{safe_name}` - **{pentas}** {pentas_text} ({games} games)\n"
        return description

    async def format_apply_update_steps(self, current_index: int, error: Optional[str] = None) -> str:
        """Formats the list of steps for the apply_lol_update command, marking the current one."""
        lines = []
        steps = self.UPDATE_STEPS 
        final_step_index = len(steps) - 1
        
        for i, step in enumerate(steps):
            # Determine the prefix based on the current step index and whether it's the final step
            if error and i == current_index:
                prefix = "❌ " # Error occurred at this step
            elif not error and i == final_step_index and current_index == final_step_index:
                 prefix = "✅ " # Final step completed successfully
            elif i == current_index:
                prefix = "--> " # Current step in progress
            elif i < current_index:
                prefix = "✅ " # Step completed successfully
            else:
                prefix = "•   " # Pending step
            lines.append(f"{prefix}{step}")
        
        formatted_steps = "\n".join(lines)
        if error:
            formatted_steps += f"\n\n**Error:** {error}"
        return formatted_steps

def setup(bot):
    bot.add_cog(DataFormatter(bot))


