from textual.app import App
from textual.screen import Screen
from textual.widgets import Header, Footer

from mudus import version
from mudus.database import MudusDatabase
from .mudus_scan_status import MudusScanStatus


class MudusScanScreen(Screen):
    BINDINGS = [
        ("q", "dismiss", "Close MUDUS"),
    ]

    def __init__(self, mudus_db: MudusDatabase):
        self.mudus_db: MudusDatabase = mudus_db
        return super().__init__()

    def compose(self):
        self.title = f"MUDUS Scan v.{version}"
        self.sub_title = "Multi-User system Disk USage"
        yield Header(icon="M")
        yield MudusScanStatus(mudus_db=self.mudus_db)
        yield Footer()

    def key_q(self):
        self.dismiss()


class MudusScanApp(App):
    def __init__(self, mudus_db: MudusDatabase):
        self.mudus_db: MudusDatabase = mudus_db
        return super().__init__()

    def on_mount(self):
        self.scan_screen = MudusScanScreen(mudus_db=self.mudus_db)
        self.push_screen(self.scan_screen, callback=self.quit)

    def quit(self, result=None):
        # Cancel the scan if it is running
        self.scan_screen.query_one(MudusScanStatus).cancel_scan()
        # Exit the app
        self.exit(result)
