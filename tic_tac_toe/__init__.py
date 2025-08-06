from .model.game import *
import pygame
from .log import logger, logging
from typing import Optional

@dataclass
class Settings:
    debug: bool = False
    size: tuple = (600, 600)
    fps: int = 60
    host: Optional[str] = None
    port: Optional[int] = None
    gui: bool = True
    dim: int = 3

class TicTacToeGame:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.tic_tac_toe = TicTacToe(
            size=self.settings.size,
            dim=self.settings.dim
        )
        self.running = True
        if self.settings.debug:
            logger.setLevel(logging.DEBUG)

    def before_run(self):
        pygame.init()

    def after_run(self):
        pygame.quit()

    def at_each_run(self):
        if self.settings.gui:
            pygame.display.flip()

    def run(self):
        try:
            self.before_run()
            while self.running:
                if self.tic_tac_toe.has_won(self.tic_tac_toe.turn):
                    print(f"Player '{self.tic_tac_toe.turn.value}' has won!")
                    self.stop()
                self.at_each_run()
        finally:
            self.after_run()

    def stop(self):
        self.running = False


def main(settings = None):
    if settings is None:
        settings = Settings()
    TicTacToeGame(settings).run()
