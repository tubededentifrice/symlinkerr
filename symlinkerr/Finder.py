import logging
import os

from symlinkerr.File import File

"""
Find all the files in the watched directories, check they are eligible for replacement with the Checker.
If all is in other, pass them to the Replacer for actual replacement.
"""


class Finder:
    logger = logging.getLogger("Finder")

    def __init__(self, config, database, indexer, checker, replacer):
        self.config = config
        self.watch_directories = config["directories"]["watch-directories"]
        self.undo_directories = config["directories"]["undo-all-symlinks-directories"]
        self.database = database
        self.indexer = indexer
        self.checker = checker
        self.replacer = replacer

        self.followlinks = self.config["followlinks"]
        self.find_candidates_by = self.config["find-candidates-by"]
        self.only_undo_symlinks_to_target_directories = self.config["only-undo-symlinks-to-target-directories"]

    def get_candidates(self, file):
        if self.find_candidates_by == "SIZE":
            return self.indexer.get_candidates_by_size(file.get_size())
        if self.find_candidates_by == "FILENAME":
            return self.indexer.get_candidates_by_filename(file.get_filename())
        return self.indexer.get_candidates_by_size_and_filename(
            file.get_size(), file.get_filename()
        )

    def find_and_replace_with_symlinks(self):
        for directory in self.watch_directories:
            self.logger.info(f"Finding files to replace with symlinks in directory {directory}")
            self.find_and_replace_with_symlinks_in_directory(directory["dir"])

    def find_and_replace_with_symlinks_in_directory(self, path):
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                # We very obviously want to avoid symlinks!
                if not os.path.islink(fullpath):
                    file = File(fullpath)
                    if (not self.replacer.is_file_a_replacement(file)) and self.checker.is_eligible_for_replacement(file):
                        candidates = self.get_candidates(file)
                        self.logger.info(
                            f"Candidates for {fullpath} sorted by priority:\n{"\n".join(candidates)}"
                        )

                        for candidate in candidates:
                            candidate_file = File(candidate)
                            if self.checker.can_be_replaced_with(file, candidate_file):
                                self.logger.info(
                                    f"Selected candidate {candidate} which matched all criteria, performing replacement"
                                )
                                self.replacer.replace_with_symlink(file, candidate_file)
                                break # Do not evaluate other candidates

    def find_and_replace_with_content(self):
        for directory in self.undo_directories:
            self.logger.info(f"Finding files to replace with content in directory {directory}")
            self.find_and_replace_with_content_in_directory(directory["dir"])

    def find_and_replace_with_content_in_directory(self, path):
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                # We are only interested in symlinks over here!
                if os.path.islink(fullpath):
                    symlink_file = File(fullpath)
                    link_target = symlink_file.get_readlink()
                    if not self.only_undo_symlinks_to_target_directories or self.indexer.is_file_within_target_directories(link_target):
                        if self.checker.is_eligible_for_content_replacement(symlink_file):
                            self.logger.info(f"Found a simlink to unwind: {fullpath} which links to {link_target}")
                            self.replacer.replace_with_content(symlink_file)

                    