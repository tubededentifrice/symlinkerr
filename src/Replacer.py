import logging
import os
import shutil
import sqlite3
import time

from src.File import File


class Replacer:
    logger = logging.getLogger("Replacer")

    temporary_suffix: str = ".tmp"
    dry_run_changes: list[str] = []

    def __init__(
        self, config: dict, database: sqlite3.Connection, interactive: bool = False
    ):
        self.config: dict = config
        self.database: sqlite3.Connection = database
        self.interactive: bool = interactive

        self.dry_run: bool = config["dry-run"]
        self.add_suffix: str = config["add-suffix-instead-of-deleting"]
        self.suffix: str = config["suffix"]

        self.chown_uid = config["chown-uid"]
        self.chown_gid = config["chown-gid"]
        self.chmod = config["chmod"]

        self.create_changelog_table()

    def clear_changelog(self) -> None:
        self.database.execute("DROP TABLE IF EXISTS changelog;")
        self.create_changelog_table()  # This will do the commit()

    def create_changelog_table(self) -> None:
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS changelog (
                id INTEGER PRIMARY KEY,
                date REAL,
                fullpath VARCHAR,
                filechanged VARCHAR,
                target VARCHAR,
                action VARCHAR,
                version REAL
            );
        """)

        self.database.execute("""
            CREATE INDEX IF NOT EXISTS changelog__fullpath
            ON changelog(fullpath)
        """)

        self.database.commit()

    def log_change(
        self, fullpath: str, filechanged: str, target: str, action: str
    ) -> None:
        self.database.execute(
            "INSERT INTO changelog(date, fullpath, filechanged, target, action, version) VALUES(?, ?, ?, ?, ?, 1.0)",
            (time.time(), fullpath, filechanged, target, action),
        )
        self.database.commit()

    def is_file_a_replacement(self, file: File) -> bool:
        return file.fullpath.endswith(self.suffix) or file.fullpath.endswith(
            self.temporary_suffix
        )

    def replace_with_symlink(self, file: File, file_symlink_target: File) -> None:
        self.logger.info(
            f"Replacing {file.fullpath} with a symlink to {file_symlink_target.fullpath}"
        )
        if self.dry_run:
            self.logger.info(
                "Just kidding, not actually doing anything, we are in a dry-run!"
            )
            self.log_dry_run_change(
                f"Would have replaced {file.fullpath} with a symlink to {file_symlink_target.fullpath}"
            )
            return
        # Make the symlink in a temporary location first, then force replace the target with it, to achieve atomic replace
        temporary_file = File(file.fullpath + self.temporary_suffix)

        if temporary_file.is_file():

            def remove_existing_tmp():
                temporary_file.remove()

            if not self.wrap_interactive(
                f"Remove existing temporary file {temporary_file.fullpath}?",
                remove_existing_tmp,
            ):
                return

        def create_symlink_tmp():
            self.log_change(
                file.fullpath,
                temporary_file.fullpath,
                file_symlink_target.fullpath,
                "CREATE_TEMP_SYMLINK_START",
            )
            os.symlink(file_symlink_target.fullpath, temporary_file.fullpath)
            self.log_change(
                file.fullpath,
                temporary_file.fullpath,
                file_symlink_target.fullpath,
                "CREATE_TEMP_SYMLINK_COMMIT",
            )

            self.chown(temporary_file)

        if not self.wrap_interactive(
            f"Create symlink {temporary_file.fullpath} ==> {file_symlink_target.fullpath}?",
            create_symlink_tmp,
        ):
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

            if not self.wrap_interactive(
                f"Rename {file.fullpath} to {rename_existing_to}?",
                rename_existing_to_bak,
            ):
                return

        def replace_with_symlink():
            self.log_change(
                file.fullpath,
                file.fullpath,
                file_symlink_target.fullpath,
                "MOVE_SYMLINK_START",
            )
            shutil.move(temporary_file.fullpath, file.fullpath)
            self.log_change(
                file.fullpath,
                file.fullpath,
                file_symlink_target.fullpath,
                "MOVE_SYMLINK_COMMIT",
            )

        if not self.wrap_interactive(
            f"Replace {file.fullpath} with its symlink to {file_symlink_target.fullpath}?",
            replace_with_symlink,
        ):
            return

    def replace_with_content(self, symlink_file: File) -> None:
        self.logger.info(
            f"Replacing {symlink_file.fullpath} with its content from {symlink_file.get_readlink()}"
        )
        if self.dry_run:
            self.logger.info(
                "Just kidding, not actually doing anything, we are in a dry-run!"
            )
            self.log_dry_run_change(
                f"Would have replaced {symlink_file.fullpath} with its content from {symlink_file.get_readlink()}"
            )
            return

        temporary_file = File(symlink_file.fullpath + self.temporary_suffix)
        if temporary_file.is_file():

            def remove_existing_tmp():
                temporary_file.remove()

            if not self.wrap_interactive(
                f"Remove existing temporary file {temporary_file.fullpath}?",
                remove_existing_tmp,
            ):
                return

        def copy_content_to_tmp():
            self.log_change(
                symlink_file.fullpath,
                temporary_file.fullpath,
                symlink_file.get_readlink(),
                "SYMLINK_COPY_CONTENT_START",
            )
            shutil.copy(symlink_file.fullpath, temporary_file.fullpath)
            self.log_change(
                symlink_file.fullpath,
                temporary_file.fullpath,
                symlink_file.get_readlink(),
                "SYMLINK_COPY_CONTENT_COMMIT",
            )

            self.chown(temporary_file)

        if not self.wrap_interactive(
            f"Copy the content of {symlink_file.fullpath} to {temporary_file.fullpath}?",
            copy_content_to_tmp,
        ):
            return

        # TODO: Shall we check the hashes are matching?
        # At least, check that the size is correct
        if temporary_file.get_size() != symlink_file.get_size():
            self.logger.warn(
                f"Replacing {symlink_file.fullpath} content from {symlink_file.get_readlink()} failed: sizes after copy are different. "
                + f"Temporary file size is {temporary_file.get_size()} bytes but we were expecting {symlink_file.get_size()} bytes (difference: {symlink_file.get_size() - temporary_file.get_size()} bytes). "
                + "Removing the temporary file and not proceeding further with that file."
            )
            temporary_file.remove()
            return

        def rename_tmp_to_final():
            self.log_change(
                symlink_file.fullpath,
                temporary_file.fullpath,
                symlink_file.fullpath,
                "SYMLINK_CONTENT_RENAME_START",
            )
            shutil.move(temporary_file.fullpath, symlink_file.fullpath)
            self.log_change(
                symlink_file.fullpath,
                temporary_file.fullpath,
                symlink_file.fullpath,
                "SYMLINK_CONTENT_RENAME_COMMIT",
            )

        self.wrap_interactive(
            f"Move the temporary file {temporary_file.fullpath} to {symlink_file.fullpath}?",
            rename_tmp_to_final,
        )

    def chown(self, file: File):
        os.chown(file.fullpath, self.chown_uid, self.chown_gid)
        os.chmod(file.fullpath, int(str(self.chmod), base=8))

    def wrap_interactive(self, question: str, callback) -> bool:
        if not self.interactive:
            callback()
            return True

        answer = input(question + " Y/n:").lower()
        if len(answer) > 0:
            answer = answer[0]
        else:
            answer = "y"

        if answer == "y":
            callback()
            return True
        return False

    def log_dry_run_change(self, change: str) -> None:
        self.dry_run_changes.append(change)

    def print_and_delete_dry_run_change(self) -> None:
        if self.dry_run:
            changes = self.get_and_delete_dry_run_change()
            if len(changes) > 0:
                print("** Changes that would have been performed without the dry-run: **")
                for change in self.get_and_delete_dry_run_change():
                    print("    " + change)
            else:
                print("** No change would have been performed without the dry-run **")

    def get_and_delete_dry_run_change(self) -> list[str]:
        changes = self.dry_run_changes
        self.dry_run_changes = []
        return changes
