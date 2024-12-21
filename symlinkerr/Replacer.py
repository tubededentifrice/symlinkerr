import logging
import os
import shutil
import time


class Replacer:
    logger = logging.getLogger("Replacer")

    temporary_suffix = ".tmp"

    def __init__(self, config, database):
        self.config = config
        self.database = database

        self.dry_run = config["dry-run"]
        self.add_suffix = config["add-suffix-instead-of-deleting"]
        self.suffix = config["suffix"]

        self.create_changelog_table()

    def clear_changelog(self):
        self.database.execute("DROP TABLE IF EXISTS changelog;")
        self.create_changelog_table()  # This will do the commit()

    def create_changelog_table(self):
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS changelog (
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
            "INSERT INTO changelog(date, fullpath, filechanged, target, action) VALUES(?, ?, ?, ?, ?)",
            (time.time(), fullpath, filechanged, target, action),
        )
        self.database.commit()

    def is_file_a_replacement(self, file):
        return file.fullpath.endswith(self.suffix) or file.fullpath.endswith(
            self.temporary_suffix
        )

    def replace_with_symlink(self, file, file_symlink_target):
        self.logger.info(
            f"Replacing {file.fullpath} with a symlink to {file_symlink_target.fullpath}"
        )
        if self.dry_run:
            self.logger.info(
                "Just kidding, not actually doing anything, we are in a dry-run!"
            )
        else:
            # Make the symlink in a temporary location first, then force replace the target with it, to achieve atomic replace
            temporary_file = file.fullpath + self.temporary_suffix

            if os.path.isfile(temporary_file):
                os.remove(temporary_file)

            self.log_change(
                file.fullpath,
                temporary_file,
                file_symlink_target.fullpath,
                "CREATE_TEMP_SYMLINK_START",
            )
            os.symlink(file_symlink_target.fullpath, temporary_file)
            self.log_change(
                file.fullpath,
                temporary_file,
                file_symlink_target.fullpath,
                "CREATE_TEMP_SYMLINK_COMMIT",
            )

            if self.add_suffix:
                if not self.suffix:
                    raise Exception(
                        "Requested to add a suffix, but the suffix to add was empty"
                    )
                if self.suffix == self.temporary_suffix:
                    raise Exception(
                        "Please don't use .tmp as suffix, as we are creating the simlink with that extension first"
                    )

                rename_existing_to = file.fullpath + self.suffix
                self.log_change(
                    file.fullpath,
                    rename_existing_to,
                    file_symlink_target.fullpath,
                    "ADD_SUFFIX_START",
                )
                shutil.move(file.fullpath, rename_existing_to)
                self.log_change(
                    file.fullpath,
                    rename_existing_to,
                    file_symlink_target.fullpath,
                    "ADD_SUFFIX_COMMIT",
                )

            self.log_change(
                file.fullpath,
                file.fullpath,
                file_symlink_target.fullpath,
                "MOVE_SYMLINK_START",
            )
            shutil.move(temporary_file, file.fullpath)
            self.log_change(
                file.fullpath,
                file.fullpath,
                file_symlink_target.fullpath,
                "MOVE_SYMLINK_COMMIT",
            )

    def replace_with_content(self, file_symlink):
        pass
