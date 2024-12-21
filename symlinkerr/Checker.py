import logging
import re
import time
import hashlib


class Checker:
    logger = logging.getLogger("Checker")

    def __init__(self, config, database):
        self.config = config
        self.database = database

        self.min_size = self.config["files-min-size-bytes"]
        self.min_age = self.config["files-min-age-seconds"]
        self.check_hash = config["check-hash"]
        self.exclude_watch_directories = [
            re.compile(r) for r in config["exclusions"]["watch-directories-regexes"]
        ]
        self.exclude_target_directories = [
            re.compile(r)
            for r in config["exclusions"]["symlink-target-directories-regexes"]
        ]

        self.create_hashes_table()

    def clear_hashes_cache(self):
        self.database.execute("DROP TABLE IF EXISTS hashes;")
        self.create_hashes_table()  # This will do the commit()

    def create_hashes_table(self):
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS hashes (
                fullpath VARCHAR PRIMARY KEY,
                hash VARCHAR,
                size LONG,
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
            self.logger.debug(
                f"Hash of {original_file.fullpath} is {original_file_hash}"
            )

            replacement_file_hash = self.get_hash(replacement_file)
            self.logger.debug(
                f"Hash of {replacement_file.fullpath} is {replacement_file_hash}"
            )

            if original_file_hash != replacement_file_hash:
                return False

        return True

    def get_hash(self, file):
        # Check if the hash is in the cache
        cursor = self.database.execute(
            f"SELECT hash FROM hashes WHERE fullpath=? AND size={file.get_size()} AND mtime={file.get_mtime()}",
            (file.fullpath,),
        )

        hash_in_cache = cursor.fetchone()
        if hash_in_cache is not None:
            return hash_in_cache[0]

        # Get the hash an populate the cache
        self.logger.debug(
            f"Could not find the hash of {file.fullpath} in the cache, computing it, this will take a while"
        )
        file_hash = self.sha256sum(file.fullpath)

        self.database.execute(
            "INSERT OR REPLACE INTO hashes(fullpath, hash, size, mtime) VALUES(?, ?, ?, ?)",
            (file.fullpath, file_hash, file.get_size(), file.get_mtime()),
        )
        self.database.commit()

        return file_hash

    def sha256sum(self, fullpath):
        with open(fullpath, "rb", buffering=0) as f:
            return hashlib.file_digest(f, "sha256").hexdigest()
