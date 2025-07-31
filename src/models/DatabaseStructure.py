# data base structure
""" CREATE TABLE "users" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            puuid TEXT,
            riot_id_game_name TEXT,
            riot_id_tagline TEXT,
            last_game_played TEXT,
            guild_id TEXT,
            active BOOLEAN
        );

CREATE TABLE champions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            title TEXT,
            image_full TEXT,
            image_sprite TEXT,
            image_group TEXT,
            tags TEXT,  -- Stored as comma-separated values
            partype TEXT,  -- Mana, Energy, etc.
            stats_hp REAL,
            stats_hpperlevel REAL,
            stats_mp REAL,
            stats_mpperlevel REAL,
            stats_movespeed REAL,
            stats_armor REAL,
            stats_armorperlevel REAL,
            stats_spellblock REAL,
            stats_spellblockperlevel REAL,
            stats_attackrange REAL,
            stats_hpregen REAL,
            stats_hpregenperlevel REAL,
            stats_mpregen REAL,
            stats_mpregenperlevel REAL,
            stats_crit REAL,
            stats_critperlevel REAL,
            stats_attackdamage REAL,
            stats_attackdamageperlevel REAL,
            stats_attackspeedperlevel REAL,
            stats_attackspeed REAL
        )

CREATE TABLE matches (
        match_id TEXT PRIMARY KEY,
        game_duration INTEGER,
        game_version TEXT,
        game_mode TEXT,
        game_type TEXT,
        game_creation TIMESTAMP,
        game_end TIMESTAMP,
        -- Additional InfoDto fields
        data_version TEXT,
        end_of_game_result TEXT,
        game_id INTEGER,
        game_name TEXT,
        game_start_timestamp INTEGER,
        game_end_timestamp INTEGER,
        map_id INTEGER,
        platform_id TEXT,
        queue_id INTEGER,
        tournament_code TEXT
    )

CREATE TABLE participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        puuid TEXT,
        summoner_name TEXT,
        champion_name TEXT,
        champion_id INTEGER,
        team_id INTEGER,
        team_position TEXT,
        individual_position TEXT,
        lane TEXT,
        role TEXT,
        wins BOOLEAN,
        first_place BOOLEAN,  -- Added for Cherry/Arena mode
        
        -- Combat stats
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        kda REAL,
        kill_participation REAL,
        champion_level INTEGER,
        vision_score INTEGER,
        
        -- Damage stats
        total_damage_dealt INTEGER,
        total_damage_to_champions INTEGER,
        physical_damage_to_champions INTEGER,
        magic_damage_to_champions INTEGER,
        true_damage_to_champions INTEGER,
        total_damage_taken INTEGER,
        
        -- Economy stats
        gold_earned INTEGER,
        gold_spent INTEGER,
        total_minions_killed INTEGER,
        
        -- Vision stats
        vision_wards_bought INTEGER,
        sight_wards_bought INTEGER,
        wards_placed INTEGER,
        wards_killed INTEGER,
        
        -- Game progression
        champion_experience INTEGER,
        time_played INTEGER,
        total_time_spent_dead INTEGER,
        
        -- Items
        item0 INTEGER,
        item1 INTEGER,
        item2 INTEGER,
        item3 INTEGER,
        item4 INTEGER,
        item5 INTEGER,
        item6 INTEGER,
                   
        -- Additional Combat Stats
        bounty_level INTEGER,
        killing_sprees INTEGER,
        largest_killing_spree INTEGER,
        largest_multi_kill INTEGER,
        longest_time_spent_living INTEGER,
        double_kills INTEGER,
        triple_kills INTEGER,
        quadra_kills INTEGER,
        penta_kills INTEGER,
        unreal_kills INTEGER,
        
        -- Damage Breakdown
        damage_dealt_to_buildings INTEGER,
        damage_dealt_to_objectives INTEGER,
        damage_dealt_to_turrets INTEGER,
        damage_self_mitigated INTEGER,
        largest_critical_strike INTEGER,
        
        -- Objective Stats
        inhibitor_kills INTEGER,
        inhibitor_takedowns INTEGER,
        inhibitors_lost INTEGER,
        nexus_kills INTEGER,
        nexus_lost INTEGER,
        nexus_takedowns INTEGER,
        turret_kills INTEGER,
        turret_takedowns INTEGER,
        turrets_lost INTEGER,
        
        -- Additional Game Stats
        champion_transform INTEGER,
        consumables_purchased INTEGER,
        items_purchased INTEGER,
        neutral_minions_killed INTEGER,
        total_ally_jungle_minions_killed INTEGER,
        total_enemy_jungle_minions_killed INTEGER,
        total_time_cc_dealt INTEGER,
        total_units_healed INTEGER,
        
        -- Team Stats
        first_blood_assist BOOLEAN,
        first_blood_kill BOOLEAN,
        first_tower_assist BOOLEAN,
        first_tower_kill BOOLEAN,
        game_ended_in_surrender BOOLEAN,
        game_ended_in_early_surrender BOOLEAN,
        team_early_surrendered BOOLEAN,
        
        -- Ability Usage
        spell1_casts INTEGER,
        spell2_casts INTEGER,
        spell3_casts INTEGER,
        spell4_casts INTEGER,
        summoner1_casts INTEGER,
        summoner2_casts INTEGER,
        summoner1_id INTEGER,
        summoner2_id INTEGER,
        
        -- Additional Healing/Shielding Stats
        total_heal INTEGER,
        total_heals_on_teammates INTEGER,
        total_damage_shielded_on_teammates INTEGER,
        
        -- Ping Stats
        all_in_pings INTEGER,
        assist_me_pings INTEGER,
        basic_pings INTEGER,
        command_pings INTEGER,
        danger_pings INTEGER,
        enemy_missing_pings INTEGER,
        enemy_vision_pings INTEGER,
        get_back_pings INTEGER,
        hold_pings INTEGER,
        need_vision_pings INTEGER,
        on_my_way_pings INTEGER,
        push_pings INTEGER,
        retreat_pings INTEGER,
        vision_cleared_pings INTEGER,
        
        -- Player Info
        summoner_level INTEGER,
        riot_id_game_name TEXT,
        riot_id_tagline TEXT,
        profile_icon INTEGER,
        
        -- Missing ParticipantDto fields
        baron_kills INTEGER,
        dragon_kills INTEGER,
        eligible_for_progression BOOLEAN,
        magic_damage_dealt INTEGER,
        magic_damage_taken INTEGER,
        physical_damage_dealt INTEGER,
        physical_damage_taken INTEGER,
        true_damage_dealt INTEGER,
        true_damage_taken INTEGER,
        objectives_stolen INTEGER,
        objectives_stolen_assists INTEGER,
        participant_id INTEGER,
        placement INTEGER,
        player_augment1 INTEGER,
        player_augment2 INTEGER,
        player_augment3 INTEGER,
        player_augment4 INTEGER,
        player_subteam_id INTEGER,
        subteam_placement INTEGER,
        summoner_id TEXT,
        time_ccing_others INTEGER,
        detector_wards_placed INTEGER,
        sight_wards_bought_in_game INTEGER,
        vision_wards_bought_in_game INTEGER,
        
        -- Player scores from MissionsDto
        player_score0 INTEGER,
        player_score1 INTEGER,
        player_score2 INTEGER,
        player_score3 INTEGER,
        player_score4 INTEGER,
        player_score5 INTEGER,
        player_score6 INTEGER,
        player_score7 INTEGER,
        player_score8 INTEGER,
        player_score9 INTEGER,
        player_score10 INTEGER,
        player_score11 INTEGER,
        
        FOREIGN KEY (match_id) REFERENCES matches (match_id),
        UNIQUE(match_id, puuid)
    );

CREATE TABLE teams (
        match_id TEXT,
        team_id INTEGER,
        win BOOLEAN,
        PRIMARY KEY (match_id, team_id),
        FOREIGN KEY (match_id) REFERENCES matches (match_id)
    );

CREATE TABLE bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        team_id INTEGER,
        champion_id INTEGER,
        pick_turn INTEGER,
        FOREIGN KEY (match_id) REFERENCES matches (match_id)
    );

CREATE TABLE objectives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        team_id INTEGER,
        objective_type TEXT, -- baron, dragon, tower, inhibitor, riftHerald, champion, horde
        first BOOLEAN,
        kills INTEGER,
        FOREIGN KEY (match_id) REFERENCES matches (match_id)
    );

CREATE TABLE challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        participant_id INTEGER,
        -- Challenge fields from ChallengesDto
        assists_streak_count_12 INTEGER,
        baron_buff_gold_advantage_over_threshold INTEGER,
        control_ward_time_coverage_in_river_or_enemy_half REAL,
        earliest_baron INTEGER,
        earliest_dragon_takedown INTEGER,
        earliest_elder_dragon INTEGER,
        early_laning_phase_gold_exp_advantage INTEGER,
        faster_support_quest_completion INTEGER,
        fastest_legendary INTEGER,
        had_afk_teammate INTEGER,
        highest_champion_damage INTEGER,
        highest_crowd_control_score INTEGER,
        highest_ward_kills INTEGER,
        jungler_kills_early_jungle INTEGER,
        kills_on_laners_early_jungle_as_jungler INTEGER,
        laning_phase_gold_exp_advantage INTEGER,
        legendary_count INTEGER,
        max_cs_advantage_on_lane_opponent REAL,
        max_level_lead_lane_opponent INTEGER,
        most_wards_destroyed_one_sweeper INTEGER,
        mythic_item_used INTEGER,
        played_champ_select_position INTEGER,
        solo_turrets_lategame INTEGER,
        takedowns_first_25_minutes INTEGER,
        teleport_takedowns INTEGER,
        third_inhibitor_destroyed_time INTEGER,
        three_wards_one_sweeper_count INTEGER,
        vision_score_advantage_lane_opponent REAL,
        infernal_scale_pickup INTEGER,
        fist_bump_participation INTEGER,
        void_monster_kill INTEGER,
        ability_uses INTEGER,
        aces_before_15_minutes INTEGER,
        allied_jungle_monster_kills REAL,
        baron_takedowns INTEGER,
        blast_cone_opposite_opponent_count INTEGER,
        bounty_gold INTEGER,
        buffs_stolen INTEGER,
        complete_support_quest_in_time INTEGER,
        control_wards_placed INTEGER,
        damage_per_minute REAL,
        damage_taken_on_team_percentage REAL,
        danced_with_rift_herald INTEGER,
        deaths_by_enemy_champs INTEGER,
        dodge_skill_shots_small_window INTEGER,
        double_aces INTEGER,
        dragon_takedowns INTEGER,
        effective_heal_and_shielding REAL,
        elder_dragon_kills_with_opposing_soul INTEGER,
        elder_dragon_multikills INTEGER,
        enemy_champion_immobilizations INTEGER,
        enemy_jungle_monster_kills REAL,
        epic_monster_kills_near_enemy_jungler INTEGER,
        epic_monster_kills_within_30_seconds_of_spawn INTEGER,
        epic_monster_steals INTEGER,
        epic_monster_stolen_without_smite INTEGER,
        first_turret_killed INTEGER,
        first_turret_killed_time REAL,
        flawless_aces INTEGER,
        full_team_takedown INTEGER,
        game_length REAL,
        get_takedowns_in_all_lanes_early_jungle_as_laner INTEGER,
        gold_per_minute REAL,
        had_open_nexus INTEGER,
        immobilize_and_kill_with_ally INTEGER,
        initial_buff_count INTEGER,
        initial_crab_count INTEGER,
        jungle_cs_before_10_minutes REAL,
        jungler_takedowns_near_damaged_epic_monster INTEGER,
        kda REAL,
        kill_after_hidden_with_ally INTEGER,
        killed_champ_took_full_team_damage_survived INTEGER,
        killing_sprees INTEGER,
        kill_participation REAL,
        kills_near_enemy_turret INTEGER,
        kills_on_other_lanes_early_jungle_as_laner INTEGER,
        kills_on_recently_healed_by_aram_pack INTEGER,
        kills_under_own_turret INTEGER,
        kills_with_help_from_epic_monster INTEGER,
        knock_enemy_into_team_and_kill INTEGER,
        k_turrets_destroyed_before_plates_fall INTEGER,
        land_skill_shots_early_game INTEGER,
        lane_minions_first_10_minutes INTEGER,
        lost_an_inhibitor INTEGER,
        max_kill_deficit INTEGER,
        mejais_full_stack_in_time INTEGER,
        more_enemy_jungle_than_opponent REAL,
        multi_kill_one_spell INTEGER,
        multikills INTEGER,
        multikills_after_aggressive_flash INTEGER,
        multi_turret_rift_herald_count INTEGER,
        outer_turret_executes_before_10_minutes INTEGER,
        outnumbered_kills INTEGER,
        outnumbered_nexus_kill INTEGER,
        perfect_dragon_souls_taken INTEGER,
        perfect_game INTEGER,
        pick_kill_with_ally INTEGER,
        poro_explosions INTEGER,
        quick_cleanse INTEGER,
        quick_first_turret INTEGER,
        quick_solo_kills INTEGER,
        rift_herald_takedowns INTEGER,
        save_ally_from_death INTEGER,
        scuttle_crab_kills INTEGER,
        shortest_time_to_ace_from_first_takedown REAL,
        skillshots_dodged INTEGER,
        skillshots_hit INTEGER,
        snowballs_hit INTEGER,
        solo_baron_kills INTEGER,
        swarm_defeat_aatrox INTEGER,
        swarm_defeat_briar INTEGER,
        swarm_defeat_mini_bosses INTEGER,
        swarm_evolve_weapon INTEGER,
        swarm_have_3_passives INTEGER,
        swarm_kill_enemy INTEGER,
        swarm_pickup_gold REAL,
        swarm_reach_level_50 INTEGER,
        swarm_survive_15_min INTEGER,
        swarm_win_with_5_evolved_weapons INTEGER,
        solo_kills INTEGER,
        stealth_wards_placed INTEGER,
        survived_single_digit_hp_count INTEGER,
        survived_three_immobilizes_in_fight INTEGER,
        takedown_on_first_turret INTEGER,
        takedowns INTEGER,
        takedowns_after_gaining_level_advantage INTEGER,
        takedowns_before_jungle_minion_spawn INTEGER,
        takedowns_first_x_minutes INTEGER,
        takedowns_in_alcove INTEGER,
        takedowns_in_enemy_fountain INTEGER,
        team_baron_kills INTEGER,
        team_damage_percentage REAL,
        team_elder_dragon_kills INTEGER,
        team_rift_herald_kills INTEGER,
        took_large_damage_survived INTEGER,
        turret_plates_taken INTEGER,
        turrets_taken_with_rift_herald INTEGER,
        turret_takedowns INTEGER,
        twenty_minions_in_3_seconds_count INTEGER,
        two_wards_one_sweeper_count INTEGER,
        unseen_recalls INTEGER,
        vision_score_per_minute REAL,
        wards_guarded INTEGER,
        ward_takedowns INTEGER,
        ward_takedowns_before_20m INTEGER,
        -- Legendary item used list stored as comma-separated values
        legendary_item_used TEXT,
        
        FOREIGN KEY (match_id) REFERENCES matches (match_id)
    );

CREATE TABLE perks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        participant_id INTEGER,
        -- Stat perks
        stat_defense INTEGER,
        stat_flex INTEGER,
        stat_offense INTEGER,
        
        FOREIGN KEY (match_id) REFERENCES matches (match_id)
    );

CREATE TABLE perk_styles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        perk_id INTEGER,
        description TEXT,
        style INTEGER,
        
        FOREIGN KEY (perk_id) REFERENCES perks (id)
    );

CREATE TABLE perk_selections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        perk_style_id INTEGER,
        perk INTEGER,
        var1 INTEGER,
        var2 INTEGER,
        var3 INTEGER,
        
        FOREIGN KEY (perk_style_id) REFERENCES perk_styles (id)
    );

CREATE TABLE pending_matches (
    match_id TEXT PRIMARY KEY,
    game_mode TEXT NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); """
