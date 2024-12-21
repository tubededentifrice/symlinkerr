import logging
import os
import shutil
import time


class Replacer:
    logger = logging.getLogger("Replacer")

    def __init__(self, config, database):
        self.config = config
        self.database = database

        self.dry_run = config["dry-run"]
        
        self.create_changes_table()

    def replace_with_symlink(self, file, file_symlink_target):
        self.logger.info(
            f"Replacing {file.fullpath} with a symlink to {file_symlink_target.fullpath}"
        )
        if self.dry_run:
            self.logger.info("Just kidding, not actually doing anything, we are in a dry-run!")
        else:
            # Make the symlink in a temporary location first, then force replace the target with it, to achieve atomic replace
            temporary_file = file.fullpath + ".link"

            self.log_change(file.fullpath, temporary_file, file_symlink_target.fullpath, "CREATE_TEMP_SYMLINK_START")
            os.symlink(temporary_file, file_symlink_target.fullpath)
            self.log_change(file.fullpath, temporary_file, file_symlink_target.fullpath, "CREATE_TEMP_SYMLINK_COMMIT")

            self.log_change(file.fullpath, file.fullpath, file_symlink_target.fullpath, "MOVE_SYMLINK_START")
            shutil.move(temporary_file, file.fullpath)
            self.log_change(file.fullpath, file.fullpath, file_symlink_target.fullpath, "MOVE_SYMLINK_COMMIT")


    def replace_with_content(self, file_symlink):
        pass

    def create_changes_table(self):
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS changes (
                id INTEGER PRIMARY KEY,
                date REAL,
                fullpath VARCHAR,
                filechanged VARCHAR,
                target VARCHAR,
                action VARCHAR
            );
        """)
        self.database.commit()

    def log_change(self, fullpath, filechanged, target, action):
        self.database.execute(
            "INSERT INTO changes(date, fullpath, filechanged, target, action) VALUES(?, ?, ?, ?, ?)",
            (time.time(), fullpath, filechanged, target, action)
        )
        self.database.commit()
