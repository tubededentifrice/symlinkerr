_Like this app? Thanks for giving it a_ ⭐️

# ** Symlinkerr **
Replace files in given directories with symlinks to another -- eg. a remote share -- to save local storage.

## Table of contents

-   [Features](#features)
-   [How that works?](#how-that-works)
-   [Dependencies](#dependencies)
-   [Configuration](#configuration)
-   [Run](#run)
-   [Contributing](#contributing)
-   [Bug reports](#bug-reports)
-   [TODO](#todo)
-   [Disclaimer](#disclaimer)

## Features

Extensive but simple configuration allows to configure watched directories, for which:
- You want some content replaced with symlinks (to provide deduplication, or linking to an external system)
- Or, to the opposite, you want the symlinks to be replaced with actual content (eg. for archival / long term storage)

Typical use case is when you have a bunch of files downloaded through RD and have a mount of RD through [Zurg](https://github.com/debridmediamanager/zurg-testing) and [Rclone](https://github.com/debridmediamanager/zurg-testing/blob/main/docker-compose.yml).
You might want to actually download the files first for fast, local analysis (extracting subtitles, etc.), but don't want to bear the cost of long term storage: Symlinkerr will replace those files with symlinks to the remote once you're done.

And you might have a library of things you really liked that you want to keep local, so Symlinkerr will also allow you to unwind those symlinks, by simply moving the root path of the content you wish to keep.

It has an interactive mode (`-i` flag) which will ask you confirmation before performing any write, but this is probably less useful than the `dry-mode`. Always run a `dry-mode` after adding new watched directories and review the changes it prints at the end.

## How that works?

In the config, you set up a bunch of directories to monitor:
- `symlink-target-directories` where to point the symlinks to (ie. your WebDav mount or other remote mount)
- `watch-directories` in which directories you want to browse for duplicates
- `undo-all-symlinks-directories` the directories where you want to unwind the symlinks, replacing them with actual content

First, it indexes the files present in `symlink-target-directories` (name and size).
For the symlink replacement, while iterating over the content of `watch-directories`, it will try to find candidate by SIZE and/or FILENAME in `symlink-target-directories`.
When suitable replacements are found, it will iterate over them and check their hash actually match the original file, and if so will perform the replacement.
The hashes are stored in the database, so they will only be computed once, as this is a very expensive operation. Hashes are invalidated if modification time or size is changed.

All actions performed are logged in the database (`changelog` table), and *should* be performed in a safe way (using temporary files for non-atomic operations).

Always start with a dry-run first, as it will print out what it would have done. This will take a very long time though, as it will compute hashes, but those hashes will be cached in the database, so the next run will be much faster.
Some mounts aren't properly persisting the modification time, so set the config option `change-in-mtime-invalidates-hash` to `false` if you notice it recomputing hashes it shouldn't. If file size changes, it will always recompute the hash.

## Dependencies

** This has not been tested on Windows and is very unlikely to work. **
Very minimal dependencies are required except for a recent version of Python (3.10+) and PYYAML. Everything else should be in base Python 3.

Install them on Debian/Ubuntu with:
```
apt update && apt install python3 python3-yaml
```

## Configuration

Look at the [configuration defaults](https://github.com/tubededentifrice/symlinkerr/blob/main/config_default.yml), which has comments for everything.
Those can/should be overriden in your own config.yml -- your values will take over whatever is in the default.

## Run

The default config -- `config_default.yml` -- is using those directories, you will need to change that to suit your own needs.
Duplicate that file onto `config.yml` and make your changes.
```
finder:
  directories:
    # Directories where we will delete files and replace them with symlinks
    watch-directories:
      - dir: "/data/media/movies"

    # Directories where we will try to find replacements
    # Only files with the exact same size will be eligible.
    # After finding a candidate, the hash of both files will be computed to ensure they are indeed identical (and accessible!)
    # In case the file is found in multiple targets, the top priority will be used (ie. the lowest)
    # If there is still multiple matching candidates, a random one will be chosen
    # It is VERY important those paths are mounted to the same places everywhere (host, containers, etc.), otherwise they won't resolve properly accross apps
    symlink-target-directories:
      - dir: "/mnt/remotes/rclone/zurg/__downloads__"
        priority: 1
      - dir: "/mnt/remotes/rclone/zurg/__all__"
        priority: 2

    # Symlinks in this folder will be replaced by the content at the target of the symlink
    # Eg. this is the things you actually want to store locally, if you are happy with the content
    # Must obviously NOT be with the watch-directories, otherwise it will replace with a symlink, then replace that symlink with content, etc.
    undo-all-symlinks-directories:
      - dir: "/data/media/movies-i-like"
```

### Docker

Docker is the recommended way to go. Mount a persistent storage at /config (where your config and database will be stored).
Mount the directories you want to watch/rewrite and the symlink target.
The app will be in /app and you can run command manually from there. The entrypoint is the watcher, so it will be running in a loop.
Config is reloaded at each run, without restarting the container.

**It's very important the symlink target paths are the same accross all your containers, and even host!**
If not, you'll end with dead symlinks. The target of the symlinks also needs to be mounted on all containers that needs to access the content of the files.

### Bare metal

The default config file will be `config.yml` in the current directory (override with `-c /path/to/config.yml`). If the file doesn't exist, the first run will create it. Or do it yourself by copying `config_default.yml` and changing settings beforehand.
The default config runs in a `dry-run`, so won't actually be doing anything, and put the database in `/config/symlinkerr.sqlite`, so you'll most probably want to change that as well.

## Contributing

The code base is very small and easy to understand. I will happily review PRs.
It has few main components:
- `Indexer` which looks at the files in the target directories and put them in the database, so candidates are very quickly found
- `Finder` which iterates over the files in the watched directories
- `Checker` which checks if the candidates are matching all the requirements
- `Replacer` which actually performs the replacement operations

## Bug reports

Set logger level to DEBUG in the config and paste the relevant logs.
```
logger:
  level: DEBUG
```

## TODO

[] Update symlinks with new paths (eg. the mount directory has changed)
[] Changelog viewer

## Disclaimer

This script comes free of any warranty, and you are using it at your own risk.
Dude, this deletes stuff, so be careful!
