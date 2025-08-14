from __future__ import annotations
from typing import TYPE_CHECKING
import os

from .directory_sizes import DirectorySizes

if TYPE_CHECKING:
    from mudus.database import MudusDatabase


def accumulate_directory_sizes(
    mudus_db: MudusDatabase, data: list[tuple[str, int, int]]
) -> DirectorySizes:
    """
    Accumulate directory sizes from the scan results.


    After accumulation the size of a directory should include the size of all files in that
    directory, and all files in all sub-directories recursively.
    """
    # Get data sorted by path length so child directories are seen before their parents
    # This allows us to accumulate sizes correctly
    data.sort(key=lambda x: len(x[0]), reverse=True)

    # Identify directory sizes and the names of their children directories
    # This can take 10 seconds or more, depending on the size of the database
    user_dir_children: dict[str, set[str]] = {}
    users_dir_cumulative_sizes: dict[str, int] = {}
    users_dir_cumulative_numfiles: dict[str, int] = {}
    for path, size, numfiles in data:
        # Size of this directory - only direct children (files not in sub-directories)
        users_dir_cumulative_sizes[path] = size + users_dir_cumulative_sizes.get(path, 0)
        users_dir_cumulative_numfiles[path] = numfiles + users_dir_cumulative_numfiles.get(path, 0)

        # Identify parent directories by traversing up the path
        parent = path
        while True:
            child = parent
            parent = os.path.split(child)[0]

            if parent == child:
                # Stop when we reach the top-level directory
                break
            elif parent not in users_dir_cumulative_sizes:
                # New parent directory, initialize it
                users_dir_cumulative_sizes[parent] = 0
                users_dir_cumulative_numfiles[parent] = 0
                user_dir_children[parent] = set()
            
            # Add the child directory to the parent's children and accumulate its size
            user_dir_children[parent].add(child)
            users_dir_cumulative_sizes[parent] += size
            users_dir_cumulative_numfiles[parent] += numfiles

        if mudus_db.cancel_scan:
            break

    return DirectorySizes(
        dir_sizes=users_dir_cumulative_sizes,
        num_files=users_dir_cumulative_numfiles,
        dir_children=user_dir_children,
    )
