from textual.app import App
from textual.screen import Screen
from textual.widgets import Header, Footer

from mudus import version
from mudus.database import MudusDatabase
from .mudus_view_table import MudusTable


class MudusViewScreen(Screen):
    BINDINGS = [
        ("q", "dismiss", "Close MUDUS"),
    ]

    def __init__(self, mudus_db: MudusDatabase, user_id: int):
        self.mudus_db: MudusDatabase = mudus_db
        self.user_id: int = user_id
        return super().__init__()

    def compose(self):
        self.title = f"MUDUS v.{version}"
        self.sub_title = "Multi-User system Disk USage"

        yield Header(icon="M")
        yield MudusTable(mudus_db=self.mudus_db, user_id=self.user_id)
        yield Footer()

    def key_q(self):
        self.dismiss()


class MudusViewApp(App):
    def __init__(self, mudus_db: MudusDatabase, user_id: int):
        self.mudus_db: MudusDatabase = mudus_db
        self.user_id: int = user_id
        return super().__init__()

    def on_mount(self):
        screen = MudusViewScreen(mudus_db=self.mudus_db, user_id=self.user_id)
        self.push_screen(screen, callback=self.quit)

    def quit(self, result=None):
        self.exit(result)
