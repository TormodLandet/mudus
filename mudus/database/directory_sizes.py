from __future__ import annotations
from pathlib import Path
import json


class DirectorySizes:
    def __init__(
        self,
        dir_sizes: dict[str, int],
        num_files: dict[str, int],
        dir_children: dict[str, set[str]],
        top_level_dir: str = "/",
    ):
        #: Mapping from path-string to num bytes (int)
        self.dir_sizes: dict[str, int] = dir_sizes

        #: Mapping from path-string to num files (int)
        self.num_files: dict[str, int] = num_files

        #: Mapping from path-string to list of path-strings
        self.dir_children: dict[str, set[str]] = dir_children

        #: The directory which is the first interesting directory.
        #: It may be "/beegfs/projects" instead of "/beegfs" or "/"
        #: if the user has no files or directories in "/beegfs" except
        #: under the "/beegfs/projects" directory.
        #: It then makes sense to start the viewer inside this directory.
        self.top_level_dir: str = top_level_dir

    @classmethod
    def empty(cls) -> DirectorySizes:
        return cls(dir_sizes={}, num_files={}, dir_children={})

    @property
    def total_size(self) -> int:
        """
        The total cumulative size of the top-level directory.
        """
        return self.dir_sizes[self.top_level_dir]

    @property
    def has_data(self) -> bool:
        return self.total_size > 0

    def find_root_directory(self) -> str:
        """
        Find the root directory the one that has no parents

        Assumes that there is one root directory, typically "/",
        or that only one disk drive is scanned (on windows)
        """
        if not self.dir_sizes:
            raise ValueError("No directory sizes available, cannot find the root directory!")

        shortest_path_length = 10_000  # Arbitrary max file system path length
        for dir_name in self.dir_sizes:
            path_length = len(dir_name)
            if path_length < shortest_path_length:
                shortest_path_length = path_length
                root_directory = dir_name
        return root_directory

    def find_top_level_dir(self) -> str:
        """
        Find the top-level directory (the one that has different size that its children)
        """
        root = self.find_root_directory()
        top_level_dir = root
        while True:
            children = self.children(top_level_dir)
            if len(children) != 1:
                break
            child_size, child = next(iter(children))
            if self.dir_sizes[top_level_dir] != child_size:
                break

            # The child is the only child of the top-level directory
            # and its size is the same as the top-level directory,
            # so we can continue to traverse down
            top_level_dir = child

        self.top_level_dir = top_level_dir
        return top_level_dir

    def children(self, dir_name: str) -> list[tuple[str, int]]:
        """
        Child directories of the given directory, sorted by size in descending order.
        """
        children = self.dir_children.get(dir_name, set())
        size_of_children = [(self.dir_sizes[child], child) for child in children]
        return sorted(size_of_children, reverse=True)

    def write(self, filename: str | Path):
        """
        Write the directory sizes to a JSON file.
        """
        me_as_dict = {
            "dir_sizes": self.dir_sizes,
            "num_files": self.num_files,
            "dir_children": {k: list(v) for k, v in self.dir_children.items()},
            "top_level_dir": self.top_level_dir,
        }
        if isinstance(filename, (str, Path)):
            # The filename is a string or Path
            with open(filename, "w") as f:
                json.dump(me_as_dict, f)
        else:
            # Assuming that filename is a file-like object
            json.dump(me_as_dict, filename)

    @classmethod
    def from_file(cls, filename: str | Path) -> DirectorySizes:
        """
        Load the directory sizes from a JSON file.
        """
        with open(filename, "r") as f:
            data = json.load(f)
        return cls(
            dir_sizes=data["dir_sizes"],
            num_files=data["num_files"],
            dir_children={k: set(v) for k, v in data["dir_children"].items()},
            top_level_dir=data.get("top_level_dir", "/"),
        )
