"""MongoDB collection name constants."""


class CollectionNames:
    users: str = "users"
    drivers: str = "drivers"
    teams: str = "teams"
    circuits: str = "circuits"
    seasons: str = "seasons"
    races: str = "races"
    race_results: str = "race_results"
    sprint_results: str = "sprint_results"
    constructor_results: str = "constructor_results"
    constructor_standings: str = "constructor_standings"
    statuses: str = "statuses"
    lap_time_summaries: str = "lap_time_summaries"
    driver_season_stats: str = "driver_season_stats"
    constructor_season_stats: str = "constructor_season_stats"
    favourites: str = "favourites"
    predictions: str = "predictions"
    facts: str = "facts"
    head_to_head_votes: str = "head_to_head_votes"
    hot_takes: str = "hot_takes"
    refresh_tokens: str = "refresh_tokens"
    token_blacklist: str = "token_blacklist"
    audit_logs: str = "audit_logs"


collections = CollectionNames()
