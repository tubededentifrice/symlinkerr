
class Replacer:
    
    
    def __init__(self, config, database):
        self.config = config
        self.database = database

        self.dry_run = config["dry-run"]
