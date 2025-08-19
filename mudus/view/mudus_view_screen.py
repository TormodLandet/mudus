from typing import Literal, TypeAlias, Callable

from textual.app import App
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.events import Key

from mudus import version
from mudus.database import MudusDatabase
from .mudus_view_table import MudusTable
from .mudus_dialog_select_group import MudusSelectGroupScreen

IdOrAll: TypeAlias = int | Literal["all"]


class MudusViewScreen(Screen):
    BINDINGS = [
        ("q", "dismiss", "Close MUDUS"),
        ("g", "select_group", "Select group"),
    ]

    def __init__(
        self,
        mudus_db: MudusDatabase,
        user_id: IdOrAll,
        group_id: IdOrAll = "all",
        quit_action: Callable | None = None,
    ):
        self.mudus_db: MudusDatabase = mudus_db
        self.user_id: IdOrAll = user_id
        self.group_id: IdOrAll = group_id
        self.quit_action: Callable | None = quit_action
        return super().__init__()

    def compose(self):
        self.title = f"MUDUS v.{version}"
        self.sub_title = "Multi-User system Disk USage"

        yield Header(icon="M")
        yield MudusTable(mudus_db=self.mudus_db, user_id=self.user_id, group_id=self.group_id)
        yield Footer()

    def key_q(self):
        self.dismiss()
        if self.quit_action is not None:
            self.quit_action()

    def key_g(self, event: Key):
        event.stop()
        initial_user_id = self.app.user_id
        self.app.push_screen(
            MudusSelectGroupScreen(self.mudus_db, initial_user_id),
            callback=self.replace_with_new_screen,
        )

    def replace_with_new_screen(self, selected: tuple[IdOrAll, IdOrAll]):
        """
        Replace this Screen with a new one showing a different user/group
        """
        user_id, group_id = selected
        self.app.switch_screen(
            MudusViewScreen(
                mudus_db=self.mudus_db,
                user_id=user_id,
                group_id=group_id,
                quit_action=self.quit_action,
            )
        )


class MudusViewApp(App):
    def __init__(self, mudus_db: MudusDatabase, user_id: int):
        self.mudus_db: MudusDatabase = mudus_db
        self.user_id: int = user_id
        return super().__init__()

    def on_mount(self):
        screen = MudusViewScreen(
            mudus_db=self.mudus_db, user_id=self.user_id, quit_action=self.quit
        )
        self.push_screen(screen, callback=self.quit)

    def quit(self, result=None):
        self.exit(result)
