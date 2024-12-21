import logging
import os
import time
from symlinkerr.File import File


"""
Find all the files in the watched directories, check they are eligible for replacement with the Checker.
If all is in other, pass them to the Replacer for actual replacement.
"""


class Finder:
    logger = logging.getLogger("Finder")

    def __init__(self, config, watch_directories, database, indexer, checker, replacer):
        self.config = config
        self.watch_directories = watch_directories
        self.database = database
        self.indexer = indexer
        self.checker = checker
        self.replacer = replacer

        self.followlinks = self.config["followlinks"]
        self.find_candidates_by = self.config["find-candidates-by"]

    def get_candidates(self, file):
        if self.find_candidates_by == "SIZE":
            return self.indexer.get_candidates_by_size(file.get_size())
        if self.find_candidates_by == "FILENAME":
            return self.indexer.get_candidates_by_filename(file.get_filename())
        return self.indexer.get_candidates_by_size_and_filename(file.get_size(), file.get_filename())

    def find_and_replace(self):
        for directory in self.watch_directories:
            self.logger.info(f"Finding files to replace in directory {directory}")
            self.find_and_replace_in_directory(directory["dir"])

    def find_and_replace_in_directory(self, path):
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                # We very obviously want to avoid symlinks!
                if not os.path.islink(fullpath):
                    file = File(fullpath)
                    if self.checker.is_eligible_for_replacement(file):
                        candidates = self.get_candidates(file)
                        self.logger.info(f"Candidates for {fullpath}:\n{"\n".join(candidates)}")

                        for candidate in candidates:
                            candidate_file = File(candidate)
                            if self.checker.can_be_replaced_with(file, candidate_file):
                                self.logger.info(f"Selected candidate {candidate} which matched all criteria, performing replacement")
                                break
