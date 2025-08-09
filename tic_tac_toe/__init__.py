import pygame
from .model.game import *
from .log import logger, logging
from .utils import Settings
from .view import ShowNothingTicTacToeView
from .controller.mark_utils import *

class TicTacToeGame:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.tic_tac_toe = TicTacToe(
            size=self.settings.size,
            dim=self.settings.dim
        )
        self.dt = None
        self.mark_utils = MarkUtils()
        self.view = self.create_view() if self.settings.gui else ShowNothingTicTacToeView()
        self.clock = pygame.time.Clock()
        self.running = True
        if self.settings.debug:
            logger.setLevel(logging.DEBUG)

    def create_view(self):
        from .view import ScreenTicTacToeView
        return ScreenTicTacToeView(self.settings.size, self.mark_utils)

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
                self.view.render(
                    self.tic_tac_toe.config.cell_width_size,
                    self.tic_tac_toe.config.cell_height_size,
                    self.settings.dim,
                    self.mark_utils.decompose(self.tic_tac_toe.marks)
                )
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
