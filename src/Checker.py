import hashlib
import logging
import re
import sqlite3
import time

from src.File import File

"""
Perform the replacement checks
"""


class Checker:
    logger = logging.getLogger("Checker")

    def __init__(self, config: dict, database: sqlite3.Connection):
        self.config = config
        self.database = database

        self.min_size = self.config["files-min-size-bytes"]
        self.min_age = self.config["files-min-age-seconds"]
        self.check_hash = config["check-hash"]
        self.change_in_mtime_invalidates_hash = config[
            "change-in-mtime-invalidates-hash"
        ]

        self.exclude_watch_directories = [
            re.compile(r) for r in config["exclusions"]["watch-directories-regexes"]
        ]
        self.exclude_target_directories = [
            re.compile(r)
            for r in config["exclusions"]["symlink-target-directories-regexes"]
        ]
        self.exclude_undo_symlinks_directories = [
            re.compile(r)
            for r in config["exclusions"]["undo-all-symlinks-directories-regexes"]
        ]

        self.create_hashes_table()

    def clear_hashes_cache(self) -> None:
        self.database.execute("DROP TABLE IF EXISTS hashes;")
        self.create_hashes_table()  # This will do the commit()

    def create_hashes_table(self) -> None:
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS hashes (
                fullpath VARCHAR PRIMARY KEY,
                hash VARCHAR,
                size LONG,
                mtime LONG
            );
        """)
        self.database.commit()

    def is_eligible_for_replacement(self, file: File) -> bool:
        # Do the fastest checks first

        # Check if the size matches the criteria
        if file.get_size() < self.min_size:
            self.logger.debug(
                f"Ignoring file with size {file.get_size()}: {file.fullpath} as it's lower than the minimum threshold of {self.min_size}"
            )
            return False

        # Check if the age matches the criteroa
        file_age = round(time.time() - file.get_mtime())
        if file_age < self.min_age:
            self.logger.debug(
                f"Ignoring file with size {file.get_size()}, file_age {file_age} seconds: {file.fullpath} as it's been modified recently (threshold: {self.min_age} seconds)"
            )
            return False

        # Check that the file is not excluded
        for exclusion in self.exclude_watch_directories:
            if exclusion.match(file.fullpath):
                self.logger.debug(
                    f"Ignoring file {file.fullpath}, matching exclusion regex '{exclusion.pattern}'"
                )
                return False

        return True

    def can_be_replaced_with(self, original_file: File, replacement_file: File) -> bool:
        # Check that the destination is not excluded
        for exclusion in self.exclude_target_directories:
            if exclusion.match(replacement_file.fullpath):
                self.logger.debug(
                    f"Replacement file {replacement_file.fullpath} matching exclusion regex '{exclusion.pattern}'"
                )
                return False

        # Check the file hashes
        if self.check_hash:
            original_file_hash = self.get_hash(original_file)
            self.logger.debug(f"Hash {original_file_hash} for {original_file.fullpath}")

            replacement_file_hash = self.get_hash(replacement_file)
            self.logger.debug(
                f"Hash {replacement_file_hash} for {replacement_file.fullpath}"
            )

            if original_file_hash != replacement_file_hash:
                self.logger.info(
                    f"Both files have different hashes, discarding {replacement_file.fullpath} as a candidate for {original_file.fullpath}"
                )
                return False

        self.logger.info(
            f"Both files have same hash {original_file_hash}, accepting {replacement_file.fullpath} as a candidate for {original_file.fullpath}"
        )
        return True

    def is_eligible_for_content_replacement(self, symlink_file: File) -> bool:
        for exclusion in self.exclude_undo_symlinks_directories:
            if exclusion.match(symlink_file.fullpath):
                self.logger.debug(
                    f"Symlink {symlink_file} matching exclusion regex '{exclusion.pattern}'"
                )
                return False

        return True

    def get_hash(self, file: File) -> str:
        # Check if the hash is in the cache

        query = f"SELECT hash FROM hashes WHERE fullpath=? AND size={file.get_size()}"
        if self.change_in_mtime_invalidates_hash:
            query += f" AND mtime={file.get_mtime()}"

        cursor = self.database.execute(query, (file.fullpath,))

        hash_in_cache = cursor.fetchone()
        if hash_in_cache is not None:
            return hash_in_cache[0]

        # Get the hash an populate the cache
        self.logger.info(f"Could not find the hash of {file.fullpath} in the cache, computing it, this will take a while")
        start_time = round(time.time())
        file_hash = self.compute_hash(file)
        end_time = round(time.time())
        self.logger.info(f"Computing the hash of {file.fullpath} ({file_hash}) took {end_time - start_time} seconds")

        self.database.execute(
            "INSERT OR REPLACE INTO hashes(fullpath, hash, size, mtime) VALUES(?, ?, ?, ?)",
            (file.fullpath, file_hash, file.get_size(), file.get_mtime()),
        )
        self.database.commit()

        return file_hash

    def compute_hash(self, file: File) -> str:
        # This is much more expensive for no good reason and can't print progress
        # with open(fullpath, "rb", buffering=0) as f:
        #     return hashlib.file_digest(f, "sha256").hexdigest()

        blocksize = 2**20
        m = hashlib.md5()
        with open(file.fullpath, "rb") as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    print("", flush=True)
                    break
                m.update(buf)
                print(".", end="", flush=True)
        return m.hexdigest()
