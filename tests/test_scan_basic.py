from pathlib import Path
import os
import shutil

from mudus.database import MudusDatabase


def test_basic_scan(tmp_path: Path):
    """
    A basic test of the database (scan + write + read)
    """
    test_dir = tmp_path / "test_dir"
    make_test_dir(test_dir)
    test_dir = test_dir.resolve(strict=True)

    # Create database (scan + write to disk)
    db_dir = tmp_path / "mudus_db"
    db = MudusDatabase(db_dir)
    db.directories_to_scan = [str(test_dir)]
    db.run_file_system_scan()

    # Delete the created test files (not needed further since
    # when we have the database). We can now ensure that the
    # db is used below without scanning the file system.
    shutil.rmtree(test_dir)

    # Read database from disk (without scan)
    db = MudusDatabase(db_dir)
    db.load_database()

    # Check the database
    assert len(db.cumulative_results) == 1
    dirsize, error = db.lookup_directory_sizes(uid=os.getuid(), gid="all")
    assert error == ""

    # Check the directory sizes
    assert dirsize.top_level_dir == str(test_dir)
    expected_size = 100 + 1000 + 200 + 500
    assert dirsize.total_size == expected_size
    assert dirsize.dir_sizes[str(test_dir)] == expected_size
    assert dirsize.num_files[str(test_dir)] == 4
    top_level_children = dirsize.dir_children[str(test_dir)]
    assert len(top_level_children) == 2

    # Check subdir 2
    dir2 = str(test_dir / "test_dir2")
    assert dir2 in top_level_children
    assert dirsize.dir_sizes[dir2] == 200
    assert dirsize.num_files[dir2] == 1

    # Check subdir 3
    dir3 = str(test_dir / "test_dir3")
    dir3b = str(Path(dir3) / "b")
    dir3c = str(Path(dir3) / "b" / "c")
    assert dir3 in top_level_children
    assert dirsize.dir_sizes[dir3] == 500
    assert dirsize.num_files[dir3] == 1
    assert dirsize.dir_children[dir3] == set([dir3b])
    # Check subdir 3/b
    assert dirsize.dir_sizes[dir3b] == 500
    assert dirsize.num_files[dir3b] == 1
    assert dirsize.dir_children[dir3b] == set([dir3c])
    # Check subdir 3/b/c
    assert dirsize.dir_sizes[dir3c] == 500
    assert dirsize.num_files[dir3c] == 1
    assert dir3c not in dirsize.dir_children


def test_top_level_dir(tmp_path: Path):
    """
    A basic test of the database picks the correct top level directory

    We create the files deep in a directory structure and scan the whole
    structure, but the top level dir (which is the one that it makes
    sense to show as the first one to the user) should be deeper into
    the hierarchy (where there are actually files)
    """
    test_dir0 = tmp_path / "test_dir"
    test_dir = test_dir0 / "deep" / "hierarchy"
    make_test_dir(test_dir)
    test_dir0 = test_dir0.resolve(strict=True)
    test_dir = test_dir.resolve(strict=True)

    # Create database (scan + write to disk) containing is the whole
    # hierarchy (test_dir/), not only the part that is buried inside
    # where the files actually are located (test_dir/deep/hierarchy)
    db_dir = tmp_path / "mudus_db"
    db = MudusDatabase(db_dir)
    db.directories_to_scan = [str(test_dir0)]
    db.run_file_system_scan()

    # Check that the top_level_dir is test_dir/deep/hierarchy
    assert len(db.cumulative_results) == 1
    dirsize, error = db.lookup_directory_sizes(uid=os.getuid(), gid="all")
    assert error == ""
    assert dirsize.top_level_dir == str(test_dir)





def make_test_dir(root_dir: Path):
    """
    Create a directory hierarchy for testing
    the mudus scanner and database:

        --------------------------    ------------
        File name                        File size
        --------------------------    ------------
        🗀 root_dir                            dir
        │
        ├── file1.txt                    100 bytes
        ├── file2.txt                   1000 bytes
        │
        ├── 🗀 test_dir2                       dir
        │   │
        │   └── file3.txt                200 bytes
        │
        └── 🗀 test_dir3                       dir
            │
            └── 🗀 b                           dir
                │
                └── 🗀 c                       dir
                    │
                    └── file4.txt        500 bytes
        --------------------------    ------------

    """
    root_dir.mkdir(parents=True, exist_ok=True)

    # There are 1100 bytes of files directly in the test dir
    (root_dir / "file1.txt").write_text("X" * 100)
    (root_dir / "file2.txt").write_text("Y" * 1000)

    # There are 200 bytes of data in test_dir2
    test_dir2 = root_dir / "test_dir2"
    test_dir2.mkdir()
    (test_dir2 / "file3.txt").write_text("Z" * 200)

    # There are 500 bytes of data in test_dir3/b/b
    test_dir3 = root_dir / "test_dir3/b/c"
    test_dir3.mkdir(parents=True)
    (test_dir3 / "file4.txt").write_text("W" * 500)

    # Create the mudus database
    db_dir = Path(root_dir) / "mudus_db"
    db_dir.mkdir()
