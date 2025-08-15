# mudus

*Multi-User Disk USage scanner and reporter.*

Quickly figure out where a specific user has left files on a shared disk by showing cumulative (recursive) directory sizes and letting the user drill down in a file-explorer like Textual TUI showing only their files.

On a large HPC system with many shared project folders it can be easy to forget terabytes of result files deep in some directory hierarchy. A year later, when the system administrator complains that disk quotas are nearing 100% full, you have no idea where to start cleaning up old analysis results. Normal disk usage tools show directory sizes for all files, but you can only clean up your own messes, so you need a more specialized tool. Also, if every user has to perform a recursive file-system scan to figure out where they left files then the shared storage server, which was already struggling due to a nearly full disk, will slow down even more when it gets hammered by metadata requests ...

Periodically running `mudus scan` lets the system administrator keep a (relatively) up to date database of who has files where. Every user can run `mudus` to instantly see their own disk usage without running a full file-system scan themselves. The downside is that the effect of cleaning up is not reflected in the database until the next scan is performed.


## Using mudus

You must first run `mudus scan` to build a database of cumulative/recursive directory contents. The database is stored in separate files for each user (file owner) and group in the mudus database directory. After scanning, you (or any other user with read access to the database) can use the `mudus view` command to figure out where on the large shared file system you have forgotten a bunch of data. Using mudus is probably overkill for single-user systems; see some alternatives listed below instead.


### Scanning

You can launch a visual scanner using `mudus scan` or run in non-interactive mode by adding the `--non-interactive` flag. Run with the `--help` flag to see all options.

If you are sharing the disk usage database with others, you probably want to set the `MUDUS_DB_DIR` environment variable to point to a shared directory where the disk usage database is stored.

Non-interactive example:

```bash
export MUDUS_DB_DIR="/shared/.cache/mudus"
mudus scan --scan-dir /shared/dir_a --scan-dir /shared/dir_b --non-interactive
```

Interactive example:

<img src="https://raw.githubusercontent.com/TormodLandet/mudus/main/docs/figures/MudusScanApp.svg" alt="Screenshot of mudus scan" width="50%" />


### Viewing the disk-usage database

Use the `mudus` command (short for `mudus view`) to show your disk usage and drill down into subdirectories to figure out where you have forgotten to clean out a closed project on a shared drive, or something similar. You can navigate with the arrow keys (`right` to enter a directory, `left` to leave, `up` and `down` to select directories) or go into the selected directory by pressing `Enter` (or click with the mouse). The `q` key will quit the program.

Example of the Textual-based TUI:

<img src="https://raw.githubusercontent.com/TormodLandet/mudus/main/docs/figures/MudusViewApp.svg" alt="Screenshot of mudus view" width="90%" />


## Installation

You can install and run mudus directly with `pipx run mudus` or `uvx mudus` if you have [pipx](https://pipx.pypa.io/) or [uv](https://docs.astral.sh/uv/) installed.
Running `pipx install mudus` should make it available as `mudus` on the command line, or you can use `uv tool install mudus` if you would rather use `uv`.

You can also use `pip install mudus` and launch it as `python -m mudus`. By creating a Python virtual environment for mudus you can make it available to all users on a system, maybe with an executable `/usr/bin/mudus` script like this:

```bash
#!/bin/bash

source /path/to/virtual-environment/activate-script
export MUDUS_DB_DIR="/something/shared/mudus-db-dir"
python -m mudus "$@"
```

## Alternatives

There are many great alternatives to `mudus` if you are on a single-user system, or you do not care about who owns the files, just the overall disk usage. One fast and easy tool is [dua (Disk Usage Analyzer)](https://github.com/Byron/dua-cli), which integrates the `scan` and `view` commands into one. When you start `dua interactive`, it spins up a bunch of threads to quickly walk the file system. This is relatively fast, but it can be unpopular on shared HPC systems where hammering the shared storage servers whenever you feel like it may not be the best idea.


## Roadmap

The following items are on the `mudus` development roadmap:

* **Show group instead of user**: You may want to see the disk usage for a given group instead of a given user. This should be a relatively small addition.

* **Deeper file-system integration**: `mudus` has support for pluggable disk scanners. Currently, the Python `scandir` method is the only implementation, but deeper integration into relevant file systems (BeeGFS Hive?) may speed up the file-system scan and reduce the load on metadata servers, etc.


## License, Copyright, and Contributing

The `mudus` software is (c) Tormod Landet, [DNV](https://www.dnv.com/maritime/advisory/), and released under an Apache 2.0 license. It was developed to help manage our internal HPC resources at DNV and is not an official DNV tool and comes with absolutely no warranty, support, or guarantees of any kind. Use at your own risk.

Issues and pull requests are welcome, but please note that replies will come when I have time at work, which may be next week or next year depending on how busy it is and how far down on the list of priorities such a relatively niche tool is at the moment (probably quite far down...). I write this not to discourage contributions or bug reports, but please do not be disappointed if I take a while to reply!
