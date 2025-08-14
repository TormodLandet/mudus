from typing import Literal
from pathlib import Path
from enum import Enum
import datetime as dt
import json
import os

from .directory_sizes import DirectorySizes
from .accumulate import accumulate_directory_sizes


METADATA_FILE_NAME = "scan_metadata.json"
CUMULATIVE_DIR_NAME = "cumulative_by_uid_gid"


class ScanningMethod(Enum):
    SCANDIR = "scandir"


class MudusDatabase:
    def __init__(self, db_directory: Path):
        self.db_directory: Path = db_directory
        self.directories_to_scan: list[Path] = []
        self.message: str = ""

        # How to scan and store the results
        self.scanning_method: ScanningMethod = ScanningMethod.SCANDIR
        self.non_root_mode: bool = False  # If True, do not hide directory names in the database

        # Data updated by the file-system scanner
        self.current_scan_item: str = ""
        self.is_scanning: bool = False
        self.cancel_scan: bool = False
        self.num_scanned_directories: int = 0
        self.num_scanned_files: int = 0
        self.errors: list[tuple[str, str]] = []  # list of (directory, error_message)

        # Mapping user (uid, gid) tuple to list of (path, size, numfiles) tuples
        # where path is the directory path, size is the total size of files in that directory,
        # and numfiles is the number of files in that directory.
        # STAGE 1: These data are non-cumulative
        self.scan_results: dict[tuple[int, int], list[tuple[str, int, int]]] = {}
        # STAGE 2: These data are cumulative per user and group
        self.cumulative_results: dict[tuple[int, int], DirectorySizes] = {}

        self.scanning_start_time: dt.datetime
        self.accumulation_start_time: dt.datetime
        self.scanning_end_time: dt.datetime
        self.scanning_duration: float = 0.0

    def load_database(self):
        """
        Load the database from the file system
        (no scanning, just reading result from prior scan).
        """
        # Load the scan results (only cumulative results)
        result_storage_dir = self.db_directory / CUMULATIVE_DIR_NAME
        for file in result_storage_dir.glob("cumulative_dir_sizes_for_uid_*.json"):
            uid, gid = parse_uid_and_gid_from_filename(file.name)
            if uid is None or gid is None:
                continue
            self.cumulative_results[(uid, gid)] = DirectorySizes.from_file(file)

        # Load metadata about the scan
        metadata_file = self.db_directory / METADATA_FILE_NAME
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        self.scanning_method = ScanningMethod(metadata["scanning_method"])
        self.non_root_mode = metadata["non_root_mode"]
        self.scanning_start_time = dt.datetime.fromisoformat(metadata["scanning_start_time"])
        self.accumulation_start_time = dt.datetime.fromisoformat(
            metadata["accumulation_start_time"]
        )
        self.scanning_end_time = dt.datetime.fromisoformat(metadata["scanning_end_time"])
        self.scanning_duration = metadata["scanning_duration"]
        self.directories_to_scan = [Path(d) for d in metadata["directories_to_scan"]]
        self.message = metadata["message"]
        self.errors = metadata["errors"]

    def save_database(self):
        """
        Save the database to the file system
        (no scanning, just writing current state).
        """
        result_storage_dir = self.db_directory / CUMULATIVE_DIR_NAME
        result_storage_dir.mkdir(parents=True, exist_ok=True)

        # Delete old database contents. We must prevent that user-group combinations that once
        # were present on the file system will remain when they are no longer present since the
        # file will not be overwritten if there is no new data.
        for file in result_storage_dir.glob("cumulative_dir_sizes_for_uid_*.json"):
            # Will this file be overwritten by the code below?
            uid, gid = parse_uid_and_gid_from_filename(file.name)
            if (uid, gid) in self.cumulative_results:
                # This file will be overwritten below. Do not prematurely remove it
                continue
            else:
                # The file contains information about a user-group combination that no longer
                # owns any files in the scanned directories. Remove this database file
                try:
                    file.unlink()
                except PermissionError:
                    self.errors.append(
                        (str(file), "Permission denied deleting old result file. Are you not root?")
                    )
                except Exception as e:
                    self.errors.append((str(file), f"Error deleting old result file: {e}"))

        # Save the scan results (only cumulative results)
        for (uid, gid), dirsize in self.cumulative_results.items():
            filename = result_storage_dir / f"cumulative_dir_sizes_for_uid_{uid}_gid_{gid}.json"
            try:
                delete_file = True
                if self.non_root_mode:
                    # Normal-user mode: assume the directory names are not sensitive information.
                    #   Just save the database contents with whatever user, group, and permissions
                    #   are currently the default for the user that is running the scan
                    with open(filename, "w") as f:
                        # Write the database contents to the file
                        dirsize.write(f)
                        # We succeeded without raising exceptions, do not delete the file
                        delete_file = False
                else:
                    # Root-mode: more secure data storage
                    #   Do not leak list of (potentially) secret directory names to other users
                    #   IMPORTANT: Requires running the scanner as root (or as the user who owns
                    #   the files, otherwise chown and chmod will fail)
                    with open(filename, "w") as f:
                        # Make file non-readable to "others" before we store any information there
                        # File is owned by the same user and group as the directory contents
                        os.fchown(f.fileno(), uid, gid)
                        # File is readable for owner and group only, no permission for others
                        os.fchmod(f.fileno(), 0o640)
                        # Write the database contents to the file
                        dirsize.write(f)
                        # We succeeded without raising exceptions, do not delete the file
                        delete_file = False
            except PermissionError:
                # If we cannot write the file, skip it
                # This can happen if the user does not have permission to access the directory
                self.errors.append(
                    (str(filename), "Permission denied writing result file. Are you not root?")
                )
            except Exception as e:
                self.errors.append((str(filename), f"Error writing result file: {e}"))

            if delete_file:
                # Do not leave files with size=0 in the result directory
                try:
                    filename.unlink()
                except Exception as e:
                    self.errors.append(
                        (str(filename), f"Error deleting result file after failed write: {e}")
                    )

        # Save metadata about the scan
        metadata = {
            "scanning_method": self.scanning_method.value,
            "non_root_mode": self.non_root_mode,
            "scanning_start_time": self.scanning_start_time.isoformat(),
            "accumulation_start_time": self.accumulation_start_time.isoformat(),
            "scanning_end_time": self.scanning_end_time.isoformat(),
            "scanning_duration": self.scanning_duration,
            "directories_to_scan": [str(d) for d in self.directories_to_scan],
            "message": self.message,
            "errors": self.errors,
        }
        with open(self.db_directory / METADATA_FILE_NAME, "w") as f:
            json.dump(metadata, f)

    def lookup_directory_sizes(self, uid: int, gid: int | Literal["all"]) -> DirectorySizes:
        """
        Lookup the directory sizes for a given user ID and group ID.
        If gid is "all", return the sizes for all groups of the user.
        If no data is found, return None.
        """
        result = DirectorySizes.empty()

        # The group IDs to look up
        gids = set()
        if gid == "all":
            # Find all group IDs for the user in the database
            for db_uid, db_gid in self.cumulative_results:
                if db_uid == uid:
                    gids.add(db_gid)
        elif (uid, gid) in self.cumulative_results:
            gids = {gid}
        else:
            return result

        # Accumulate the directory sizes for all requested groups
        for gid in gids:
            dirsize = self.cumulative_results[(uid, gid)]
            for path, size in dirsize.dir_sizes.items():
                result.dir_sizes[path] = result.dir_sizes.get(path, 0) + size
            for path, num_files in dirsize.num_files.items():
                result.num_files[path] = result.num_files.get(path, 0) + num_files
            for path, children in dirsize.dir_children.items():
                result.dir_children[path] = result.dir_children.get(path, set()).union(children)

        # Update the name of the top-level directory
        result.find_top_level_dir()

        return result

    def run_file_system_scan(self):
        """
        Perform the file system scan.
        This can take a long time ...
        """
        self.is_scanning = True
        self.cancel_scan = False
        self.errors.clear()

        # Scan the file system
        self.scanning_start_time = dt.datetime.now()
        self.message = f"Scanning started at {self.scanning_start_time.isoformat()}"
        for directory in self.directories_to_scan:
            self._scan_directory(directory)
            if self.cancel_scan:
                break

        # Compute cumulative directory sizes and file counts
        self.accumulation_start_time = dt.datetime.now()
        self.message = f"Accumulating results {self.accumulation_start_time.isoformat()}"
        self._accumulate_results()

        # Finalize the scan
        self.is_scanning = False
        self.scanning_end_time = dt.datetime.now()
        self.scanning_duration = (self.scanning_end_time - self.scanning_start_time).total_seconds()
        if self.cancel_scan:
            self.message = f"Scanning cancelled at {self.scanning_end_time.isoformat()}"
        else:
            self.message = f"File system scan completed at {self.scanning_end_time.isoformat()}"
            self.save_database()

    def _scan_directory(self, directory: Path):
        """
        Scan one of the given root directories (there are typically only one or a couple of them).

        The scanning method implementation is the one that actually loops over the whole file-system
        directory hierarchy.
        """
        if self.scanning_method == ScanningMethod.SCANDIR:
            from mudus.database.scan_with_scandir import scan_directory_with_scandir

            scan_directory_with_scandir(self, directory)

    def _accumulate_results(self):
        """
        Accumulate the results from the scan_results into cumulative_results.
        This is called after the scanning is done.
        It can take a while, but hopefully not as long as the scanning itself.
        """
        for (uid, gid), entries in self.scan_results.items():
            if self.cancel_scan:
                return
            dirsize: DirectorySizes = accumulate_directory_sizes(self, entries)
            self.cumulative_results[(uid, gid)] = dirsize

    def report_error(self, directory: str, error: str):
        """
        Report an error that occurred during the scan.
        This will be displayed in the UI.
        """
        self.errors.append((directory, error))


def parse_uid_and_gid_from_filename(filename: str) -> tuple[int | None, int | None]:
    """
    Parse a filename on the format

      f"cumulative_dir_sizes_for_uid_{uid}_gid_{gid}.json"

    And return the two integers uid and gid.
    Returns None for both if the file name is not parsable.
    """
    if not filename.startswith("cumulative_dir_sizes_for_uid_") or not filename.endswith(".json"):
        return None, None

    # Split into list ["cumulative", "dir", "sizes", "for", "uid", UID, "gid", GID]
    words = filename.split(".")[0].split("_")
    if len(words) != 8:
        # Not the expected format
        return None, None

    # Parse the UID and GID as integers
    try:
        uid = int(words[5])
        gid = int(words[7])
    except ValueError:
        return None, None

    return uid, gid
