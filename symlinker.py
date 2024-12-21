#!/usr/bin/env python3


import argparse
import logging
import os
import pprint
import shutil
import sqlite3

import yaml

from symlinkerr.Checker import Checker
from symlinkerr.Finder import Finder
from symlinkerr.Indexer import Indexer
from symlinkerr.Replacer import Replacer


def merge(source, destination):
    if source is not None:
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                merge(value, node)
            else:
                destination[key] = value

    return destination


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
        choices=[
            "replace",
            "watch",
            "undo",
            "undo-all-symlinks",
            "reset-failures",
            "reset-hashes",
        ],
        help="Action to perform (default: %(default)s)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s - %(module)s - %(message)s",
    )
    logger = logging.getLogger("symlinkerr")

    logger.info(f"Running with parameters: {vars(args)}")

    config_default_file = "config_default.yml"
    with open(config_default_file, "r") as config_file:
        config = yaml.safe_load(config_file)

    # Create configuration file if it doesn't exist
    config_arg_file = args.config
    if os.path.isfile(config_arg_file):
        with open(config_arg_file, "r") as config_file:
            config = merge(yaml.safe_load(config_file), config)
    elif config_arg_file == "config.yml":
        logger.info(f"Configuration not found, creating a base one: {config_arg_file}")
        shutil.copy(config_default_file, config_arg_file)
    else:
        raise Exception(
            f"Config file {config_arg_file} not found; since this is potentially destructive, refusing to run. Create that file and try again."
        )
        exit(1)

    logger.info(f"Configuration: {pprint.pformat(config)}")
    logging.getLogger().setLevel(config["logger"]["level"])

    with sqlite3.connect(config["database"]) as database:
        indexer = Indexer(
            config=config["indexer"],
            target_directories=config["directories"]["symlink-target-directories"],
            database=database,
            min_size=config["checker"]["files-min-size-bytes"],
        )
        checker = Checker(
            config=config["checker"],
            database=database,
        )
        replacer = Replacer(
            config=config["replacer"],
            database=database,
        )
        finder = Finder(
            config=config["finder"],
            watch_directories=config["directories"]["watch-directories"],
            database=database,
            indexer=indexer,
            checker=checker,
            replacer=replacer,
        )

        if args.action in ["watch", "replace"]:
            indexer.index_target_directories()
            finder.find_and_replace()

        if args.action in ["reset-hashes"]:
            checker.clear_hashes_cache()

    # replacer = Replacer(
    #     watch_directory=args.watch_directory,
    #     symlink_target_directory=args.symlink_target_directory,
    # )


if __name__ == "__main__":
    main()
