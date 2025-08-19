import sqlite3
from datetime import datetime, date, timedelta
from datetime import time as dt_time
import os
from disnake.ext import commands
import aiohttp
from typing import List, Optional, Set, Tuple
from ..models.models import Match, Participant, User, PlayerStats, PlayerFriendStats, UserStats
import time

DB_PATH = "/app/data/lol_stats.db"

class DatabaseOperations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../database/lol_database.db'))

    async def get_player_stats(self, username, gamemode, champion=None, limit=200, sort_by="champion games", sort_order="DESC", min_games=1, year=None) -> List[PlayerStats]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Define valid sort columns and their SQL expressions
        sort_columns = {
            "champion games": "total_games",
            "winrate": "winrate",
            "kda": "average_kda",
            "dpm": "avg_damage_per_minute",
            "time dead": "avg_time_dead_pct",
            "pentas": "total_pentas"
        }

        # Validate and get sort column
        sort_column = sort_columns.get(sort_by, "total_games")
        
        # Validate sort order
        sort_order = "DESC" if sort_order.upper() not in ["ASC", "DESC"] else sort_order.upper()

        # Add year filter to base query if year is provided
        year_filter = f"AND strftime('%Y', m.game_creation) = '{year}'" if year else ""

        base_query = f'''
        WITH base_data AS (
            SELECT p.*, m.game_duration, m.game_creation
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE LOWER(p.riot_id_game_name) = LOWER(?)
            AND LOWER(m.game_mode) = LOWER(?)
            {year_filter}
            {{champion_filter}}
        ),
        champion_stats AS (
            SELECT 
                champion_name,
                COUNT(*) as total_games,
                ROUND(AVG(CASE WHEN wins = 1 THEN 100.0 ELSE 0 END), 1) as winrate,
                ROUND(AVG(total_damage_to_champions / (game_duration / 60.0)), 0) as avg_damage_per_minute,
                ROUND(AVG(CASE 
                    WHEN deaths = 0 THEN kills + assists 
                    ELSE CAST((kills + assists) AS FLOAT) / deaths 
                END), 2) as average_kda,
                ROUND(AVG(CAST(kills AS FLOAT)), 1) as avg_kills,
                ROUND(AVG(CAST(deaths AS FLOAT)), 1) as avg_deaths,
                ROUND(AVG(CAST(assists AS FLOAT)), 1) as avg_assists,
                SUM(triple_kills) as total_triples,
                SUM(quadra_kills) as total_quadras,
                SUM(penta_kills) as total_pentas,
                ROUND(AVG(CAST(total_time_spent_dead AS FLOAT) / game_duration * 100), 1) as avg_time_dead_pct,
                ROUND(AVG(vision_score), 1) as avg_vision_score,
                ROUND(AVG(kill_participation * 100), 1) as avg_kill_participation,
                ROUND(AVG(total_damage_taken / (game_duration / 60.0)), 0) as avg_damage_taken_per_min,
                SUM(CASE WHEN first_blood_kill = 1 OR first_blood_assist = 1 THEN 1 ELSE 0 END) as total_first_bloods,
                SUM(turret_takedowns + inhibitor_takedowns) as total_objectives,
                ROUND(AVG(gold_earned / (game_duration / 60.0)), 0) as avg_gold_per_min,
                ROUND(AVG(total_minions_killed / (game_duration / 60.0)), 1) as avg_cs_per_min,
                MAX(largest_killing_spree) as max_killing_spree,
                MAX(CASE 
                    WHEN deaths = 0 THEN kills + assists 
                    ELSE CAST((kills + assists) AS FLOAT) / deaths 
                END) as max_kda,
                ROUND(AVG(CAST(placement AS FLOAT)), 2) as avg_placement,
                SUM(CASE WHEN placement = 1 THEN 1 ELSE 0 END) as first_place_count
            FROM base_data
            GROUP BY champion_name
            HAVING total_games >= ?
        ),
        overall_stats AS (
            SELECT 
                ROUND(AVG(kill_participation * 100), 1) as overall_kill_participation,
                MAX(largest_killing_spree) as overall_max_killing_spree,
                (SELECT p2.champion_name FROM base_data p2 WHERE p2.largest_killing_spree = (SELECT MAX(largest_killing_spree) FROM base_data)) as max_killing_spree_champion,
                SUM(CASE WHEN first_blood_kill = 1 OR first_blood_assist = 1 THEN 1 ELSE 0 END) as overall_first_bloods,
                SUM(turret_takedowns + inhibitor_takedowns) as overall_objectives,
                ROUND(AVG(gold_earned / (game_duration / 60.0)), 0) as overall_gold_per_min,
                ROUND(AVG(total_damage_taken / (game_duration / 60.0)), 0) as overall_damage_taken_per_min,
                ROUND(AVG(total_minions_killed / (game_duration / 60.0)), 1) as overall_cs_per_min,
                MAX(CASE 
                    WHEN deaths = 0 THEN kills + assists 
                    ELSE CAST((kills + assists) AS FLOAT) / deaths 
                END) as overall_max_kda,
                (SELECT p2.champion_name FROM base_data p2 WHERE (CASE WHEN p2.deaths = 0 THEN p2.kills + p2.assists ELSE CAST((p2.kills + p2.assists) AS FLOAT) / p2.deaths END) = 
                    (SELECT MAX(CASE WHEN deaths = 0 THEN kills + assists ELSE CAST((kills + assists) AS FLOAT) / deaths END) FROM base_data)) as max_kda_champion,
                ROUND(AVG(vision_score), 1) as overall_vision_score,
                (SELECT summoner_level FROM base_data ORDER BY game_creation DESC LIMIT 1) as latest_summoner_level,
                (SELECT profile_icon FROM base_data ORDER BY game_creation DESC LIMIT 1) as latest_profile_icon
            FROM base_data
        )
        SELECT 
            champion_name,
            total_games as champion_games,
            winrate,
            avg_damage_per_minute,
            average_kda,
            (SELECT COUNT(*) FROM base_data) as total_games_overall,
            (SELECT COUNT(DISTINCT champion_name) FROM base_data) as unique_champions_played,
            ROUND(CAST((SELECT COUNT(DISTINCT champion_name) FROM base_data) AS FLOAT) / 
                (SELECT COUNT(*) FROM base_data) * 100, 1) as unique_champ_ratio,
            (SELECT MIN(game_creation) FROM base_data) as oldest_game,
            ROUND(CAST((SELECT SUM(game_duration) FROM base_data) AS FLOAT) / 3600, 1) as total_hours_played,
            total_triples,
            total_quadras,
            total_pentas,
            (SELECT SUM(penta_kills) FROM base_data) as total_pentas_overall,
            (SELECT ROUND(AVG(CASE WHEN wins = 1 THEN 100.0 ELSE 0 END), 1) FROM base_data) as total_winrate,
            avg_time_dead_pct,
            (SELECT overall_vision_score FROM overall_stats) as avg_vision_score,
            (SELECT overall_kill_participation FROM overall_stats) as avg_kill_participation,
            (SELECT overall_damage_taken_per_min FROM overall_stats) as avg_damage_taken_per_min,
            (SELECT overall_first_bloods FROM overall_stats) as total_first_bloods,
            (SELECT overall_objectives FROM overall_stats) as total_objectives,
            (SELECT overall_gold_per_min FROM overall_stats) as avg_gold_per_min,
            avg_cs_per_min,
            (SELECT overall_max_killing_spree FROM overall_stats) as max_killing_spree,
            (SELECT overall_max_kda FROM overall_stats) as max_kda,
            (SELECT max_killing_spree_champion FROM overall_stats) as max_killing_spree_champion,
            (SELECT max_kda_champion FROM overall_stats) as max_kda_champion,
            (SELECT latest_summoner_level FROM overall_stats) as summoner_level,
            (SELECT latest_profile_icon FROM overall_stats) as profile_icon,
            avg_placement,
            first_place_count
        FROM champion_stats
        ORDER BY {sort_column} {sort_order}, champion_games DESC
        LIMIT ?;
        '''

        if champion:
            # If champion is specified, filter for that champion and remove the HAVING clause
            query = base_query.format(
                champion_filter="AND LOWER(p.champion_name) = LOWER(?)",
                sort_column=sort_column,
                sort_order=sort_order
            )
            cursor.execute(query, (username, gamemode, champion, min_games, limit))
        else:
            # Original behavior: show champions with minimum games
            query = base_query.format(
                champion_filter="",
                sort_column=sort_column,
                sort_order=sort_order
            )
            cursor.execute(query, (username, gamemode, min_games, limit))

        results = cursor.fetchall()

        # Additional query to get latest summoner level and profile icon
        latest_info_query = '''
        SELECT summoner_level, profile_icon
        FROM participants p
        JOIN matches m ON p.match_id = m.match_id
        WHERE LOWER(p.riot_id_game_name) = LOWER(?)
        ORDER BY m.game_creation DESC
        LIMIT 1;
        '''
        cursor.execute(latest_info_query, (username,))
        latest_info = cursor.fetchone()
        conn.close()

        player_stats = []
        for row in results:
            player_stats.append(PlayerStats(
                champion_name=row[0],
                champion_games=row[1],
                winrate=row[2],
                avg_damage_per_minute=row[3],
                average_kda=row[4],
                total_games_overall=row[5],
                unique_champions_played=row[6],
                unique_champ_ratio=row[7],
                oldest_game=row[8],
                total_hours_played=row[9],
                total_triples=row[10],
                total_quadras=row[11],
                total_pentas=row[12],
                total_pentas_overall=row[13],
                total_winrate=row[14],
                avg_time_dead_pct=row[15],
                avg_vision_score=row[16],
                avg_kill_participation=row[17],
                avg_damage_taken_per_min=row[18],
                total_first_bloods=row[19],
                total_objectives=row[20],
                avg_gold_per_min=row[21],
                avg_cs_per_min=row[22],
                max_killing_spree=row[23],
                max_kda=row[24],
                max_killing_spree_champion=row[25],
                max_kda_champion=row[26],
                summoner_level=latest_info[0] if latest_info else 0,
                profile_icon=latest_info[1] if latest_info else 0,
                avg_placement=row[29],
                first_place_count=row[30]
            ))
        if not player_stats:
            # If no champion stats found, still create an entry with the latest summoner info
            player_stats.append(PlayerStats(
                champion_name="",
                champion_games=0,
                winrate=0.0,
                avg_damage_per_minute=0.0,
                average_kda=0.0,
                total_games_overall=0,
                unique_champions_played=0,
                unique_champ_ratio=0.0,
                oldest_game="",
                total_hours_played=0.0,
                total_triples=0,
                total_quadras=0,
                total_pentas=0,
                total_pentas_overall=0,
                total_winrate=0.0,
                avg_time_dead_pct=0.0,
                avg_vision_score=0.0,
                avg_kill_participation=0.0,
                avg_damage_taken_per_min=0.0,
                total_first_bloods=0,
                total_objectives=0,
                avg_gold_per_min=0.0,
                avg_cs_per_min=0.0,
                max_killing_spree=0,
                max_kda=0.0,
                max_killing_spree_champion="",
                max_kda_champion="",
                summoner_level=latest_info[0] if latest_info else 0,
                profile_icon=latest_info[1] if latest_info else 0,
                avg_placement=0.0,
                first_place_count=0
            ))
        return player_stats

    async def get_all_players_stats(self) -> List[UserStats]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
        WITH earliest_match AS (
            SELECT 
                puuid, 
                MIN(m.game_creation) AS first_game_date,
                (SELECT p2.match_id 
                 FROM participants p2 
                 JOIN matches m2 ON p2.match_id = m2.match_id 
                 WHERE p2.puuid = p1.puuid 
                 ORDER BY m2.game_creation ASC LIMIT 1) AS first_match_id
            FROM participants p1
            JOIN matches m ON p1.match_id = m.match_id
            GROUP BY p1.puuid
        )
        SELECT 
            p.riot_id_game_name,
            p.riot_id_tagline,
            ROUND(SUM(p.time_played) / 3600.0, 2) AS total_hours_played,
            ROUND(
                SUM(
                    CASE 
                        WHEN strftime('%Y', m.game_creation) = '2025' 
                        THEN p.time_played 
                        ELSE 0 
                    END
                ) / 3600.0, 2
            ) AS total_hours_2024,
            COUNT(p.match_id) AS games_played,
            ROUND(AVG(p.time_played) / 60.0, 2) AS avg_minutes_per_game,
            e.first_game_date,
            SUM(p.penta_kills) as total_pentas,
            ROUND(100.0 * SUM(CASE WHEN p.wins = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as winrate
        FROM participants p
        JOIN matches m ON p.match_id = m.match_id
        JOIN earliest_match e ON p.puuid = e.puuid
        JOIN participants ep ON ep.puuid = e.puuid AND ep.match_id = e.first_match_id
        GROUP BY p.puuid
        ORDER BY total_hours_played DESC
        LIMIT 20;
        '''
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        return [UserStats(
            riot_id_game_name=row[0],
            riot_id_tagline=row[1],
            total_hours_played=row[2],
            total_hours_2024=row[3],
            games_played=row[4],
            avg_minutes_per_game=row[5],
            first_game_date=row[6],
            total_pentas=row[7],
            winrate=row[8]
        ) for row in results]

    async def get_player_friend_stats(self, username) -> List[PlayerFriendStats]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
        WITH my_matches AS (
            SELECT 
                p.match_id, 
                p.team_id, 
                CASE WHEN p.wins = 1 THEN 1 ELSE 0 END AS my_win
            FROM participants p
            WHERE LOWER(p.riot_id_game_name) = LOWER(?)
        ),
        teammates AS (
            SELECT
                p2.riot_id_game_name AS teammate_name,
                COUNT(*) AS games_together,
                SUM(CASE WHEN m.my_win = 1 THEN 1 ELSE 0 END) AS wins_together,
                ROUND(
                    100.0 * SUM(CASE WHEN m.my_win = 1 THEN 1 ELSE 0 END) 
                    / COUNT(*), 1
                ) AS win_rate
            FROM my_matches m
            JOIN participants p2 ON p2.match_id = m.match_id
            WHERE p2.team_id = m.team_id
              AND LOWER(p2.riot_id_game_name) <> LOWER(?)
            GROUP BY p2.riot_id_game_name
            HAVING COUNT(*) >= 5
        )
        SELECT *
        FROM teammates
        ORDER BY win_rate DESC, games_together DESC
        LIMIT 15;
        '''
        
        cursor.execute(query, (username, username))
        results = cursor.fetchall()
        conn.close()
        
        return [PlayerFriendStats(
            teammate_name=row[0],
            games_together=row[1],
            wins_together=row[2],
            win_rate=row[3]
        ) for row in results]

    async def get_stored_match_ids(self, puuid) -> Set[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT match_id 
            FROM participants 
            WHERE puuid = ?
            UNION
            SELECT match_id
            FROM matches
            WHERE game_duration = 0
        ''', (puuid,))
        stored_matches = set(row[0] for row in cursor.fetchall())
        conn.close()
        return stored_matches

    async def get_player_match_ids(self, riot_id_game_name: str, game_mode: str = None, limit: int = None, start_date: str = None, end_date: str = None) -> List[str]:
        """
        Get match IDs for a player by their riot game name.
        
        Args:
            riot_id_game_name: Player's Riot ID game name
            game_mode: Optional game mode filter (e.g., 'CLASSIC', 'ARAM', 'CHERRY')
            limit: Optional limit on number of match IDs to return
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)
            
        Returns:
            List of match IDs for the player
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build the query with optional filters
        query = '''
            SELECT DISTINCT p.match_id
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE LOWER(p.riot_id_game_name) = LOWER(?)
        '''
        params = [riot_id_game_name]
        
        if game_mode:
            query += ' AND LOWER(m.game_mode) = LOWER(?)'
            params.append(game_mode)
            
        if start_date:
            query += ' AND DATE(m.game_creation) >= ?'
            params.append(start_date)
            
        if end_date:
            query += ' AND DATE(m.game_creation) <= ?'
            params.append(end_date)
            
        # Order by game creation date (newest first)
        query += ' ORDER BY m.game_creation DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
            
        cursor.execute(query, params)
        match_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return match_ids

    async def get_match_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM matches')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    async def get_users(self, guild_id = None, active = False) -> List[User]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if guild_id:
            cursor.execute('SELECT id, username, puuid, riot_id_game_name, riot_id_tagline, guild_id, active, last_game_played FROM users WHERE guild_id = ?', (guild_id,))
        elif active:
            cursor.execute('SELECT id, username, puuid, riot_id_game_name, riot_id_tagline, guild_id, active, last_game_played FROM users WHERE active = ?', (active,))
        else:
            cursor.execute('SELECT id, username, puuid, riot_id_game_name, riot_id_tagline, guild_id, active, last_game_played FROM users')
        results = cursor.fetchall()
        conn.close()
        
        return [User(
            id=row[0],
            username=row[1],
            puuid=row[2],
            riot_id_game_name=row[3],
            riot_id_tagline=row[4],
            guild_id=row[5],
            active=bool(row[6]),
            last_game_played=row[7]
        ) for row in results]

    async def get_champion(self, id) -> Optional[str]:
        #get version with riotapioperations
        versions = await self.bot.get_cog("RiotAPIOperations").get_versions()
        url = f"https://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/en_US/champion.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                for champ_name, champ_data in data['data'].items():
                    if int(champ_data['key']) == id:
                        return champ_data['id']
        return None

    async def insert_match(self, match_data):
        match_id = match_data['metadata']['matchId']
        info = match_data['info']
        metadata = match_data['metadata']
        
        print(f"🔄 Processing match: {match_id}")
        print(f"📊 Match has {len(info.get('participants', []))} participants")
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256 MB
            
            cursor.execute('''
            INSERT OR REPLACE INTO matches (
                match_id, game_duration, game_version, game_mode, game_type, 
                game_creation, game_end, data_version, end_of_game_result,
                game_id, game_name, game_start_timestamp, game_end_timestamp,
                map_id, platform_id, queue_id, tournament_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_id,
                info.get('gameDuration', 0),
                info.get('gameVersion', ''),
                info.get('gameMode', ''),
                info.get('gameType', ''),
                datetime.fromtimestamp(info.get('gameCreation', 0)/1000) if info.get('gameCreation') else None,
                datetime.fromtimestamp(info.get('gameEndTimestamp', 0)/1000) if info.get('gameEndTimestamp') else None,
                metadata.get('dataVersion', ''),
                info.get('endOfGameResult', ''),
                info.get('gameId', 0),
                info.get('gameName', ''),
                info.get('gameStartTimestamp', 0),
                info.get('gameEndTimestamp', 0),
                info.get('mapId', 0),
                info.get('platformId', ''),
                info.get('queueId', 0),
                info.get('tournamentCode', '')
            ))

            # Insert team data
            for team in info.get('teams', []):
                cursor.execute('''
                INSERT OR REPLACE INTO teams (match_id, team_id, win) 
                VALUES (?, ?, ?)
                ''', (match_id, team.get('teamId', 0), team.get('win', False)))
                
                # Insert bans for this team
                for ban in team.get('bans', []):
                    cursor.execute('''
                    INSERT OR REPLACE INTO bans (match_id, team_id, champion_id, pick_turn)
                    VALUES (?, ?, ?, ?)
                    ''', (match_id, team.get('teamId', 0), ban.get('championId', 0), ban.get('pickTurn', 0)))
                
                # Insert objectives for this team
                objectives = team.get('objectives', {})
                for obj_type, obj_data in objectives.items():
                    if isinstance(obj_data, dict):
                        cursor.execute('''
                        INSERT OR REPLACE INTO objectives (match_id, team_id, objective_type, first, kills)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (match_id, team.get('teamId', 0), obj_type, 
                              obj_data.get('first', False), obj_data.get('kills', 0)))

            # Insert participant data with all new fields
            for participant in info.get('participants', []):
                # Helper function to safely get values with defaults
                def get_safe(key, default=0):
                    return participant.get(key, default)
                
                # Helper function to safely get nested challenge values
                def get_challenge(key, default=0):
                    return participant.get('challenges', {}).get(key, default)
                
                # Helper function to get missions data
                def get_mission(key, default=0):
                    return participant.get('missions', {}).get(key, default)

                cursor.execute('''
                INSERT OR REPLACE INTO participants (
                    match_id, puuid, summoner_name, champion_name, champion_id,
                    team_id, team_position, individual_position, lane, role,
                    wins, kills, deaths, assists, kda, kill_participation,
                    champion_level, vision_score, total_damage_dealt,
                    total_damage_to_champions, physical_damage_to_champions,
                    magic_damage_to_champions, true_damage_to_champions,
                    total_damage_taken, gold_earned, gold_spent,
                    total_minions_killed, vision_wards_bought,
                    sight_wards_bought, wards_placed, wards_killed,
                    champion_experience, time_played, total_time_spent_dead,
                    item0, item1, item2, item3, item4, item5, item6,
                    bounty_level, killing_sprees, largest_killing_spree,
                    largest_multi_kill, longest_time_spent_living, double_kills,
                    triple_kills, quadra_kills, penta_kills, unreal_kills,
                    damage_dealt_to_buildings, damage_dealt_to_objectives,
                    damage_dealt_to_turrets, damage_self_mitigated,
                    largest_critical_strike, inhibitor_kills, inhibitor_takedowns,
                    inhibitors_lost, nexus_kills, nexus_lost, nexus_takedowns,
                    turret_kills, turret_takedowns, turrets_lost, champion_transform,
                    consumables_purchased, items_purchased, neutral_minions_killed,
                    total_ally_jungle_minions_killed, total_enemy_jungle_minions_killed,
                    total_time_cc_dealt, total_units_healed, first_blood_assist,
                    first_blood_kill, first_tower_assist, first_tower_kill,
                    game_ended_in_surrender, game_ended_in_early_surrender,
                    team_early_surrendered, spell1_casts, spell2_casts, spell3_casts,
                    spell4_casts, summoner1_casts, summoner2_casts, summoner1_id,
                    summoner2_id, total_heal, total_heals_on_teammates,
                    total_damage_shielded_on_teammates, all_in_pings, assist_me_pings,
                    basic_pings, command_pings, danger_pings, enemy_missing_pings,
                    enemy_vision_pings, get_back_pings, hold_pings, need_vision_pings,
                    on_my_way_pings, push_pings, retreat_pings, vision_cleared_pings,
                    summoner_level, riot_id_game_name, riot_id_tagline, profile_icon,
                    baron_kills, dragon_kills, eligible_for_progression,
                    magic_damage_dealt, magic_damage_taken, physical_damage_dealt,
                    physical_damage_taken, true_damage_dealt, true_damage_taken,
                    objectives_stolen, objectives_stolen_assists, participant_id,
                    placement, player_augment1, player_augment2, player_augment3,
                    player_augment4, player_subteam_id, subteam_placement,
                    summoner_id, time_ccing_others, detector_wards_placed,
                    sight_wards_bought_in_game, vision_wards_bought_in_game,
                    player_score0, player_score1, player_score2, player_score3,
                    player_score4, player_score5, player_score6, player_score7,
                    player_score8, player_score9, player_score10, player_score11
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                ''', (
                    match_id,
                    get_safe('puuid'),
                    get_safe('summonerName'),
                    get_safe('championName'),
                    get_safe('championId'),
                    get_safe('teamId'),
                    get_safe('teamPosition'),
                    get_safe('individualPosition'),
                    get_safe('lane'),
                    get_safe('role'),
                    get_safe('win'),
                    get_safe('kills'),
                    get_safe('deaths'),
                    get_safe('assists'),
                    get_challenge('kda') or (get_safe('kills') + get_safe('assists')) / max(get_safe('deaths'), 1),
                    get_challenge('killParticipation'),
                    get_safe('champLevel'),
                    get_safe('visionScore'),
                    get_safe('totalDamageDealt'),
                    get_safe('totalDamageDealtToChampions'),
                    get_safe('physicalDamageDealtToChampions'),
                    get_safe('magicDamageDealtToChampions'),
                    get_safe('trueDamageDealtToChampions'),
                    get_safe('totalDamageTaken'),
                    get_safe('goldEarned'),
                    get_safe('goldSpent'),
                    get_safe('totalMinionsKilled'),
                    get_safe('visionWardsBoughtInGame'),
                    get_safe('sightWardsBoughtInGame'),
                    get_safe('wardsPlaced'),
                    get_safe('wardsKilled'),
                    get_safe('champExperience'),
                    get_safe('timePlayed'),
                    get_safe('totalTimeSpentDead'),
                    get_safe('item0'),
                    get_safe('item1'),
                    get_safe('item2'),
                    get_safe('item3'),
                    get_safe('item4'),
                    get_safe('item5'),
                    get_safe('item6'),
                    get_safe('bountyLevel'),
                    get_safe('killingSprees'),
                    get_safe('largestKillingSpree'),
                    get_safe('largestMultiKill'),
                    get_safe('longestTimeSpentLiving'),
                    get_safe('doubleKills'),
                    get_safe('tripleKills'),
                    get_safe('quadraKills'),
                    get_safe('pentaKills'),
                    get_safe('unrealKills'),
                    get_safe('damageDealtToBuildings'),
                    get_safe('damageDealtToObjectives'),
                    get_safe('damageDealtToTurrets'),
                    get_safe('damageSelfMitigated'),
                    get_safe('largestCriticalStrike'),
                    get_safe('inhibitorKills'),
                    get_safe('inhibitorTakedowns'),
                    get_safe('inhibitorsLost'),
                    get_safe('nexusKills'),
                    get_safe('nexusLost'),
                    get_safe('nexusTakedowns'),
                    get_safe('turretKills'),
                    get_safe('turretTakedowns'),
                    get_safe('turretsLost'),
                    get_safe('championTransform'),
                    get_safe('consumablesPurchased'),
                    get_safe('itemsPurchased'),
                    get_safe('neutralMinionsKilled'),
                    get_safe('totalAllyJungleMinionsKilled'),
                    get_safe('totalEnemyJungleMinionsKilled'),
                    get_safe('totalTimeCCDealt'),
                    get_safe('totalUnitsHealed'),
                    get_safe('firstBloodAssist'),
                    get_safe('firstBloodKill'),
                    get_safe('firstTowerAssist'),
                    get_safe('firstTowerKill'),
                    get_safe('gameEndedInSurrender'),
                    get_safe('gameEndedInEarlySurrender'),
                    get_safe('teamEarlySurrendered'),
                    get_safe('spell1Casts'),
                    get_safe('spell2Casts'),
                    get_safe('spell3Casts'),
                    get_safe('spell4Casts'),
                    get_safe('summoner1Casts'),
                    get_safe('summoner2Casts'),
                    get_safe('summoner1Id'),
                    get_safe('summoner2Id'),
                    get_safe('totalHeal'),
                    get_safe('totalHealsOnTeammates'),
                    get_safe('totalDamageShieldedOnTeammates'),
                    get_safe('allInPings'),
                    get_safe('assistMePings'),
                    get_safe('basicPings'),
                    get_safe('commandPings'),
                    get_safe('dangerPings'),
                    get_safe('enemyMissingPings'),
                    get_safe('enemyVisionPings'),
                    get_safe('getBackPings'),
                    get_safe('holdPings'),
                    get_safe('needVisionPings'),
                    get_safe('onMyWayPings'),
                    get_safe('pushPings'),
                    get_safe('retreatPings'),
                    get_safe('visionClearedPings'),
                    get_safe('summonerLevel'),
                    get_safe('riotIdGameName'),
                    get_safe('riotIdTagline'),
                    get_safe('profileIcon'),
                    # New fields
                    get_safe('baronKills'),
                    get_safe('dragonKills'),
                    get_safe('eligibleForProgression'),
                    get_safe('magicDamageDealt'),
                    get_safe('magicDamageTaken'),
                    get_safe('physicalDamageDealt'),
                    get_safe('physicalDamageTaken'),
                    get_safe('trueDamageDealt'),
                    get_safe('trueDamageTaken'),
                    get_safe('objectivesStolen'),
                    get_safe('objectivesStolenAssists'),
                    get_safe('participantId'),
                    get_safe('placement'),
                    get_safe('playerAugment1'),
                    get_safe('playerAugment2'),
                    get_safe('playerAugment3'),
                    get_safe('playerAugment4'),
                    get_safe('playerSubteamId'),
                    get_safe('subteamPlacement'),
                    get_safe('summonerId'),
                    get_safe('timeCCingOthers'),
                    get_safe('detectorWardsPlaced'),
                    get_safe('sightWardsBoughtInGame'),
                    get_safe('visionWardsBoughtInGame'),
                    # Mission scores
                    get_mission('playerScore0'),
                    get_mission('playerScore1'),
                    get_mission('playerScore2'),
                    get_mission('playerScore3'),
                    get_mission('playerScore4'),
                    get_mission('playerScore5'),
                    get_mission('playerScore6'),
                    get_mission('playerScore7'),
                    get_mission('playerScore8'),
                    get_mission('playerScore9'),
                    get_mission('playerScore10'),
                    get_mission('playerScore11')
                ))
                
                # Insert challenges data if available (simplified for now)
                challenges = participant.get('challenges', {})
                if challenges:
                    print(f"📈 Found {len(challenges)} challenges for participant {get_safe('participantId')}")
                
                # Insert perks data if available (simplified for now)  
                perks = participant.get('perks', {})
                if perks:
                    print(f"🔮 Found perks data for participant {get_safe('participantId')}")

            conn.commit()
            print(f"✅ Successfully inserted match: {match_id}")
            
        except sqlite3.OperationalError as e:
            print(f"❌ Database operational error for match {match_id}: {e}")
            if conn:
                conn.rollback()
            raise e
        except sqlite3.Error as e:
            print(f"❌ Database error for match {match_id}: {e}")
            if conn:
                conn.rollback()
            raise e
        except Exception as e:
            print(f"❌ Unexpected error for match {match_id}: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
                print(f"🔐 Database connection closed for match: {match_id}")

    async def insert_user(self, username, puuid, riot_id_game_name, riot_id_tagline, inter, active = "TRUE"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        guild_id = inter.guild.id
        
        cursor.execute('''
        INSERT OR REPLACE INTO users (
            username, puuid, riot_id_game_name, riot_id_tagline, guild_id, active
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, puuid, riot_id_game_name, riot_id_tagline, guild_id, active))
        
        conn.commit()
        conn.close()
    
    async def insert_champions(self, champions_data: List[dict]) -> int:
        """
        Insert or update champion data in the database.
        Args:
            champions_data: List of dictionaries containing champion data with the following structure:
                {
                    'id': int,
                    'name': str,
                    'title': str,
                    'image_full': str,
                    'image_sprite': str,
                    'image_group': str,
                    'tags': str,  # Comma-separated values
                    'partype': str,
                    'stats_hp': float,
                    'stats_hpperlevel': float,
                    'stats_mp': float,
                    'stats_mpperlevel': float,
                    'stats_movespeed': float,
                    'stats_armor': float,
                    'stats_armorperlevel': float,
                    'stats_spellblock': float,
                    'stats_spellblockperlevel': float,
                    'stats_attackrange': float,
                    'stats_hpregen': float,
                    'stats_hpregenperlevel': float,
                    'stats_mpregen': float,
                    'stats_mpregenperlevel': float,
                    'stats_crit': float,
                    'stats_critperlevel': float,
                    'stats_attackdamage': float,
                    'stats_attackdamageperlevel': float,
                    'stats_attackspeedperlevel': float,
                    'stats_attackspeed': float
                }
        Returns:
            Number of champions added/updated
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        champions_added = 0

        try:
            for champion in champions_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO champions (
                        id, name, title, image_full, image_sprite, image_group,
                        tags, partype, stats_hp, stats_hpperlevel, stats_mp,
                        stats_mpperlevel, stats_movespeed, stats_armor,
                        stats_armorperlevel, stats_spellblock,
                        stats_spellblockperlevel, stats_attackrange,
                        stats_hpregen, stats_hpregenperlevel, stats_mpregen,
                        stats_mpregenperlevel, stats_crit, stats_critperlevel,
                        stats_attackdamage, stats_attackdamageperlevel,
                        stats_attackspeedperlevel, stats_attackspeed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    champion['id'],
                    champion['name'],
                    champion['title'],
                    champion['image_full'],
                    champion['image_sprite'],
                    champion['image_group'],
                    champion['tags'],
                    champion['partype'],
                    champion['stats_hp'],
                    champion['stats_hpperlevel'],
                    champion['stats_mp'],
                    champion['stats_mpperlevel'],
                    champion['stats_movespeed'],
                    champion['stats_armor'],
                    champion['stats_armorperlevel'],
                    champion['stats_spellblock'],
                    champion['stats_spellblockperlevel'],
                    champion['stats_attackrange'],
                    champion['stats_hpregen'],
                    champion['stats_hpregenperlevel'],
                    champion['stats_mpregen'],
                    champion['stats_mpregenperlevel'],
                    champion['stats_crit'],
                    champion['stats_critperlevel'],
                    champion['stats_attackdamage'],
                    champion['stats_attackdamageperlevel'],
                    champion['stats_attackspeedperlevel'],
                    champion['stats_attackspeed']
                ))
                champions_added += 1

            conn.commit()
            return champions_added
        except Exception as e:
            print(f"Error inserting champions: {e}")
            await self.bot.get_channel(self.bot.botlol_channel_id).send(f"Error inserting champions: {e}")
            return 0
        finally:
            conn.close()

    async def update_user(self, username, puuid = None, riot_id_game_name = None, riot_id_tagline = None, last_game_played = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query dynamically based on non-None values
        update_fields = []
        params = []
        if puuid is not None:
            update_fields.append("puuid = ?")
            params.append(puuid)
        if riot_id_game_name is not None:
            update_fields.append("riot_id_game_name = ?") 
            params.append(riot_id_game_name)
        if riot_id_tagline is not None:
            update_fields.append("riot_id_tagline = ?")
            params.append(riot_id_tagline)
        if last_game_played is not None:
            update_fields.append("last_game_played = ?")
            params.append(last_game_played)
            
        if update_fields:
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?"
            params.append(username)
            cursor.execute(query, params)
            
        conn.commit()
        conn.close()
    
    async def get_champion_names(self) -> List[str]:
        """Get all champion names from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT image_full FROM champions ORDER BY name')
        #remove .png from the end of the string
        names = [row[0].replace('.png', '') for row in cursor.fetchall()]
        conn.close()
        return names
        
    async def get_match_info(self, match_id: str) -> tuple:
        """Get basic match information from the database.
        
        Args:
            match_id: The match ID to retrieve
            
        Returns:
            Tuple containing (game_mode, game_duration, game_end)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT game_mode, game_duration, game_end, game_creation
            FROM matches
            WHERE match_id = ?
        ''', (match_id,))
        match_info = cursor.fetchone()
        conn.close()
        return match_info
        
    async def get_match_participants(self, match_id: str) -> list:
        """Get all participants data for a specific match.
        
        Args:
            match_id: The match ID to retrieve participants for
            
        Returns:
            List of dictionaries containing participant data
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # This makes fetchall() return dictionaries
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                p.riot_id_game_name, p.champion_name, p.team_id, p.wins,
                p.kills, p.deaths, p.assists, p.total_damage_to_champions,
                p.vision_score, p.gold_earned, p.total_minions_killed,
                p.total_time_spent_dead, p.largest_killing_spree,
                p.largest_multi_kill, p.penta_kills, p.profile_icon,
                p.puuid, p.summoner_level, p.kda, p.kill_participation,
                p.total_damage_dealt, p.damage_self_mitigated,
                p.total_heal, p.total_heals_on_teammates,
                p.total_damage_shielded_on_teammates, p.placement
            FROM participants p
            WHERE p.match_id = ?
            ORDER BY p.team_id, p.total_damage_to_champions DESC
        ''', (match_id,))
        participants_data = cursor.fetchall()
        
        # Convert sqlite3.Row objects to dictionaries
        result = [dict(row) for row in participants_data]
        conn.close()
        return result

    async def get_champion_global_stats(self, champion_name, gamemode) -> Optional[PlayerStats]:
        """Get global average statistics for a specific champion in a specific gamemode.
        
        Args:
            champion_name: The champion name to get stats for
            gamemode: The game mode to filter by
            
        Returns:
            PlayerStats object with average statistics across all players
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        WITH champion_data AS (
            SELECT p.*, m.game_duration, m.game_creation
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE LOWER(p.champion_name) = LOWER(?)
            AND LOWER(m.game_mode) = LOWER(?)
        )
        SELECT 
            champion_name,
            COUNT(*) as champion_games,
            ROUND(AVG(CASE WHEN wins = 1 THEN 100.0 ELSE 0 END), 1) as winrate,
            ROUND(AVG(total_damage_to_champions / (game_duration / 60.0)), 0) as avg_damage_per_minute,
            ROUND(AVG(CASE 
                WHEN deaths = 0 THEN kills + assists 
                ELSE CAST((kills + assists) AS FLOAT) / deaths 
            END), 2) as average_kda,
            ROUND(AVG(CAST(kills AS FLOAT)), 1) as avg_kills,
            ROUND(AVG(CAST(deaths AS FLOAT)), 1) as avg_deaths,
            ROUND(AVG(CAST(assists AS FLOAT)), 1) as avg_assists,
            SUM(triple_kills) as total_triples,
            SUM(quadra_kills) as total_quadras,
            SUM(penta_kills) as total_pentas,
            ROUND(AVG(CAST(total_time_spent_dead AS FLOAT) / game_duration * 100), 1) as avg_time_dead_pct,
            ROUND(AVG(vision_score), 1) as avg_vision_score,
            ROUND(AVG(kill_participation * 100), 1) as avg_kill_participation,
            ROUND(AVG(total_damage_taken / (game_duration / 60.0)), 0) as avg_damage_taken_per_min,
            SUM(CASE WHEN first_blood_kill = 1 OR first_blood_assist = 1 THEN 1 ELSE 0 END) as total_first_bloods,
            SUM(turret_takedowns + inhibitor_takedowns) as total_objectives,
            ROUND(AVG(gold_earned / (game_duration / 60.0)), 0) as avg_gold_per_min,
            ROUND(AVG(total_minions_killed / (game_duration / 60.0)), 1) as avg_cs_per_min,
            ROUND(AVG(damage_self_mitigated), 0) as avg_damage_mitigated,
            MAX(largest_killing_spree) as max_killing_spree,
            MAX(CASE 
                WHEN deaths = 0 THEN kills + assists 
                ELSE CAST((kills + assists) AS FLOAT) / deaths 
            END) as max_kda
        FROM champion_data
        GROUP BY champion_name
        '''
        
        cursor.execute(query, (champion_name, gamemode))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        return PlayerStats(
            champion_name=result[0],
            champion_games=result[1],
            winrate=result[2],
            avg_damage_per_minute=result[3],
            average_kda=result[4],
            total_games_overall=result[1],  # Same as champion_games for global stats
            unique_champions_played=1,  # Only one champion
            unique_champ_ratio=100.0,  # 100% since only one champion
            oldest_game="",  # Not relevant for global stats
            total_hours_played=0.0,  # Not calculated for global stats
            total_triples=result[8],
            total_quadras=result[9],
            total_pentas=result[10],
            total_pentas_overall=result[10],  # Same as total_pentas for global stats
            total_winrate=result[2],  # Same as winrate for global stats
            avg_time_dead_pct=result[11],
            avg_vision_score=result[12],
            avg_kill_participation=result[13],
            avg_damage_taken_per_min=result[14],
            total_first_bloods=result[15],
            total_objectives=result[16],
            avg_gold_per_min=result[17],
            avg_cs_per_min=result[18],  # New field for CS per minute
            max_killing_spree=result[19],
            max_kda=result[20],
            max_killing_spree_champion=result[0],  # Same as champion_name
            max_kda_champion=result[0],  # Same as champion_name
            summoner_level=0,  # Not relevant for global stats
            profile_icon=0  # Not relevant for global stats
        )

    async def get_leaderboard_kda(self, gamemode: str, guild_id: int, period: str = "Weekly", limit: int = 10) -> List[Tuple[str, float, int, int]]:
        """Fetches the KDA leaderboard for the specified period, retrieving the profile icon from the player's latest game in this mode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        params = [gamemode, gamemode, guild_id] # Base params for subquery and main query
        where_clauses = [
            "LOWER(m.game_mode) = LOWER(?)",
            "u.guild_id = ?",
            "p.riot_id_game_name IS NOT NULL AND p.riot_id_game_name != '0' AND p.riot_id_game_name != ''"
        ]

        if period != "All Time":
            today = date.today()
            if period == "Weekly":
                start_date = today - timedelta(days=today.weekday())
            elif period == "Monthly":
                start_date = today.replace(day=1)
            else: # Default to weekly if invalid period somehow passed
                start_date = today - timedelta(days=today.weekday())
            
            start_datetime = datetime.combine(start_date, dt_time.min)
            start_string = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append("m.game_end >= ?")
            params.append(start_string)

        query = f"""
        SELECT
            p.riot_id_game_name,
            ROUND(AVG(CASE
                WHEN p.deaths = 0 THEN p.kills + p.assists
                ELSE CAST(p.kills + p.assists AS FLOAT) / p.deaths
            END), 2) as average_kda,
            COUNT(DISTINCT p.match_id) as total_games,
            (SELECT pp.profile_icon
             FROM participants pp
             JOIN matches mm ON pp.match_id = mm.match_id
             WHERE pp.puuid = p.puuid AND LOWER(mm.game_mode) = LOWER(?)
             ORDER BY mm.game_end DESC
             LIMIT 1
            ) as latest_profile_icon_id
        FROM participants p
        JOIN matches m ON p.match_id = m.match_id
        INNER JOIN users u ON p.puuid = u.puuid
        WHERE {" AND ".join(where_clauses)}
        GROUP BY p.puuid, p.riot_id_game_name
        HAVING total_games > 0
        ORDER BY average_kda DESC
        LIMIT ?;
        """
        params.append(limit) # Add limit to the end of params
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    async def get_leaderboard_winrate(self, gamemode: str, guild_id: int, period: str = "Weekly", min_games: int = 10, limit: int = 10) -> List[Tuple[str, float, int, int]]:
        """Fetches the Win Rate leaderboard for the specified period, retrieving the profile icon from the player's latest game in this mode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        params = [gamemode, gamemode, guild_id]
        where_clauses = [
            "LOWER(m.game_mode) = LOWER(?)",
            "u.guild_id = ?",
            "p.riot_id_game_name IS NOT NULL AND p.riot_id_game_name != '0' AND p.riot_id_game_name != ''"
        ]

        if period != "All Time":
            today = date.today()
            if period == "Weekly":
                start_date = today - timedelta(days=today.weekday())
            elif period == "Monthly":
                start_date = today.replace(day=1)
            else: 
                start_date = today - timedelta(days=today.weekday())
            
            start_datetime = datetime.combine(start_date, dt_time.min)
            start_string = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append("m.game_end >= ?")
            params.append(start_string)

        query = f"""
        SELECT
            p.riot_id_game_name,
            ROUND(AVG(CASE WHEN p.wins = 1 THEN 100.0 ELSE 0 END), 1) as winrate,
            COUNT(DISTINCT p.match_id) as total_games,
            (SELECT pp.profile_icon
             FROM participants pp
             JOIN matches mm ON pp.match_id = mm.match_id
             WHERE pp.puuid = p.puuid AND LOWER(mm.game_mode) = LOWER(?)
             ORDER BY mm.game_end DESC
             LIMIT 1
            ) as latest_profile_icon_id
        FROM participants p
        JOIN matches m ON p.match_id = m.match_id
        INNER JOIN users u ON p.puuid = u.puuid
        WHERE {" AND ".join(where_clauses)}
        GROUP BY p.puuid, p.riot_id_game_name
        HAVING total_games >= ?
        ORDER BY winrate DESC
        LIMIT ?;
        """
        params.append(min_games) # Add min_games
        params.append(limit)     # Add limit
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    async def get_leaderboard_dpm(self, gamemode: str, guild_id: int, period: str = "Weekly", limit: int = 10) -> List[Tuple[str, int, int, int]]:
        """Fetches the DPM leaderboard for the specified period, retrieving the profile icon from the player's latest game in this mode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        params = [gamemode, gamemode, guild_id] # Base params for subquery and main query
        where_clauses = [
            "LOWER(m.game_mode) = LOWER(?)",
            "u.guild_id = ?",
            "p.riot_id_game_name IS NOT NULL AND p.riot_id_game_name != '0' AND p.riot_id_game_name != ''",
            "m.game_duration > 0" # Ensure game duration is positive to avoid division by zero
        ]

        if period != "All Time":
            today = date.today()
            if period == "Weekly":
                start_date = today - timedelta(days=today.weekday())
            elif period == "Monthly":
                start_date = today.replace(day=1)
            else: # Default to weekly
                start_date = today - timedelta(days=today.weekday())

            start_datetime = datetime.combine(start_date, dt_time.min)
            start_string = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            where_clauses.append("m.game_end >= ?")
            params.append(start_string)

        query = f"""
        SELECT
            p.riot_id_game_name,
            -- Calculate Average DPM (Damage Per Minute)
            ROUND(AVG(p.total_damage_to_champions / (m.game_duration / 60.0)), 0) as average_dpm,
            COUNT(DISTINCT p.match_id) as total_games,
            (SELECT pp.profile_icon
             FROM participants pp
             JOIN matches mm ON pp.match_id = mm.match_id
             WHERE pp.puuid = p.puuid AND LOWER(mm.game_mode) = LOWER(?)
             ORDER BY mm.game_end DESC
             LIMIT 1
            ) as latest_profile_icon_id
        FROM participants p
        JOIN matches m ON p.match_id = m.match_id
        INNER JOIN users u ON p.puuid = u.puuid
        WHERE {" AND ".join(where_clauses)}
        GROUP BY p.puuid, p.riot_id_game_name
        HAVING total_games > 0 AND average_dpm IS NOT NULL -- Ensure DPM could be calculated
        ORDER BY average_dpm DESC
        LIMIT ?;
        """
        params.append(limit) # Add limit to the end of params
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        # Result tuple: (name, dpm, games, latest_profile_icon_id)
        # Convert DPM to int here
        return [(name, int(dpm) if dpm is not None else 0, games, icon) for name, dpm, games, icon in results]

    async def create_pending_matches_table(self):
        """Create the pending_matches table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_matches (
                match_id TEXT PRIMARY KEY,
                game_mode TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    async def add_pending_match(self, match_id: str, game_mode: str, channel_id: int, message_id: int):
        """Add a match to the pending matches queue"""
        await self.create_pending_matches_table()  # Ensure table exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pending_matches 
            (match_id, game_mode, channel_id, message_id, attempts, created_at, last_attempt)
            VALUES (?, ?, ?, ?, 0, datetime('now'), datetime('now'))
        """, (match_id, game_mode, channel_id, message_id))
        conn.commit()
        conn.close()

    async def get_pending_matches(self, if_older_than: int = 0) -> list:
        """Get all pending matches that need to be retried"""
        await self.create_pending_matches_table()  # Ensure table exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT match_id, game_mode, channel_id, message_id, attempts, created_at, last_attempt
            FROM pending_matches
            WHERE created_at < datetime('now', '-{} minutes')  -- Maximum 10 attempts
            ORDER BY created_at ASC
        """.format(if_older_than))
        results = cursor.fetchall()
        conn.close()
        return results

    async def update_pending_match_attempt(self, match_id: str):
        """Increment the attempt counter and update last_attempt timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pending_matches 
            SET attempts = attempts + 1, last_attempt = datetime('now')
            WHERE match_id = ?
        """, (match_id,))
        conn.commit()
        conn.close()

    async def remove_pending_match(self, match_id: str):
        """Remove a match from the pending matches queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_matches WHERE match_id = ?", (match_id,))
        conn.commit()
        conn.close()

    async def cleanup_old_pending_matches(self, days: int = 7):
        """Remove pending matches older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM pending_matches 
            WHERE created_at < datetime('now', '-{} days')
        """.format(days))
        conn.commit()
        conn.close()

def setup(bot):
    bot.add_cog(DatabaseOperations(bot))