"""MongoDB collection name constants."""


class CollectionNames:
    users: str = "users"
    drivers: str = "drivers"
    teams: str = "teams"
    favourites: str = "favourites"
    predictions: str = "predictions"
    facts: str = "facts"
    head_to_head_votes: str = "head_to_head_votes"
    hot_takes: str = "hot_takes"


collections = CollectionNames()
