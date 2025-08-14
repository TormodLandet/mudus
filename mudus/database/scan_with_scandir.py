from pathlib import Path
import os

from mudus.database import MudusDatabase


def scan_directory_with_scandir(db: MudusDatabase, directory: Path):
    directories = [str(directory)]
    while directories:
        if db.cancel_scan:
            return

        # Get the next directory to scan
        current_dir = directories.pop()
        db.current_scan_item = current_dir

        # Scan this directory. Scanning will append any sub-directories
        # to the list of directories to scan.
        # If the directory does not exist or cannot be accessed, it will be skipped.
        try:
            scan_one_directory(db, current_dir, directories)
        except PermissionError:
            db.report_error(directory=current_dir, error="Permission denied")
        except FileNotFoundError:
            db.report_error(directory=current_dir, error="Directory not found")
        except Exception as e:
            db.report_error(directory=current_dir, error=f"Other error: {e}")



def scan_one_directory(db: MudusDatabase, directory: str, directories: list[str]):
    """
    Scan a directory and accumulate the size of files by user ID
    in the SQLite database.
    """
    with os.scandir(directory) as it:
        file_size_for_dir: dict[tuple[int, int], int] = {}
        num_files_for_dir: dict[tuple[int, int], int] = {}
        num_files: int = 0
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                directories.append(entry.path)
            elif entry.is_file(follow_symlinks=False):
                uid = entry.stat().st_uid
                gid = entry.stat().st_gid
                key = (uid, gid)
                size = entry.stat().st_size
                file_size_for_dir[key] = file_size_for_dir.get(key, 0) + size
                num_files_for_dir[key] = num_files_for_dir.get(key, 0) + 1
                num_files += 1

    db.num_scanned_files += num_files
    db.num_scanned_directories += 1

    # Update the database with the directory data
    for (uid, gid), size in file_size_for_dir.items():
        num_files = num_files_for_dir[uid, gid]
        db.scan_results.setdefault((uid, gid), []).append((directory, size, num_files))
