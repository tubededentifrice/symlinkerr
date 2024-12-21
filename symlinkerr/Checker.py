import logging
import re
import time

class Checker:
    logger = logging.getLogger("Checker")

    def __init__(self, config, database):
        self.config = config
        self.database = database

        self.min_size = self.config["files-min-size-bytes"]
        self.min_age = self.config["files-min-age-seconds"]
        self.check_hash = config["check-hash"]
        self.exclude_watch_directories = [re.compile(r) for r in config["exclusions"]["watch-directories-regexes"]]
        self.exclude_target_directories = [re.compile(r) for r in config["exclusions"]["symlink-target-directories-regexes"]]

        self.database.execute("""
            CREATE TABLE IF NOT EXISTS hashes (
                fullpath VARCHAR PRIMARY KEY,
                hash VARCHAR,
                size INTEGER,
                mtime LONG
            );
        """)
        self.database.commit()

    def is_eligible_for_replacement(self, file):
        # Do the fastest check first

        # Check if the size matches the criteria
        if file.get_size() < self.min_size:
            self.logger.debug(
                f"Ignoring file with size {file.get_size()}: {file.fullpath} as it's lower than the minimum threshold of {self.min_size}"
            )
            return False

        # Check if the age matches the criteroa
        file_age = time.time() - file.get_mtime()
        if file_age < self.min_age:
            self.logger.debug(
                f"Ignoring file with size {file.get_size()}, file_age {file_age} seconds: {file.fullpath} as it's been modified recently (threshold: {self.min_age} seconds)"
            )
            return False

        # Check that the file is not excluded
        for exclusion in self.exclude_watch_directories:
            if exclusion.match(file.filepath):
                self.logger.debug(
                    f"Ignoring file {file.fullpath}, matching exclusion regex '{exclusion.pattern}'"
                )
                return False

        return True

    def can_be_replaced_with(self, original_file, replacement_file):
        # Check that the destination is not excluded
        for exclusion in self.exclude_target_directories:
            if exclusion.match(replacement_file.filepath):
                self.logger.debug(
                    f"Replacement file {replacement_file.fullpath} matching exclusion regex '{exclusion.pattern}'"
                )
                return False

        # Check the file hashes
        if self.check_hash:
            original_file_hash = self.get_hash(original_file)
            replacement_file_hash = self.get_hash(replacement_file)
            pass

        return True

    def get_hash(self, file):
        cursor = self.database.execute(
            "SELECT hash FROM hashes WHERE fullpath=? AND size=? AND mtime=?",
            (file.filepath, file.get_size(), file.get_mtime(), )
        )
        hash_in_cache = cursor.fetchone()
        print(f"hash_in_cache = {hash_in_cache}")