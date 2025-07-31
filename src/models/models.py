from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Match:
    match_id: str
    game_duration: int
    game_version: str
    game_mode: str
    game_type: str
    game_creation: str
    game_end: str
    # Additional InfoDto fields
    data_version: Optional[str] = None
    end_of_game_result: Optional[str] = None
    game_id: Optional[int] = None
    game_name: Optional[str] = None
    game_start_timestamp: Optional[int] = None
    game_end_timestamp: Optional[int] = None
    map_id: Optional[int] = None
    platform_id: Optional[str] = None
    queue_id: Optional[int] = None
    tournament_code: Optional[str] = None

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
    first_place: bool  # Added for Cherry/Arena mode
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
    # Missing ParticipantDto fields
    baron_kills: int = 0
    dragon_kills: int = 0
    eligible_for_progression: bool = False
    magic_damage_dealt: int = 0
    magic_damage_taken: int = 0
    physical_damage_dealt: int = 0
    physical_damage_taken: int = 0
    true_damage_dealt: int = 0
    true_damage_taken: int = 0
    objectives_stolen: int = 0
    objectives_stolen_assists: int = 0
    participant_id: int = 0
    placement: int = 0
    player_augment1: int = 0
    player_augment2: int = 0
    player_augment3: int = 0
    player_augment4: int = 0
    player_subteam_id: int = 0
    subteam_placement: int = 0
    summoner_id: Optional[str] = None
    time_ccing_others: int = 0
    detector_wards_placed: int = 0
    sight_wards_bought_in_game: int = 0
    vision_wards_bought_in_game: int = 0
    # Player scores from MissionsDto
    player_score0: int = 0
    player_score1: int = 0
    player_score2: int = 0
    player_score3: int = 0
    player_score4: int = 0
    player_score5: int = 0
    player_score6: int = 0
    player_score7: int = 0
    player_score8: int = 0
    player_score9: int = 0
    player_score10: int = 0
    player_score11: int = 0

@dataclass
class Team:
    match_id: str
    team_id: int
    win: bool

@dataclass
class Ban:
    id: int
    match_id: str
    team_id: int
    champion_id: int
    pick_turn: int

@dataclass
class Objective:
    id: int
    match_id: str
    team_id: int
    objective_type: str  # baron, dragon, tower, inhibitor, riftHerald, champion, horde
    first: bool
    kills: int

