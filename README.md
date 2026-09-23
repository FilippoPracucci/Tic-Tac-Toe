# Tic-Tac-Toe

This game is a variant of the classic [Tic-Tac-Toe](https://en.wikipedia.org/wiki/Tic-tac-toe), in which 2 players can play one against the other, placing alternately a mark per turn in the spaces of a 3x3 grid; the player who succeeds in placing three of his marks in a vertical, horizontal or diagonal row first is the winner.

## Variation

The variation consists on the fact that every player will never have on the grid more than 3 marks simultaneously, which means that starting after placing the third personal mark, at each turn a random mark of the active player will be removed, before he can put the next one (so his fourth on the grid).

## How to run

- Starting from the root of the project, it is possible to run the system by means of **Poetry**, so first of all
install it;
- install the project dependencies by executing:
```bash
poetry install
```

- run the **central server** by executing:
```bash
poetry run lobby-coordinator
```

- run the **clients** by executing on different terminals:
```bash
poetry run terminal
```

To run the game locally execute:
```bash
poetry run local
```

### Alternative

It is possible to run the system directly from the CLI, specifying some arguments, which can be listed by executing:
```bash
  poetry run python -m tic_tac_toe --help
```

The arguments can be added both to the commands to run the central server and the clients, which are respectevely:
```bash
  poetry run python -m tic_tac_toe -m centralised -r coordinator
```

```bash
  poetry run python -m tic_tac_toe -m centralised -r terminal
```

To run the game locally:
```bash
  poetry run python -m tic_tac_toe -m local
```

## User guide

In the game interface, it is displayed the state of the game in the grid, and the active
player can place a mark in an empty cell by clicking on it with the **left mouse button**.

In any moment of the game, the player can leave it by pressing the **Esc** key, which
will bring all the players of the game back to the lobby menu.

In addition, the players can chat with each other by typing a message in the CLI and
pressing **Enter** to send it, also the messages received by the other player will be displayed
there.

Finally, every message that the game server or the central server wants the client to
display, will be printed in the CLI.
