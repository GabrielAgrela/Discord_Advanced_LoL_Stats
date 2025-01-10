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
        game_end TIMESTAMP
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
        
        FOREIGN KEY (match_id) REFERENCES matches (match_id),
        UNIQUE(match_id, puuid)
        
        FOREIGN KEY (match_id) REFERENCES matches (match_id),
        UNIQUE(match_id, puuid)
    ) """
