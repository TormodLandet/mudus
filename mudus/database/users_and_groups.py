import pwd
import grp

# Cache for group and user names
# You currently cannot (easily) clear these caches, they should not change
# during the running of mudus (who even changes user or group names??)
# Reopening the program will (of course) reset these caches
_GROUP_NAMES_CACHE: dict[int, str] = {}
_USER_NAMES_CACHE: dict[int, str] = {}


def get_group_name(gid: int) -> str:
    """
    Ask the system for the name of the group with the given Group ID.
    """
    if gid not in _GROUP_NAMES_CACHE:
        try:
            group_name = grp.getgrgid(gid).gr_name
        except KeyError:
            group_name = "**UNKNOWN GROUP**"
        _GROUP_NAMES_CACHE[gid] = group_name
    return _GROUP_NAMES_CACHE[gid]


def get_user_name(uid: int) -> str:
    """
    Ask the system for the name of the user with the given User ID.
    """
    if uid not in _USER_NAMES_CACHE:
        try:
            user_name = pwd.getpwuid(uid).pw_name
        except KeyError:
            user_name = "**UNKNOWN USER**"
        _USER_NAMES_CACHE[uid] = user_name
    return _USER_NAMES_CACHE[uid]
