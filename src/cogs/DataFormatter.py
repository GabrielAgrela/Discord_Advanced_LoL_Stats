from datetime import datetime
from disnake.ext import commands

class DataFormatter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def format_get_player_stats(self, data):
        # Get overall stats from the first row
        total_games = data[0][5]
        unique_champs = data[0][6]
        unique_ratio = data[0][7]
        oldest_game = datetime.strptime(data[0][8], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
        total_hours = data[0][9]
        total_pentas = data[0][13]

        # Create the stats table with wider columns
        table = "```\nChampion Stats:\n"
        table += f"{'Champion':<15} {'Games':<8} {'Win%':<8} {'DPM':<8} {'KDA':<5} {'x4':<2} {'x5':<2}\n"
        table += "-" * 55 + "\n"  # Increased separator length
        
        for row in data:
            champ = row[0][:14] if "Strawberry_" not in row[0] else row[0].replace("Strawberry_", "")[:14]
            games = str(row[1])
            winrate = f"{row[2]:.1f}"
            dpm = str(int(row[3]))
            kda = f"{row[4]:.2f}"
            quadras = str(row[11])
            pentas = str(row[12])

            
            table += f"{champ:<15} {games:<8} {winrate:<8} {dpm:<8} {kda:<5} {quadras:2} {pentas:2}\n"
        
        table += "```"

        # Create overall stats description
        description = f"**Overall Stats in the last ~1 or 2 years:**\n"
        description += f"• Total Games: {total_games}\n"
        description += f"• Unique Champions: {unique_champs}\n"
        description += f"• Champion Variety: {unique_ratio:.1f}%\n"
        description += f"• Total Hours: {total_hours}\n"
        description += f"• Total Pentas: {total_pentas}\n"
        description += f"• Latest Game Fetched: {oldest_game}\n\n"
        description += table

        return description
    
    async def format_get_all_players_stats(self, data):
         # Create the stats table
        table = "```\nPlayer Time Stats:\n"
        table += f"{'Player':<15} {'Hours':<6} {'2024h':<6} {'Games':<5} {' WR':<4} {'Avg(m)':<8} {'Pentas':<5}\n"
        table += "-" * 55 + "\n"
        
        for row in data:
            name = f"{row[0]}"[:14] 
            total_hours = f"{row[2]:.1f}"
            hours_2024 = f"{row[3]:.1f}"
            games = str(row[4])
            avg_minutes = f"{row[5]:.1f}"
            pentas = str(row[7])  # New field for pentakills
            winrate = f"{row[8]:.1f}"
            table += f"{name:<15} {total_hours:<6} {hours_2024:<6} {games:<5} {winrate:<4} {avg_minutes:<8} {pentas:5}\n"
        
        table += "```"

        # Create description with the table
        description = f"**League of Legends Time Stats**\n"
        description += table

        return description
    
    async def format_player_vs_player(self, data_user1, data_user2, username1, username2):
        # Get overall stats from the first row for both players
        total_games1, total_hours1 = data_user1[0][5], data_user1[0][9]
        total_games2, total_hours2 = data_user2[0][5], data_user2[0][9]

        # Create dictionaries of champion stats
        champ_dict1 = {row[0]: row[1:] for row in data_user1}
        champ_dict2 = {row[0]: row[1:] for row in data_user2}
        all_champs = sorted(set(list(champ_dict1.keys()) + list(champ_dict2.keys())))

        # Create the table header
        table = "```\n"
        table += f"{'Stat':<20} {username1:<15} {username2:<15}\n"
        table += "-" * 50 + "\n"

        # Add champion stats
        for champ in all_champs:            
            # Get stats for both players
            stats1 = champ_dict1.get(champ, [0] * 13)  # Updated to match new column count
            stats2 = champ_dict2.get(champ, [0] * 13)  # Updated to match new column count
            
            if stats1[0] > 0 or stats2[0] > 0:  # Only show if either player has games
                table += f"{'Games':<20} {stats1[0]:<15} {stats2[0]:<15}\n"
                table += f"{'Total Hours':<20} {total_hours1:<15.1f} {total_hours2:<15.1f}\n"
                table += f"{'Win Rate %':<20} {stats1[1]:<15.1f} {stats2[1]:<15.1f}\n"
                table += f"{'DPM':<20} {int(stats1[2]):<15} {int(stats2[2]):<15}\n"
                table += f"{'KDA':<20} {stats1[3]:<15.2f} {stats2[3]:<15.2f}\n"
                table += f"{'Triple Kills':<20} {stats1[9]:<15} {stats2[9]:<15}\n"
                table += f"{'Quadra Kills':<20} {stats1[10]:<15} {stats2[10]:<15}\n"
                table += f"{'Penta Kills':<20} {stats1[11]:<15} {stats2[11]:<15}\n"
                table += "\n"

        table += "```"

        return table
    
    async def format_player_friends_data(self, data, username):
        # Create the stats table
        table = "```\nDuo Queue Stats:\n"
        table += f"{'Friend':<15} {'Games':<8} {'Wins':<8} {'Win%':<8}\n"
        table += "-" * 42 + "\n"
        
        total_games = 0
        weighted_winrate = 0
        
        for row in data:
            name = row[0][:14]  # Limit name length
            games = str(row[1])
            wins = str(row[2])
            winrate = f"{row[3]:.1f}"
            
            total_games += row[1]
            weighted_winrate += row[1] * row[3]
            
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

    async def format_active_players(self, active_players):
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

    async def format_update_database_scan_message(self, users):
        table = "```\n"  # Start code block for better formatting
        for user in users:
            table += f"• {user[1]}\n"
        table += "```"  # End code block
        return {
            "title": "🎮 Looking for New Matches",
            "description": f"Scanning for new matches from:\n{table}"
        }

    async def format_update_database_progress_message(self, game_name, match_count):
        return {
            "title": "🎮 Updating Database",
            "description": f"Adding {match_count} matches to the database found for {game_name}"
        }

def setup(bot):
    bot.add_cog(DataFormatter(bot))


