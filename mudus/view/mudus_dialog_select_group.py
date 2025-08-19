from typing import Literal, TypeAlias
import grp
import pwd

from rich.text import Text
from rich.panel import Panel
from textual import on
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Header, OptionList, Label
from textual.widgets.option_list import Option
from textual.message import Message

from mudus.database import MudusDatabase, get_user_name, get_group_name


IdOrAll: TypeAlias = int | Literal["all"]


class MudusSelectGroupWidget(Widget):
    class GroupSelected(Message):
        def __init__(self, user_id: IdOrAll, group_id: IdOrAll) -> None:
            self.user_id: IdOrAll = user_id
            self.group_id: IdOrAll = group_id
            super().__init__()

    def __init__(self, mudus_db: MudusDatabase, user_id: int):
        super().__init__()
        self.mudus_db: MudusDatabase = mudus_db
        self.user_id: int = user_id
        self._group_names: dict[int, str] = {}
        self._user_names: dict[int, str] = {}

        # Figure out which groups we can access
        self.mudus_db.mark_accessible()

        # Names of groups the user owns files in
        self.groups_with_owned_files: set[int] = set()
        for uid, gid in self.mudus_db.cumulative_results:
            if uid == self.user_id:
                self.groups_with_owned_files.add(gid)

        # Collect groups we can inspect
        self.group_ids_and_names: list[tuple[int, str]] = []
        accessible_uids_for_group: dict[int, set[int]] = {}
        inaccessible_uids_for_group: dict[int, set[int]] = {}
        for uid, gid in self.mudus_db.cumulative_results:
            if (uid, gid) in self.mudus_db.accessible_data:
                accessible_uids_for_group.setdefault(gid, set()).add(uid)
            else:
                inaccessible_uids_for_group.setdefault(gid, set()).add(uid)

        # Create a menu of groups the user can choose to see
        group_ids_with_accessible_data = accessible_uids_for_group.keys()
        self.details_for_group: dict[int, str] = {}
        for gid in group_ids_with_accessible_data:
            group_name = get_group_name(gid)
            self.group_ids_and_names.append((gid, group_name))

            # How many users have files in this group and can you see all that info?
            n_accessible = len(accessible_uids_for_group.get(gid, set()))
            n_inaccessible = len(inaccessible_uids_for_group.get(gid, set()))
            self.details_for_group[gid] = f"\n[dim]  Includes data from {n_accessible} users[/]"
            if n_inaccessible:
                # Some users (root??) in this group has directories you cannot see
                users_inaccessible = [
                    get_user_name(uid) for uid in inaccessible_uids_for_group[gid]
                ]
                self.details_for_group[gid] += (
                    f"\n[dim yellow]  WARNING: there are data from {n_inaccessible} users you"
                    f" cannot see: {', '.join(users_inaccessible)}[/]"
                )

    def compose(self):
        group_names_all = sorted([get_group_name(gid) for gid in self.groups_with_owned_files])
        current_user_name = get_user_name(self.user_id)
        options = [
            Option(
                Panel(
                    Text.from_markup(
                        f"[bold blue]ALL GROUPS for {current_user_name}[/]"
                        " [dim italic](this is the default)[/]"
                        f"\n[dim]  Includes data for groups: {', '.join(group_names_all)}[/]"
                    )
                ),
                id="all",
            ),
            *[
                Option(
                    Panel(
                        Text.from_markup(
                            f"GROUP [cyan bold]{name}[/] [dim italic](GID {gid})[/]"
                            f"{self.details_for_group[gid]}"
                        )
                    ),
                    id=str(gid),
                )
                for gid, name in self.group_ids_and_names
            ],
        ]
        self.title = "Select Group"
        self.subtitle = "Show data about a group instead of about a user"
        yield Header(icon="G")
        yield Label("Show data about a group instead of about a user\n")
        yield OptionList(*options)
        yield Footer()

    def on_option_list_option_selected(self, option: OptionList.OptionSelected):
        if option.option_id == "all":
            selected_uid = self.user_id
            selected_gid = "all"
        else:
            selected_uid = "all"
            selected_gid = int(option.option_id)
        self.post_message(self.GroupSelected(selected_uid, selected_gid))


class MudusSelectGroupScreen(ModalScreen):
    CSS = """
    MudusSelectGroupScreen {
        align: center middle;
    }
    MudusSelectGroupWidget {
        margin: 3 10;
    }
    """

    def __init__(self, mudus_db: MudusDatabase, user_id: int):
        """
        Screen with a dialog to change the selected database group.
        """
        super().__init__()
        self.mudus_db: MudusDatabase = mudus_db
        self.user_id: int = user_id

    def compose(self):
        self.title = "Select Group"
        self.sub_title = "Select the group for the disk-usage table"
        yield MudusSelectGroupWidget(self.mudus_db, self.user_id)

    @on(MudusSelectGroupWidget.GroupSelected)
    def group_selected(self, selection: MudusSelectGroupWidget.GroupSelected):
        self.dismiss((selection.user_id, selection.group_id))
