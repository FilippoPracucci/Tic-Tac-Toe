from enum import Enum

class Config(Enum):
    """Enumeration of configuration parameters for a centralised game in remote mode."""

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 12345
    JOINABLE_GAMES_FILE = "joinable_games.json"

class CoordinationMessageType(Enum):
    """Enumeration of message types used for coordination in a centralised game in remote mode."""

    JOINABLE_GAMES = "joinable_games"
    COORDINATOR = "coordinator"
    CONNECTION = "connection"
    ERROR = "error"
