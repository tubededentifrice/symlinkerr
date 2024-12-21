import logging
import os
import shutil
import time


class Replacer:
    logger = logging.getLogger("Replacer")

    temporary_suffix = ".tmp"

    def __init__(self, config, database, interactive=False):
        self.config = config
        self.database = database
        self.interactive = interactive

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
            return
        # Make the symlink in a temporary location first, then force replace the target with it, to achieve atomic replace
        temporary_file = file.fullpath + self.temporary_suffix

        if os.path.isfile(temporary_file):
            def remove_existing_tmp():
                os.remove(temporary_file)

            if not self.wrap_interactive(f"Remove existing temporary file {temporary_file}?", remove_existing_tmp):
                return

        def create_symlink_tmp():
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
        if not self.wrap_interactive(f"Create symlink {temporary_file} ==> {file_symlink_target.fullpath}?", create_symlink_tmp):
            return

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
            def rename_existing_to_bak():
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
            if not self.wrap_interactive(f"Rename {file.fullpath} to {rename_existing_to}?", rename_existing_to_bak):
                return

        def replace_with_symlink():
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
        if not self.wrap_interactive(f"Replace {file.fullpath} with its symlink to {file_symlink_target.fullpath}?", replace_with_symlink):
            return

    def replace_with_content(self, symlink_file):
        self.logger.info(
            f"Replacing {symlink_file.fullpath} with its content from {symlink_file.get_readlink()}"
        )
        if self.dry_run:
            self.logger.info(
                "Just kidding, not actually doing anything, we are in a dry-run!"
            )
            return

        temporary_file = symlink_file.fullpath + self.temporary_suffix
        if os.path.isfile(temporary_file):
            def remove_existing_tmp():
                os.remove(temporary_file)

            if not self.wrap_interactive(f"Remove existing temporary file {temporary_file}?", remove_existing_tmp):
                return
            

        def copy_content_to_tmp():
            self.log_change(
                symlink_file.fullpath,
                temporary_file,
                symlink_file.get_readlink(),
                "SYMLINK_COPY_CONTENT_START",
            )
            shutil.copy(symlink_file.fullpath, temporary_file)
            self.log_change(
                symlink_file.fullpath,
                temporary_file,
                symlink_file.get_readlink(),
                "SYMLINK_COPY_CONTENT_COMMIT",
            )

        if not self.wrap_interactive(f"Copy the content of {symlink_file.fullpath} to {temporary_file}?", copy_content_to_tmp):
            return

        # TODO: Shall we check the hash of the files are matching?

        def rename_tmp_to_final():
            self.log_change(
                symlink_file.fullpath,
                temporary_file,
                symlink_file.fullpath,
                "SYMLINK_CONTENT_RENAME_START",
            )
            shutil.move(temporary_file, symlink_file.fullpath)
            self.log_change(
                symlink_file.fullpath,
                temporary_file,
                symlink_file.fullpath,
                "SYMLINK_CONTENT_RENAME_COMMIT",
            )
        self.wrap_interactive(f"Move the temporary file {temporary_file} to {symlink_file.fullpath}?", rename_tmp_to_final)

    def wrap_interactive(self, question, callback):
        answer = input(question + " Y/n:").lower()
        if len(answer) > 0:
            answer = answer[0]
        else:
            answer = "y"

        if answer == "y":
            callback()
            return True
        return False
