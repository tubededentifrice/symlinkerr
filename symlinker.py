#!/usr/bin/env python3


import argparse
import logging
import pprint
import sqlite3
import yaml
from symlinkerr.Replacer import Replacer
from symlinkerr.Indexer import Indexer


def main():
    parser = argparse.ArgumentParser(
        description="""Replace files in a directory with symlinks to another one.
Useful to save your local disk space by replacing your files with links to a remote share."""
    )

    parser.add_argument(
        "-c",
        "--config",
        default="config.yml",
        const="config.yml",
        nargs="?",
        type=str,
        help="Config file (default: %(default)s)",
    )
    parser.add_argument(
        "action",
        default="watch",
        const="watch",
        nargs="?",
        choices=["replace", "watch", "undo", "undo-all-symlinks", "index-symlink-targets", "reset-failures", "reset-cache-watched", "reset-cache-target"],
        help="Action to perform (default: %(default)s)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s - %(module)s - %(message)s")
    logger = logging.getLogger("symlinkerr")

    logger.info(f"Running with parameters: {vars(args)}")

    with open(args.config, "r") as config_file:
        config = yaml.safe_load(config_file)

    logger.info(f"Configuration: {pprint.pformat(config)}")

    database = sqlite3.connect(config["database"])
    indexer = Indexer(
        target_directories=config["directories"]["symlink-target-directories"],
        database=database,
    )
    
    if args.action == "index-symlink-targets":
        indexer.index()


    # replacer = Replacer(
    #     watch_directory=args.watch_directory,
    #     symlink_target_directory=args.symlink_target_directory,
    # )


if __name__ == "__main__":
    main()
