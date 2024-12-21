import logging
import os
import time


"""
Find all the files in the watched directories, check they are eligible for replacement with the Checker.
If all is in other, pass them to the Replacer for actual replacement.
"""


class Finder:
    logger = logging.getLogger("Finder")

    def __init__(self, config, watch_directories, database, checker, replacer):
        self.config = config
        self.watch_directories = watch_directories
        self.database = database
        self.checker = checker
        self.replacer = replacer

        self.followlinks = self.config["followlinks"]
        self.min_size = self.config["files-min-size-bytes"]
        self.min_age = self.config["files-min-age-seconds"]

    def find_and_replace(self):
        for directory in self.watch_directories:
            self.logger.info(f"Finding files to replace in directory {directory}")
            self.find_and_replace_in_directory(directory["dir"])

    def find_and_replace_in_directory(self, path):
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                size = os.path.getsize(fullpath)
                if size >= self.min_size:
                    file_age = time.time() - os.path.getmtime(path)
                    if file_age >= self.min_age:
                        self.logger.debug(
                            f"Checking candidates for file with size {size}, file_age {round(file_age)} seconds: {fullpath}"
                        )
                    else:
                        self.logger.debug(
                            f"Ignoring file with size {size}, file_age {file_age} seconds: {fullpath} as it's been modified recently (threshold: {self.min_age} seconds)"
                        )
                else:
                    self.logger.debug(
                        f"Ignoring file with size {size}: {fullpath} as it's lower than the minimum threshold of {self.min_size}"
                    )

                #     self.logger.debug(f"Found file with size {size}: {fullpath}")
                #     self.database.execute(
                #         "INSERT OR IGNORE INTO index_target_directories(fullpath, filename, size) VALUES(?, ?, ?)",
                #         (fullpath, filename, size),
                #     )
                # else:
                #     self.logger.debug(
                #         f"Ignoring filewith size {size}: {fullpath} as it's lower than the minimum threshold of {self.min_size}"
