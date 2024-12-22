#!/usr/bin/env python3


import argparse
import logging
import os
import pprint
import shutil
import sqlite3
import time

import yaml

from src.Checker import Checker
from src.Finder import Finder
from src.Indexer import Indexer
from src.Replacer import Replacer

IS_IN_DOCKER = os.environ.get("IS_IN_DOCKER")

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

    default_config_path = "config.yml"
    if IS_IN_DOCKER:
        default_config_path = "/config/" + default_config_path

    parser.add_argument(
        "-c",
        "--config",
        default=default_config_path,
        const=default_config_path,
        nargs="?",
        type=str,
        help="Config file (default: %(default)s)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Confirm all replacements before performing them",
    )
    parser.add_argument(
        "action",
        default="watch",
        const="watch",
        nargs="?",
        choices=[
            "replace-with-symlinks",
            "replace-with-content",
            "watch",
            # "changelog",
            "clear-changelog",
            "clear-hashes",
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
    config_arg_file = args.config
    with open(config_default_file, "r") as config_file:
        config = yaml.safe_load(config_file)

    while True:
        start_time = round(time.time())

        # Always reload the config when we loop, in case it changed on disk
        # Create configuration file if it doesn't exist
        if os.path.isfile(config_arg_file):
            with open(config_arg_file, "r") as config_file:
                config = merge(yaml.safe_load(config_file), config)
        else:
            logger.warn(
                f"Configuration not found, creating a base one at {config_arg_file}"
            )
            shutil.copy("config_override_base.yml", config_arg_file)

        logger.info(f"Configuration: {pprint.pformat(config)}")
        logging.getLogger().setLevel(config["logger"]["level"])

        with sqlite3.connect(config["database"]) as database:
            indexer = Indexer(
                config=config["indexer"],
                target_directories=config["finder"]["directories"][
                    "symlink-target-directories"
                ],
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
                interactive=args.interactive,
            )
            finder = Finder(
                config=config["finder"],
                database=database,
                indexer=indexer,
                checker=checker,
                replacer=replacer,
            )

            if args.action in [
                "watch",
                "replace-with-symlinks",
                "replace-with-content",
            ]:
                indexer.index_target_directories()

            if args.action in ["watch", "replace-with-symlinks"]:
                finder.find_and_replace_with_symlinks()

            if args.action in ["watch", "replace-with-content"]:
                finder.find_and_replace_with_content()

            if args.action in ["clear-changelog"]:
                replacer.clear_changelog()

            if args.action in ["clear-hashes"]:
                checker.clear_hashes_cache()

            replacer.print_and_delete_dry_run_change()

        # Release the sqlite connection while we sleep
        if args.action in ["watch"]:
            # Sleep so that the total time is interval-seconds
            interval_duration = config["watcher"]["interval-seconds"]
            run_duration = round(time.time()) - start_time
            sleep_duration = interval_duration - run_duration
            if sleep_duration <= 0:
                sleep_duration = interval_duration

            logger.info(f"Sleeping for {sleep_duration} seconds...")
            time.sleep(sleep_duration)
        else:
            return 0


if __name__ == "__main__":
    main()
