import re

class Checker:
    def __init__(self, config, database):
        self.config = config
        self.database = database

        self.check_filesize = config["check-filesize"]
        self.check_hash = config["check-hash"]
        self.check_filename = config["check-filename"]
        self.exclude_watch_directories = [re.compile(r) for r in config["exclusions"]["watch-directories-regexes"]]
        self.exclude_target_directories = [re.compile(r) for r in config["exclusions"]["symlink-target-directories-regexes"]]

    def is_eligible_for_replacement(fullpath):
        return True

    def can_be_replaced_with(original_fullpath, replacement_fullpath):
        return False

    def get_hash(fullpath):
        pass