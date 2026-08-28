import pygame
from .model import *
from .log import logger, logging
from .utils import Settings
from .view import ShowNothingTicTacToeView
from typing import List

class TicTacToeGame:
    """Manage a Tic-Tac-Toe game session.

    :param settings: Optional game settings.
    :param players: List of game's players.
    """

    def __init__(self, settings: Settings = None, players: List[Player] = []):
        self.settings = settings or Settings()
        self.logger = logger("TicTacToeGame")
        self.tic_tac_toe = TicTacToe(
            size=self.settings.size,
            dim=self.settings.dim,
            players=players
        )
        self.dt = None
        self._turn: Player = None
        self.view = self.create_view() if self.settings.gui else ShowNothingTicTacToeView(self.tic_tac_toe)
        self.clock = pygame.time.Clock()
        self.running = True
        self.controller = self.create_controller()
        if self.settings.debug:
            self.logger.setLevel(logging.INFO)

    @property
    def turn(self) -> Player:
        """Return the active player.

        :return: The current player.
        """
        return self._turn

    @turn.setter
    def turn(self, player: Player) -> None:
        """Set the active player.

        :param player: The new active player.
        :raises AssertionError: If the given player is not an instance of :class:`Player`.
        """
        assert isinstance(player, Player), f"Invalid symbol for a player: {player.symbol}"
        self._turn = player

    def create_controller(game: 'TicTacToeGame'):
        """Create the local controller bound to the current game instance.

        :param game: The game instance the controller should interact with.
        :return: A configured controller object for local gameplay.
        """
        from .controller.local import TicTacToeLocalController

        class Controller(TicTacToeLocalController):
            def __init__(self):
                super().__init__(game.tic_tac_toe)

            def on_player_join(this, tic_tac_toe: TicTacToe, symbol: Symbol, **kwargs):
                super().on_player_join(tic_tac_toe, symbol, **kwargs)
                if not game.turn:
                    game.turn = tic_tac_toe.get_turn_player()

            def on_change_turn(this, _):
                super().on_change_turn(game.tic_tac_toe)
                game.turn = game.tic_tac_toe.get_turn_player()

            def on_game_over(this, tic_tac_toe: TicTacToe, symbol: Symbol):
                super().on_game_over(tic_tac_toe, symbol)
                game.stop()

        return Controller()

    def create_view(self, title: str = "GAME"):
        """Build the view used to render the board.

        :param title: Title of the window.
        :return: The view instance created.
        """
        from .view import ScreenTicTacToeView
        return ScreenTicTacToeView(self.tic_tac_toe, title)

    def before_run(self) -> None:
        """Operations to perform before the game loop starts."""
        pygame.init()

    def after_run(self) -> None:
        """Operations to perform after the game loop stops."""
        pygame.quit()

    def at_each_run(self) -> None:
        """Operations to perform on each game loop iteration."""
        if self.settings.gui:
            pygame.display.flip()

    def run(self) -> None:
        """The game loop."""
        try:
            self.dt = 0
            self.before_run()
            while self.running:
                self.controller.handle_inputs(self.dt)
                self.controller.handle_events()
                self.view.render()
                self.at_each_run()
                self.dt = self.clock.tick(self.settings.fps) / 1000
        finally:
            self.after_run()

    def stop(self) -> None:
        """Stop the game loop."""
        self.running = False


def main(settings: Settings = None):
    """Create and run a Tic-Tac-Toe game, after the players creation and using the provided settings.

    :param settings: Optional game settings.
    """
    if settings is None:
        settings = Settings()
    players = [Player(symbol) for symbol in Symbol.values()]
    TicTacToeGame(settings, players).run()
