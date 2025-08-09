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
        if dt is not None:
            self.time_elapsed(dt)

    def _to_cell(self, pos: Vector2) -> Cell:
        cells_area_matrix = self._tic_tac_toe.config.cells_area_matrix
        value = list(filter(lambda key: pos.x in range(cells_area_matrix[key][0][0], cells_area_matrix[key][0][1]) and \
                    pos.y in range(cells_area_matrix[key][1][0], cells_area_matrix[key][1][1]), cells_area_matrix)).__getitem__(0)
        return Cell(value[0], value[1])

class TicTacToeEventHandler(EventHandler):
    def on_game_start(self, tic_tac_toe):
        pass

    def on_game_over(self, tic_tac_toe):
        pass

    def on_mark_placed(self, tic_tac_toe, cell: Cell):
        size = tic_tac_toe.size.x / tic_tac_toe.grid.dim
        if tic_tac_toe.place_mark(Mark(
            cell,
            Symbol.NOUGHT if self._tic_tac_toe.turn.is_nought else Symbol.CROSS,
            size,
            tic_tac_toe.config.cells_symbol_position.get((cell.x, cell.y))
        )):
            if tic_tac_toe.has_won(tic_tac_toe.turn):
                self.on_game_over(tic_tac_toe)
            tic_tac_toe.change_turn()
            tic_tac_toe.remove_random_mark()

    def on_time_elapsed(self, tic_tac_toe, dt):
        tic_tac_toe.update(dt)

class TicTacToeLocalController(TicTacToeInputHandler, TicTacToeEventHandler):
    def __init__(self, tic_tac_toe: TicTacToe):
        TicTacToeInputHandler.__init__(self, tic_tac_toe)
        TicTacToeEventHandler.__init__(self, tic_tac_toe)
