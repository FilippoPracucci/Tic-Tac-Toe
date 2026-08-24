from enum import Enum

class Config(Enum):
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 12345
    GAME_IDS_FILE = "games.json"

class CoordinationMessageType(Enum):
    GAME_IDS = "game_ids"
    COORDINATOR = "coordinator"
    CONNECTION = "connection"
    ERROR = "error"
