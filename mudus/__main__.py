import os
import pwd
import argparse
from pathlib import Path

import rich
from .database import MudusDatabase
from .scan import MudusScanApp, run_non_interactive_scan
from .view import MudusViewApp


def main():
    # ------------------------------------------
    # Command line argument defaults
    if "MUDUS_DB_DIR" in os.environ:
        environment_db_dir = os.environ["MUDUS_DB_DIR"]
        default_db_directory = Path(environment_db_dir)
    else:
        environment_db_dir = UNSET()
        default_db_directory = Path.home() / ".cache/mudus"

    # ------------------------------------------
    # Setup command line argument parser
    parser = argparse.ArgumentParser(
        prog="mudus", description="MUDUS TUI - Multi-User system Disk USage"
    )

    parser.add_argument(
        "-d",
        "--db-directory",
        type=Path,
        default=default_db_directory,
        help=(
            "Directory where the MUDUS database is stored."
            " You must first run a scan to create this database, then you can view it later."
            f" The default location is: {str(default_db_directory)!r}."
            " The default location can be set by the MUDUS_DB_DIR environment variable."
            f" The value of that environmental variable right now is: {environment_db_dir!r}."
        ),
    )

    parser.add_argument(
        "-u",
        "--user",
        type=str,
        default=os.getuid(),
        help=(
            "User ID or user name to show when running the 'view' command."
            " This has no effect for the scan command."
        ),
    )

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help=(
            "Run scanner in non-interactive mode, do not show the TUI, just run the scan and"
            " store the updated disk-usage database if successful."
        ),
    )

    parser.add_argument(
        "--non-root",
        action="store_true",
        help=(
            "Run scanner in non-root mode. The database will be stored without trying to hide"
            " any directory name information. The default is to store information about directory"
            " names in files that are owned by the same user and group as the directory contents."
            " When running as root you can see all directory names, some of which may be secret."
            " It is then recommended to keep the default, make sure others (not same user or group)"
            " cannot access the database files containing directory names."
            " The database never contains file names or file contents. Only directory names and"
            " cumulative (recursive) content size."
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="view",
        metavar="COMMAND",
        choices=["view", "scan"],
        help=(
            "The mudus command to run, either 'view' or 'scan'."
            " The default is 'view' if not specified."
        ),
    )

    parser.add_argument(
        "-s",
        "--scan-dir",
        type=Path,
        metavar="DIRECTORY",
        action="append",
        help="Directory to scan (you can add multiple directories)",
    )

    # ------------------------------------------
    # Parse the command line arguments
    args = parser.parse_args()
    user_id = get_user_id(args.user, parser)
    is_scan = args.command == "scan"
    database: MudusDatabase = get_database(args.db_directory, is_scan, parser)
    database.non_root_mode = args.non_root
    if is_scan:
        # Collect directories to scan
        add_directories_to_scan(database, args.scan_dir or [], parser)
    else:
        # Scan should already be done, so we load the database
        try:
            database.load_database()
        except Exception as e:
            stop_with_error(
                f"Error loading database!"
                "\n  You must first run a scan before using this command."
                f"\n  The database location is: {args.db_directory}"
                f"\n  Error during database load: {e}",
                parser,
            )

    if args.non_interactive:
        # Run the scanner in non-interactive mode
        if is_scan:
            return run_non_interactive_scan(database)
        else:
            stop_with_error("Only the scan can be run in non-interactive mode.", parser)
    else:
        # Run the normal Textual TUI (app can be the 'view' or 'scan' console applications)
        app = get_application(args.command, database, user_id, parser)
        app.run()


def get_user_id(user: str | int, parser: argparse.ArgumentParser) -> int:
    """
    Get the user ID from a user name or ID.
    """
    try:
        return int(user)
    except ValueError:
        # The user is a name, not an ID
        pass

    try:
        return pwd.getpwnam(user).pw_uid
    except KeyError:
        # The user name does not exist
        stop_with_error(f"User '{user}' not found.", parser=parser)


def get_database(db_dir: Path, is_scan: bool, parser: argparse.ArgumentParser) -> MudusDatabase:
    if is_scan and not db_dir.is_dir():
        db_dir.mkdir(parents=True, exist_ok=True)
    elif not db_dir.is_dir():
        stop_with_error(
            f"Database directory '{db_dir}' does not exist."
            "\n  You must first run a scan before using this command.",
            parser=parser,
        )
    return MudusDatabase(db_dir)


def add_directories_to_scan(
    database: MudusDatabase, dirs_to_scan: list[Path], parser: argparse.ArgumentParser
):
    for directory in dirs_to_scan:
        if not directory.is_dir():
            stop_with_error(f"Directory '{directory}' does not exist, cannot scan it!", parser)
        else:
            database.directories_to_scan.append(directory.resolve(strict=True))
    if not database.directories_to_scan:
        stop_with_error(
            "No directories to scan specified. Use --scan-dir to specify directories.", parser
        )


def get_application(
    command: str, db: MudusDatabase, user_id: int, parser: argparse.ArgumentParser
) -> MudusViewApp:
    if command == "view":
        return MudusViewApp(mudus_db=db, user_id=user_id)
    elif command == "scan":
        return MudusScanApp(mudus_db=db)
    else:
        stop_with_error(f"Unknown command: {command}", parser)


def stop_with_error(message: str, parser: argparse.ArgumentParser):
    """
    Print an error message and exit the program.
    """
    parser.print_help()
    rich.print(f"\n[red][bold]Error:[/bold] {message}[/red]")
    parser.exit(1, "Exiting due to error")


class UNSET:
    def __repr__(self):
        return "**NOT SET**"


if __name__ == "__main__":
    main()
