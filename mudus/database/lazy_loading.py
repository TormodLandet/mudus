from pathlib import Path
import json
import grp
import pwd

from .directory_sizes import DirectorySizes


class LazyLoadingDirectorySizes:
    def __init__(self, datafile: Path, uid: int, gid: int):
        """
        A placeholder for DirectorySizes objects that have not yet
        been loaded from disk (belonging to other users, not the
        user that is currently looking at the database etc)
        """
        self.datafile: Path = datafile
        self.uid: int = uid
        self.gid: int = gid

    def load(self) -> tuple[DirectorySizes | None, str]:
        """
        Load the directory sizes from disk
        Return the object (or None if not loadable)

        Returns a string with the reason why the object is None if
        the file could not be loaded, otherwise this string is empty
        """
        reason_for_error: str = ""
        try:
            return DirectorySizes.from_file(self.datafile), reason_for_error
        except PermissionError:
            reason_for_error = "Permission denied, cannot read file"
        except FileNotFoundError:
            reason_for_error = "File not found"
        except json.JSONDecodeError:
            reason_for_error = "Corrupted JSON data"
        except Exception as e:
            reason_for_error = f"Unknown error loading: {e}"

        # Construct a more easily understood reason for the error
        reason_for_error = f"Cannot load directory sizes: {reason_for_error}"
        try:
            username = repr(pwd.getpwuid(self.uid).pw_name)
        except KeyError:
            username = "**UNKNOWN USER**"
        reason_for_error += f"\n  Owner: {username} (UID={self.uid})"

        try:
            groupname = repr(grp.getgrgid(self.gid).gr_name)
        except KeyError:
            groupname = "**UNKNOWN GROUP**"
        reason_for_error += f"\n  Group: {groupname} (GID={self.gid})"

        reason_for_error += f"\n  Datafile: {self.datafile}"
        return None, reason_for_error
