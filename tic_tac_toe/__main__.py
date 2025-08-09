import argparse
import tic_tac_toe

def arg_parser():
    ap = argparse.ArgumentParser()
    ap.prog = "python -m tic-tac-toe"
    game = ap.add_argument_group("game")
    game.add_argument("--debug", '-d', help="Enable debug mode", action="store_true", default=False)
    game.add_argument("--size", '-S', help="Size of the game window", type=int, nargs=2, default=[900, 600])
    game.add_argument("--fps", '-f', help="Frames per second", type=int, default=60)
    game.add_argument("--no-gui", help="Disable GUI", action="store_true", default=False)
    return ap

def args_to_settings(args):
    settings = tic_tac_toe.Settings(size=tuple(args.size), debug=args.debug)
    settings.gui = not args.no_gui
    return settings


parser = arg_parser()
args = parser.parse_args()
settings = args_to_settings(args)

tic_tac_toe.main(settings)
exit(0)