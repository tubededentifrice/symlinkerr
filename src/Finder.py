import logging
import os
import sqlite3

from src.Checker import Checker
from src.File import File
from src.Indexer import Indexer
from src.Replacer import Replacer

"""
Find all the files in the watched directories, check they are eligible for replacement with the Checker.
If all is in other, pass them to the Replacer for actual replacement.
"""


class Finder:
    logger = logging.getLogger("Finder")

    def __init__(
        self,
        config: dict,
        database: sqlite3.Connection,
        indexer: Indexer,
        checker: Checker,
        replacer: Replacer,
    ):
        self.config = config
        self.watch_directories = config["directories"]["watch-directories"]
        self.undo_directories = config["directories"]["undo-all-symlinks-directories"]
        self.database = database
        self.indexer = indexer
        self.checker = checker
        self.replacer = replacer

        self.followlinks = self.config["followlinks"]
        self.find_candidates_by = self.config["find-candidates-by"]
        self.only_undo_symlinks_to_target_directories = self.config[
            "only-undo-symlinks-to-target-directories"
        ]

    def get_candidates(self, file: File) -> list[str]:
        if self.find_candidates_by == "SIZE":
            return self.indexer.get_candidates_by_size(file.get_size())
        if self.find_candidates_by == "FILENAME":
            return self.indexer.get_candidates_by_filename(file.get_filename())
        if self.find_candidates_by == "SIZE_OR_FILENAME":
            return self.indexer.get_candidates_by_size_or_filename(
                file.get_size(), file.get_filename()
            )

        return self.indexer.get_candidates_by_size_and_filename(
            file.get_size(), file.get_filename()
        )

    def find_and_replace_with_symlinks(self) -> None:
        for directory in self.watch_directories:
            self.logger.info(
                f"Finding files to replace with symlinks in directory {directory}"
            )
            self.find_and_replace_with_symlinks_in_directory(directory["dir"])

    def find_and_replace_with_symlinks_in_directory(self, path: str) -> None:
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                # We very obviously want to avoid symlinks!
                if not os.path.islink(fullpath):
                    file = File(fullpath)
                    if (
                        not self.replacer.is_file_a_replacement(file)
                    ) and self.checker.is_eligible_for_replacement(file):
                        candidates = self.get_candidates(file)

                        if len(candidates) > 0:
                            self.logger.info(
                                f"Candidates for {fullpath} sorted by priority:\n{"\n".join(candidates)}"
                            )

                            for candidate in candidates:
                                try:
                                    candidate_file = File(candidate)
                                    if self.checker.can_be_replaced_with(
                                        file, candidate_file
                                    ):
                                        self.logger.info(
                                            f"Selected candidate {candidate} which matched all criteria, performing replacement"
                                        )
                                        self.replacer.replace_with_symlink(
                                            file, candidate_file
                                        )
                                        break  # Do not evaluate other candidates
                                except Exception as e:
                                    self.logger.error(
                                        f"An exception occured while replacing {file.fullpath} with a symlink to {candidate_file.fullpath}: {e}"
                                    )
                        else:
                            self.logger.debug(f"No candidate found for {fullpath}")

    def find_and_replace_with_content(self) -> None:
        for directory in self.undo_directories:
            self.logger.info(
                f"Finding files to replace with content in directory {directory}"
            )
            self.find_and_replace_with_content_in_directory(directory["dir"])

    def find_and_replace_with_content_in_directory(self, path: str) -> None:
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                # We are only interested in symlinks over here!
                if os.path.islink(fullpath):
                    symlink_file = File(fullpath)
                    link_target = symlink_file.get_readlink()
                    if (
                        not self.only_undo_symlinks_to_target_directories
                        or self.indexer.is_file_within_target_directories(link_target)
                    ):
                        if self.checker.is_eligible_for_content_replacement(
                            symlink_file
                        ):
                            self.logger.info(
                                f"Found a simlink to unwind: {fullpath} which links to {link_target}"
                            )

                            try:
                                self.replacer.replace_with_content(symlink_file)
                            except Exception as e:
                                self.logger.error(
                                    f"An exception occured while replacing {symlink_file.fullpath} with contents from {link_target}: {e}"
                                )
