from enum import Enum

class Config(Enum):
    """Enumeration of configuration parameters for a centralised game in remote mode."""

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 12345
    GAME_IDS_FILE = "games.json"

class CoordinationMessageType(Enum):
    """Enumeration of message types used for coordination in a centralised game in remote mode."""

    GAME_IDS = "game_ids"
    COORDINATOR = "coordinator"
    CONNECTION = "connection"
    ERROR = "error"
