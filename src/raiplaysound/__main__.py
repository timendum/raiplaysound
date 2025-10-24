from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace


def handle_single(args: "Namespace") -> None:
    from raiplaysound.single import SKIP_DEFAULT, RaiParser

    parser = RaiParser(
        args.url,
        args.folder,
    )
    if args.skip == ["d"] or args.skip == ["default"]:
        parser.skip = SKIP_DEFAULT
    else:
        parser.skip = [s.lower() for s in args.skip]
    parser.date_ok = args.dateok
    parser.reverse = args.reverse
    parser.process()


def handle_all(args: "Namespace") -> None:
    from raiplaysound.all import RaiPlaySound

    skip = [s.lower() for s in args.skip]
    dumper = RaiPlaySound()
    dumper.workers = args.workers
    dumper.parse_index()
    dumper.create_feeds(skip)


def handle_index(_: "Namespace") -> None:
    from raiplaysound.index import Indexer

    indexer = Indexer()
    indexer.generate()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="raiplaysound",
        description="Genera RSS da RaiPlaySound",
        epilog="Info su https://github.com/timendum/raiplaysound/",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    # single command
    parser_single = subparsers.add_parser(
        "single",
        help="Genera un RSS da un programma di RaiPlaySound",
    )
    parser_single.set_defaults(func=handle_single)
    parser_single.add_argument("url", help="URL di un podcast (o playlist) su raiplaysound.")
    parser_single.add_argument(
        "-f", "--folder", help="Cartella in cui scrivere il RSS podcast.", default="."
    )
    parser_single.add_argument(
        "--skip",
        help="Specifica tipologie da saltare.",
        action="append",
        default=[],
    )
    parser_single.add_argument(
        "--dateok",
        help="Lascia inalterata la data di pubblicazione degli episodi.",
        action="store_true",
    )
    parser_single.add_argument(
        "--reverse",
        help="Ordina gli episodi dal più recente al meno recente.",
        action="store_true",
    )
    # all command
    parser_all = subparsers.add_parser(
        "all", help="Genera un RSS per ogni programma disponibile su RaiPlaySound"
    )
    parser_all.set_defaults(func=handle_all)
    parser_all.add_argument(
        "--skip",
        help=("Specifica tipologie da saltare, (default: programmi, film, notiziari)."),
        action="append",
        default=[],
    )
    parser_all.add_argument(
        "--workers",
        help="Number of parallel workers to use when generating feeds (default: 1).",
        type=int,
        default=1,
    )
    # index command
    parser_index = subparsers.add_parser(
        "index", help="Genera index.html per ogni feed già generato."
    )
    parser_index.set_defaults(func=handle_index)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
