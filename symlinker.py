#!/usr/bin/env python3


import argparse
import logging
import pprint
import os
import sqlite3
import yaml
from symlinkerr.Checker import Checker
from symlinkerr.Finder import Finder
from symlinkerr.Indexer import Indexer
from symlinkerr.Replacer import Replacer


def main():
    parser = argparse.ArgumentParser(
        description="""Replace files in a directory with symlinks to another one.
Useful to save your local disk space by replacing your files with links to a remote share.
WARNING: THIS THING IS DESTRUCTIVE! It will delete stuff and replace them with symlinks. If the target is deleted or moved, the symlinks will become invalids and you'll be screwed."""
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
        choices=["replace", "watch", "undo", "undo-all-symlinks", "reset-failures", "reset-hashes"],
        help="Action to perform (default: %(default)s)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s - %(module)s - %(message)s")
    logger = logging.getLogger("symlinkerr")

    logger.info(f"Running with parameters: {vars(args)}")

    with open("config_default.yml", "r") as config_file:
        default_config = yaml.safe_load(config_file)
    
    # Create configuration file if it doesn't exist
    if args.config == "config.yml" and not os.path.isfile(args.config):
        open(args.config, 'a').close()
    with open(args.config, "r") as config_file:
        config = {**default_config, **yaml.safe_load(config_file)}

    logger.info(f"Configuration: {pprint.pformat(config)}")

    database = sqlite3.connect(config["database"])
    indexer = Indexer(
        config=config["indexer"],
        target_directories=config["directories"]["symlink-target-directories"],
        database=database,
        min_size = config["finder"]["files-min-size-bytes"]
    )
    checker = Checker(
        config=config["checker"],
        database=database,
    )
    replacer = Replacer(
        config = config["replacer"],
        database=database,
    )
    finder = Finder(
        config = config["finder"],
        watch_directories=config["directories"]["watch-directories"],
        database=database,
        checker=checker,
        replacer=replacer,
    )

    if args.action in ["watch", "replace"]:
        indexer.index_target_directories()
        finder.find_and_replace()


    # replacer = Replacer(
    #     watch_directory=args.watch_directory,
    #     symlink_target_directory=args.symlink_target_directory,
    # )


if __name__ == "__main__":
    main()
