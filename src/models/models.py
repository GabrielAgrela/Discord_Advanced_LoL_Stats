from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Match:
    match_id: str
    game_duration: int
    game_version: str
    game_mode: str
    game_type: str
    game_creation: str
    game_end: str

@dataclass
class Participant:
    id: int
    match_id: str
    puuid: str
    summoner_name: str
    champion_name: str
    champion_id: int
    team_id: int
    team_position: str
    individual_position: str
    lane: str
    role: str
    wins: bool
    # Combat stats
    kills: int
    deaths: int
    assists: int
    kda: float
    kill_participation: float
    champion_level: int
    vision_score: int
    # Damage stats
    total_damage_dealt: int
    total_damage_to_champions: int
    physical_damage_to_champions: int
    magic_damage_to_champions: int
    true_damage_to_champions: int
    total_damage_taken: int
    # Economy stats
    gold_earned: int
    gold_spent: int
    total_minions_killed: int
    # Vision stats
    vision_wards_bought: int
    sight_wards_bought: int
    wards_placed: int
    wards_killed: int
    # Game progression
    champion_experience: int
    time_played: int
    total_time_spent_dead: int
    # Items
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    # Additional Combat Stats
    bounty_level: int
    killing_sprees: int
    largest_killing_spree: int
    largest_multi_kill: int
    longest_time_spent_living: int
    double_kills: int
    triple_kills: int
    quadra_kills: int
    penta_kills: int
    unreal_kills: int
    # Damage Breakdown
    damage_dealt_to_buildings: int
    damage_dealt_to_objectives: int
    damage_dealt_to_turrets: int
    damage_self_mitigated: int
    largest_critical_strike: int
    # Objective Stats
    inhibitor_kills: int
    inhibitor_takedowns: int
    inhibitors_lost: int
    nexus_kills: int
    nexus_lost: int
    nexus_takedowns: int
    turret_kills: int
    turret_takedowns: int
    turrets_lost: int
    # Additional Game Stats
    champion_transform: int
    consumables_purchased: int
    items_purchased: int
    neutral_minions_killed: int
    total_ally_jungle_minions_killed: int
    total_enemy_jungle_minions_killed: int
    total_time_cc_dealt: int
    total_units_healed: int
    # Team Stats
    first_blood_assist: bool
    first_blood_kill: bool
    first_tower_assist: bool
    first_tower_kill: bool
    game_ended_in_surrender: bool
    game_ended_in_early_surrender: bool
    team_early_surrendered: bool
    # Ability Usage
    spell1_casts: int
    spell2_casts: int
    spell3_casts: int
    spell4_casts: int
    summoner1_casts: int
    summoner2_casts: int
    summoner1_id: int
    summoner2_id: int
    # Additional Healing/Shielding Stats
    total_heal: int
    total_heals_on_teammates: int
    total_damage_shielded_on_teammates: int
    # Ping Stats
    all_in_pings: int
    assist_me_pings: int
    basic_pings: int
    command_pings: int
    danger_pings: int
    enemy_missing_pings: int
    enemy_vision_pings: int
    get_back_pings: int
    hold_pings: int
    need_vision_pings: int
    on_my_way_pings: int
    push_pings: int
    retreat_pings: int
    vision_cleared_pings: int
    # Player Info
    summoner_level: int
    riot_id_game_name: str
    riot_id_tagline: str
    profile_icon: int

@dataclass
class User:
    id: int
    username: str
    puuid: str
    riot_id_game_name: str
    riot_id_tagline: str
    guild_id: str
    active: bool
    last_game_played: Optional[str] = None

@dataclass
class Champion:
    id: int
    name: str
    title: str
    image_full: str
    image_sprite: str
    image_group: str
    tags: str  # Stored as comma-separated values
    partype: str  # Mana, Energy, etc.
    stats_hp: float
    stats_hpperlevel: float
    stats_mp: float
    stats_mpperlevel: float
    stats_movespeed: float
    stats_armor: float
    stats_armorperlevel: float
    stats_spellblock: float
    stats_spellblockperlevel: float
    stats_attackrange: float
    stats_hpregen: float
    stats_hpregenperlevel: float
    stats_mpregen: float
    stats_mpregenperlevel: float
    stats_crit: float
    stats_critperlevel: float
    stats_attackdamage: float
    stats_attackdamageperlevel: float
    stats_attackspeedperlevel: float
    stats_attackspeed: float

@dataclass
class PlayerStats:
    def __init__(self, champion_name: str, champion_games: int, winrate: float, avg_damage_per_minute: float,
                 average_kda: float, total_games_overall: int, unique_champions_played: int, unique_champ_ratio: float,
                 oldest_game: str, total_hours_played: float, total_triples: int, total_quadras: int, total_pentas: int,
                 total_pentas_overall: int, total_winrate: float, avg_time_dead_pct: float, avg_vision_score: float,
                 avg_kill_participation: float, avg_damage_taken_per_min: float, total_first_bloods: int,
                 total_objectives: int, avg_gold_per_min: float, max_killing_spree: int, max_kda: float,
                 max_killing_spree_champion: str, max_kda_champion: str, summoner_level: int, profile_icon: int,
                 avg_cs_per_min: float = 0.0):
        self.champion_name = champion_name
        self.champion_games = champion_games
        self.winrate = winrate
        self.avg_damage_per_minute = avg_damage_per_minute
        self.average_kda = average_kda
        self.total_games_overall = total_games_overall
        self.unique_champions_played = unique_champions_played
        self.unique_champ_ratio = unique_champ_ratio
        self.oldest_game = oldest_game
        self.total_hours_played = total_hours_played
        self.total_triples = total_triples
        self.total_quadras = total_quadras
        self.total_pentas = total_pentas
        self.total_pentas_overall = total_pentas_overall
        self.total_winrate = total_winrate
        self.avg_time_dead_pct = avg_time_dead_pct
        self.avg_vision_score = avg_vision_score
        self.avg_kill_participation = avg_kill_participation
        self.avg_damage_taken_per_min = avg_damage_taken_per_min
        self.total_first_bloods = total_first_bloods
        self.total_objectives = total_objectives
        self.avg_gold_per_min = avg_gold_per_min
        self.max_killing_spree = max_killing_spree
        self.max_kda = max_kda
        self.max_killing_spree_champion = max_killing_spree_champion
        self.max_kda_champion = max_kda_champion
        self.summoner_level = summoner_level
        self.profile_icon = profile_icon
        self.avg_cs_per_min = avg_cs_per_min

@dataclass
class PlayerFriendStats:
    teammate_name: str
    games_together: int
    wins_together: int
    win_rate: float 

@dataclass
class UserStats:
    riot_id_game_name: str
    riot_id_tagline: str
    total_hours_played: float
    total_hours_2024: float
    games_played: int
    avg_minutes_per_game: float
    first_game_date: str
    total_pentas: int
    winrate: float 