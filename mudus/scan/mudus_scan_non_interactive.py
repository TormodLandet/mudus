import threading
import time
import sys

import rich

from mudus.database import MudusDatabase


class ScanThread(threading.Thread):
    def __init__(self, mudus_db: MudusDatabase):
        super().__init__()
        self.mudus_db = mudus_db

    def run(self):
        self.mudus_db.run_file_system_scan()


def run_non_interactive_scan(mudus_db: MudusDatabase):
    """
    Run the scan in non-interactive mode.
    """
    print()
    rich.print("[cyan]MUDUS file-system scan[/]")
    rich.print("[cyan]======================[/]\n")
    rich.print("  Directories to scan:")
    for directory in mudus_db.directories_to_scan:
        rich.print("  -", directory)
    rich.print("  Database directory: ", mudus_db.db_directory)
    rich.print("  Non-root mode:      ", mudus_db.non_root_mode)

    rich.print("\nStarting to scan ... this make take a while\n")

    def print_status():
        # Information about errors encountered during the scan
        error_message = f"\n  Number of errors: {len(mudus_db.errors)}"
        if mudus_db.errors:
            last_error = mudus_db.errors[-1]
            error_message = (
                f"[red]{error_message}"
                f"\n    Last error: {last_error[1]}"
                f"\n    Error path: {last_error[0]}"
                "[/]"
            )

        current_scan_item = mudus_db.current_scan_item or "unknown"
        rich.print(
            f"[green]Scanned {mudus_db.num_scanned_files:,d} files"
            f" and {mudus_db.num_scanned_directories:,d} directories so far[/]"
            f"\n  Now scanning: {current_scan_item}"
            f"{error_message}\n"
        )

    # Run the scanner in a separate thread so that we can easily decide the
    # output-frequency. This is also how the Texual TUI runs the scanner
    # (using a worker thread), so it keeps the code similar.
    thread = ScanThread(mudus_db)
    thread.start()

    # Wait for the scanner to complete (or Ctrl+C or another Exception)
    try:
        while thread.is_alive():
            time.sleep(5)
            print_status()
        print(f"\nDONE in {mudus_db.scanning_duration:.2f} seconds.")
    except KeyboardInterrupt:
        rich.print("\n[yellow]Scan cancelled by user.[/]\n\nSHUTTING DOWN ...")
        mudus_db.cancel_scan = True
        thread.join()  # Wait for the scan thread to cancel
        sys.exit(8)
    except Exception as e:
        rich.print(f"\n[red]Got unexpected ERROR: {e}[/]\n\nSHUTTING DOWN ...")
        mudus_db.cancel_scan = True
        thread.join()  # Wait for the scan thread to cancel
        sys.exit(9)
