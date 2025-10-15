import argparse
import tic_tac_toe

def arg_parser():
    ap = argparse.ArgumentParser()
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
    game.add_argument("--debug", '-d', help="Enable debug mode", action="store_true", default=False)
    game.add_argument("--size", '-S', help="Size of the game window", type=int, nargs=2, default=[900, 600])
    game.add_argument("--fps", '-f', help="Frames per second", type=int, default=60)
    game.add_argument("--no-gui", help="Disable GUI", action="store_true", default=False)
    return ap

def args_to_settings(args):
    settings = tic_tac_toe.Settings(size=tuple(args.size), debug=args.debug)
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
    import tic_tac_toe.remote.centralised
    if args.role == 'coordinator':
        tic_tac_toe.remote.centralised.main_coordinator(settings)
        exit(0)
    if args.role == 'terminal':
        tic_tac_toe.remote.centralised.main_terminal(settings)
        exit(0)
    print(f"Invalid role: {args.role}. Must be either 'coordinator' or 'terminal'")
parser.print_help()
exit(1)
