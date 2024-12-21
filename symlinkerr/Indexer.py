import logging
import os
from symlinkerr.File import File

"""
Find all the files in the target directories and put them into the database.
"""


class Indexer:
    logger = logging.getLogger("Indexer")

    def __init__(self, config, target_directories, database, min_size=0):
        self.config = config
        self.target_directories = target_directories
        self.database = database
        self.min_size = min_size

        self.followlinks = self.config["followlinks"]

    def index_target_directories(self):
        # Recreate the indexing table
        self.database.execute("DROP TABLE IF EXISTS index_target_directories;")
        self.database.execute("""
            CREATE TABLE index_target_directories (
                fullpath VARCHAR PRIMARY KEY,
                filename VARCHAR,
                size LONG,
                priority INTEGER
            );
        """)

        for directory in self.target_directories:
            self.logger.info(f"Indexing target directory {directory}")
            self.index_directory(directory["dir"], directory["priority"])

        self.database.commit()

    def index_directory(self, path, priority):
        for root, dirs, files in os.walk(path, followlinks=self.followlinks):
            for filename in files:
                fullpath = os.path.join(root, filename)
                file = File(fullpath)
                if file.get_size() >= self.min_size:
                    self.logger.debug(
                        f"Found file with size {file.get_size()}: {fullpath}"
                    )
                    self.database.execute(
                        "INSERT OR IGNORE INTO index_target_directories(fullpath, filename, size, priority) VALUES(?, ?, ?, ?)",
                        (fullpath, filename, file.get_size(), priority),
                    )
                else:
                    self.logger.debug(
                        f"Ignoring file with size {file.get_size()}: {fullpath} as it's lower than the minimum threshold of {self.min_size}"
                    )

    def get_candidates_by_size_and_filename(self, size, filename):
        return self.fetch_to_array(self.database.execute(
            f"SELECT fullpath FROM index_target_directories WHERE size={size} AND filename=? ORDER BY priority",
            (filename,),
        ))

    def get_candidates_by_size(self, size):
        return self.fetch_to_array(self.database.execute(
            f"SELECT fullpath FROM index_target_directories WHERE size={size} ORDER BY priority"
        ))

    def get_candidates_by_filename(self, filename):
        return self.fetch_to_array(self.database.execute(
            "SELECT fullpath FROM index_target_directories WHERE filename=? ORDER BY priority",
            (filename,),
        ))

    def fetch_to_array(self, cursor):
        return [
            c[0]
            for c in cursor.fetchall()
        ]
