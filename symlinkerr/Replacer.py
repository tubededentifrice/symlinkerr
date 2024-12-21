import sqlite3
import logging


class Replacer():


    def __init__(self, watch_directories, symlink_target_directories):
        self.watch_directory = watch_directory
        self.symlink_target_directory = symlink_target_directory
