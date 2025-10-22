from tic_tac_toe.controller import *

class TicTacToeInputHandler(InputHandler):
    def __init__(self, tic_tac_toe: TicTacToe):
        self._tic_tac_toe = tic_tac_toe
        self._command = ActionMap(PlayerAction.PLACE_MARK)

    def mouse_clicked(self):
        pos = self._command.click().__getattribute__("click_point")
        self.post_event(ControlEvent.MARK_PLACED, cell=self._to_cell(pos))
    
    def handle_inputs(self, dt=None):
        for event in pygame.event.get(self.INPUT_EVENTS):
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_clicked()
            elif event.type in [pygame.KEYDOWN, pygame.KEYUP]:
                self.post_event(ControlEvent.PLAYER_LEAVE)
        if dt is not None:
            self.time_elapsed(dt)

    def _to_cell(self, pos: Vector2) -> Cell:
        cells_area_matrix = self._tic_tac_toe.config.cells_area_matrix
        value = list(filter(lambda key: pos.x in range(cells_area_matrix[key][0][0], cells_area_matrix[key][0][1]) and \
                    pos.y in range(cells_area_matrix[key][1][0], cells_area_matrix[key][1][1]), cells_area_matrix)).__getitem__(0)
        return Cell(value[0], value[1])

class TicTacToeEventHandler(EventHandler):
    def on_player_join(self, tic_tac_toe: TicTacToe):
        if len(list(filter(lambda s: s == Symbol.CROSS, map(lambda p: p.symbol, tic_tac_toe.players)))) == 0:
            symbol = Symbol.CROSS
        else:
            symbol = Symbol.NOUGHT
        tic_tac_toe.add_player(Player(symbol))

    def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
        self.on_game_over(tic_tac_toe)

    def on_game_start(self, tic_tac_toe: TicTacToe):
        pass

    def on_game_over(self, tic_tac_toe: TicTacToe):
        pass

    def on_mark_placed(self, tic_tac_toe, cell: Cell):
        tic_tac_toe.place_mark(Mark(
            cell=cell,
            symbol=self._tic_tac_toe.turn,
            size=(tic_tac_toe.size / tic_tac_toe.grid.dim),
            position=tic_tac_toe.config.cells_symbol_position.get((cell.x, cell.y))
        ))
        if tic_tac_toe.end_turn():
            self.on_game_over(tic_tac_toe)

    def on_time_elapsed(self, tic_tac_toe, dt):
        tic_tac_toe.update(dt)

class TicTacToeLocalController(TicTacToeInputHandler, TicTacToeEventHandler):
    def __init__(self, tic_tac_toe: TicTacToe):
        TicTacToeInputHandler.__init__(self, tic_tac_toe)
        TicTacToeEventHandler.__init__(self, tic_tac_toe)
