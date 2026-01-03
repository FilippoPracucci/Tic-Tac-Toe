import argparse
from argparse import ArgumentParser
from typing import Any
import tic_tac_toe
from tic_tac_toe.model.game_object import Symbol
from tic_tac_toe.utils import Settings

def arg_parser() -> ArgumentParser:
    ap = ArgumentParser()
    ap.prog = "python -m " + tic_tac_toe.__name__
    mode = ap.add_argument_group("mode")
    mode.add_argument("--mode", '-m', choices=['local', 'centralised'],
                      help="Run the game in local or centralised mode")
    mode.add_argument("--role", '-r', required=False, choices=['coordinator', 'terminal'],
                      help="Run the game with a central coordinator, in either coordinator or terminal role")
    networking = ap.add_argument_group("networking")
    networking.add_argument("--host", '-H', help="Host to connect to", type=str, default="localhost")
    networking.add_argument("--port", '-p', help="Port to connect to", type=int, default=None)
    game = ap.add_argument_group("game")
    game.add_argument("--create", '-c', help="Create a new game", action="store_true", default=False)
    game.add_argument("--join-game", '-j', help="Join an existing game by its ID", type=int, dest="game_id", default=None)
    game.add_argument("--symbol", '-s', choices=[symbol.name.lower() for symbol in Symbol.values()],
                      help="Symbol to play with", default=Symbol.CROSS, dest="symbol")
    game.add_argument("--debug", '-d', help="Enable debug mode", action="store_true", default=False)
    game.add_argument("--size", '-S', help="Size of the game window", type=int, nargs=2, default=[900, 600])
    game.add_argument("--fps", '-f', help="Frames per second", type=int, default=60)
    game.add_argument("--no-gui", help="Disable GUI", action="store_true", default=False)
    return ap

def args_to_settings(args: Any) -> Settings:
    settings = Settings(size=tuple(args.size), debug=args.debug)
    settings.host = args.host
    settings.port = args.port
    settings.fps = args.fps
    settings.gui = not args.no_gui
    return settings


parser = arg_parser()
args = parser.parse_args()
settings = args_to_settings(args)

if args.mode == 'local':
    tic_tac_toe.main(settings)
    exit(0)
if args.mode == 'centralised':
    from tic_tac_toe.remote.centralised import main_lobby, main_terminal
    if args.role == 'coordinator':
        main_lobby(settings)
        exit(0)
    if args.role == 'terminal':
        main_terminal(
            symbol=Symbol[str(args.symbol).upper()],
            creation=args.create,
            game_id=args.game_id,
            settings=settings
        )
        exit(0)
    print(f"Invalid role: {args.role}. Must be either 'coordinator' or 'terminal'")
parser.print_help()
exit(1)
