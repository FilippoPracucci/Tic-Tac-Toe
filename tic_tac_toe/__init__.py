import pygame
from .model import *
from .log import logger, logging
from .utils import Settings
from .view import ShowNothingTicTacToeView
from .controller.mark_utils import *

class TicTacToeGame:
    def __init__(self, settings: Settings=None):
        self.settings = settings or Settings()
        self.tic_tac_toe = TicTacToe(
            size=self.settings.size,
            dim=self.settings.dim
        )
        self.dt = None
        self.mark_utils = MarkUtils()
        self.view = self.create_view() if self.settings.gui else ShowNothingTicTacToeView(self.tic_tac_toe)
        self.clock = pygame.time.Clock()
        self.running = True
        self.controller = self.create_controller()
        if self.settings.debug:
            logger.setLevel(logging.DEBUG)

    def create_controller(game):
        from .controller.local import TicTacToeLocalController

        class Controller(TicTacToeLocalController):
            def __init__(self):
                super().__init__(game.tic_tac_toe)

            def on_game_over(this, _):
                print(f"Player '{game.tic_tac_toe.turn.value}' has won!")
                game.stop()

        return Controller()

    def create_view(self):
        from .view import ScreenTicTacToeView
        return ScreenTicTacToeView(self.tic_tac_toe)

    def before_run(self):
        pygame.init()

    def after_run(self):
        pygame.quit()

    def at_each_run(self):
        if self.settings.gui:
            pygame.display.flip()

    def run(self):
        try:
            self.dt = 0
            self.before_run()
            while self.running:
                if self.tic_tac_toe.has_won(self.tic_tac_toe.turn):
                    self.stop()
                self.controller.handle_inputs(self.dt)
                self.controller.handle_events()
                self.view.render()
                self.at_each_run()
                self.dt = self.clock.tick(self.settings.fps) / 1000
        finally:
            self.after_run()

    def stop(self):
        self.running = False


def main(settings = None):
    if settings is None:
        settings = Settings()
    TicTacToeGame(settings).run()
