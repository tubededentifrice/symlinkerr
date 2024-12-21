class Indexer:
    def __init__(self, target_directories, database):
        self.target_directories = target_directories
        self.database = database

    def index(self):
        # Recreate the indexing table
        self.database.execute("DROP TABLE IF EXISTS index_target_directories;")
        self.database.execute("""
            CREATE TABLE index_target_directories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directory VARCHAR,
                filepath VARCHAR,
                filename VARCHAR,
                size INTEGER
            );
        """)