@dataclass
class Challenge:
    id: int
    match_id: str
    participant_id: int
    # Challenge fields from ChallengesDto
    assists_streak_count_12: int = 0
    baron_buff_gold_advantage_over_threshold: int = 0
    control_ward_time_coverage_in_river_or_enemy_half: float = 0.0
    earliest_baron: int = 0
    earliest_dragon_takedown: int = 0
    earliest_elder_dragon: int = 0
    early_laning_phase_gold_exp_advantage: int = 0
    faster_support_quest_completion: int = 0
    fastest_legendary: int = 0
    had_afk_teammate: int = 0
    highest_champion_damage: int = 0
    highest_crowd_control_score: int = 0
    highest_ward_kills: int = 0
    jungler_kills_early_jungle: int = 0
    kills_on_laners_early_jungle_as_jungler: int = 0
    laning_phase_gold_exp_advantage: int = 0
    legendary_count: int = 0
    max_cs_advantage_on_lane_opponent: float = 0.0
    max_level_lead_lane_opponent: int = 0
    most_wards_destroyed_one_sweeper: int = 0
    mythic_item_used: int = 0
    played_champ_select_position: int = 0
    solo_turrets_lategame: int = 0
    takedowns_first_25_minutes: int = 0
    teleport_takedowns: int = 0
    third_inhibitor_destroyed_time: int = 0
    three_wards_one_sweeper_count: int = 0
    vision_score_advantage_lane_opponent: float = 0.0
    infernal_scale_pickup: int = 0
    fist_bump_participation: int = 0
    void_monster_kill: int = 0
    ability_uses: int = 0
    aces_before_15_minutes: int = 0
    allied_jungle_monster_kills: float = 0.0
    baron_takedowns: int = 0
    blast_cone_opposite_opponent_count: int = 0
    bounty_gold: int = 0
    buffs_stolen: int = 0
    complete_support_quest_in_time: int = 0
    control_wards_placed: int = 0
    damage_per_minute: float = 0.0
    damage_taken_on_team_percentage: float = 0.0
    danced_with_rift_herald: int = 0
    deaths_by_enemy_champs: int = 0
    dodge_skill_shots_small_window: int = 0
    double_aces: int = 0
    dragon_takedowns: int = 0
    effective_heal_and_shielding: float = 0.0
    elder_dragon_kills_with_opposing_soul: int = 0
    elder_dragon_multikills: int = 0
    enemy_champion_immobilizations: int = 0
    enemy_jungle_monster_kills: float = 0.0
    epic_monster_kills_near_enemy_jungler: int = 0
    epic_monster_kills_within_30_seconds_of_spawn: int = 0
    epic_monster_steals: int = 0
    epic_monster_stolen_without_smite: int = 0
    first_turret_killed: int = 0
    first_turret_killed_time: float = 0.0
    flawless_aces: int = 0
    full_team_takedown: int = 0
    game_length: float = 0.0
    get_takedowns_in_all_lanes_early_jungle_as_laner: int = 0
    gold_per_minute: float = 0.0
    had_open_nexus: int = 0
    immobilize_and_kill_with_ally: int = 0
    initial_buff_count: int = 0
    initial_crab_count: int = 0
    jungle_cs_before_10_minutes: float = 0.0
    jungler_takedowns_near_damaged_epic_monster: int = 0
    kda: float = 0.0
    kill_after_hidden_with_ally: int = 0
    killed_champ_took_full_team_damage_survived: int = 0
    killing_sprees: int = 0
    kill_participation: float = 0.0
    kills_near_enemy_turret: int = 0
    kills_on_other_lanes_early_jungle_as_laner: int = 0
    kills_on_recently_healed_by_aram_pack: int = 0
    kills_under_own_turret: int = 0
    kills_with_help_from_epic_monster: int = 0
    knock_enemy_into_team_and_kill: int = 0
    k_turrets_destroyed_before_plates_fall: int = 0
    land_skill_shots_early_game: int = 0
    lane_minions_first_10_minutes: int = 0
    lost_an_inhibitor: int = 0
    max_kill_deficit: int = 0
    mejais_full_stack_in_time: int = 0
    more_enemy_jungle_than_opponent: float = 0.0
    multi_kill_one_spell: int = 0
    multikills: int = 0
    multikills_after_aggressive_flash: int = 0
    multi_turret_rift_herald_count: int = 0
    outer_turret_executes_before_10_minutes: int = 0
    outnumbered_kills: int = 0
    outnumbered_nexus_kill: int = 0
    perfect_dragon_souls_taken: int = 0
    perfect_game: int = 0
    pick_kill_with_ally: int = 0
    poro_explosions: int = 0
    quick_cleanse: int = 0
    quick_first_turret: int = 0
    quick_solo_kills: int = 0
    rift_herald_takedowns: int = 0
    save_ally_from_death: int = 0
    scuttle_crab_kills: int = 0
    shortest_time_to_ace_from_first_takedown: float = 0.0
    skillshots_dodged: int = 0
    skillshots_hit: int = 0
    snowballs_hit: int = 0
    solo_baron_kills: int = 0
    swarm_defeat_aatrox: int = 0
    swarm_defeat_briar: int = 0
    swarm_defeat_mini_bosses: int = 0
    swarm_evolve_weapon: int = 0
    swarm_have_3_passives: int = 0
    swarm_kill_enemy: int = 0
    swarm_pickup_gold: float = 0.0
    swarm_reach_level_50: int = 0
    swarm_survive_15_min: int = 0
    swarm_win_with_5_evolved_weapons: int = 0
    solo_kills: int = 0
    stealth_wards_placed: int = 0
    survived_single_digit_hp_count: int = 0
    survived_three_immobilizes_in_fight: int = 0
    takedown_on_first_turret: int = 0
    takedowns: int = 0
    takedowns_after_gaining_level_advantage: int = 0
    takedowns_before_jungle_minion_spawn: int = 0
    takedowns_first_x_minutes: int = 0
    takedowns_in_alcove: int = 0
    takedowns_in_enemy_fountain: int = 0
    team_baron_kills: int = 0
    team_damage_percentage: float = 0.0
    team_elder_dragon_kills: int = 0
    team_rift_herald_kills: int = 0
    took_large_damage_survived: int = 0
    turret_plates_taken: int = 0
    turrets_taken_with_rift_herald: int = 0
    turret_takedowns: int = 0
    twenty_minions_in_3_seconds_count: int = 0
    two_wards_one_sweeper_count: int = 0
    unseen_recalls: int = 0
    vision_score_per_minute: float = 0.0
    wards_guarded: int = 0
    ward_takedowns: int = 0
    ward_takedowns_before_20m: int = 0
    legendary_item_used: Optional[str] = None  # Comma-separated list

@dataclass
class Perk:
    id: int
    match_id: str
    participant_id: int
    stat_defense: int
    stat_flex: int
    stat_offense: int

@dataclass
class PerkStyle:
    id: int
    perk_id: int
    description: str
    style: int

@dataclass
class PerkSelection:
    id: int
    perk_style_id: int
    perk: int
    var1: int
    var2: int
    var3: int

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

@dataclass
class PendingMatch:
    match_id: str
    game_mode: str
    channel_id: int
    message_id: int
    attempts: int
    created_at: str
    last_attempt: str 