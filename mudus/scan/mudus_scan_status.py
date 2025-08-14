from rich.text import Text
from textual import on, work
from textual.widget import Widget
from textual.widgets import Label, Button, Static, LoadingIndicator
from textual.containers import Horizontal, Vertical
from textual.events import Timer

from mudus.database import MudusDatabase


class MudusScanStatus(Widget):
    """
    A class to represent the status of a MUDUS scan.
    It inherits from Grid to allow for flexible layout management.
    """

    DEFAULT_CSS = """
    MudusScanStatus {
        layout: vertical;
        padding: 2 8;
    }
    Label {
        margin: 1 0;
    }
    #scan_status_info {
        height: 6;
    }
    Button {
        margin: 1 5;
    }
    #scan_status_title {
        width: 80%;
        text-align: center;
        padding: 1;
        background: $panel;
        color: $primary;
        text-style: bold;
    }
    #scan_status_loading {
        align: left middle;
        width: 40;
        height: 5;
    }
    #buttons {
        height: 5;
    }
    .hidden {
        display: none;
    }
    """

    def __init__(self, mudus_db: MudusDatabase):
        super().__init__()
        self.mudus_db: MudusDatabase = mudus_db

    def compose(self):
        yield Vertical(
            Label("MUDUS File System Scanner", id="scan_status_title"),
            Label("Scanner is NOT currently running", id="scan_status_message"),
            Label("", id="scan_status_info"),
            LoadingIndicator(id="scan_status_loading", classes="hidden"),
            Horizontal(
                Button("Scan Now", id="scan_now_button", variant="primary"),
                Button("Cancel", id="cancel_button", variant="warning"),
                id="buttons",
            ),
            Static(
                Text(
                    "Directories to scan:\n  -"
                    + "\n  -".join(str(pth) for pth in self.mudus_db.directories_to_scan)
                ),
                id="scan_directories",
            ),
        )

    @on(Button.Pressed, "#scan_now_button")
    @work(group="scanner", thread=True)
    def start_scan(self):
        self.app.call_from_thread(self.set_timer, 1.0, self.update_status)
        self.mudus_db.run_file_system_scan()

    @on(Button.Pressed, "#cancel_button")
    def cancel_scan(self):
        if not self.mudus_db.is_scanning:
            return
        self.mudus_db.cancel_scan = True

    def update_status(self, event: Timer | None = None):
        db = self.mudus_db

        # Information about errors encountered during the scan
        error_message = f"Number of errors: {len(db.errors)}"
        if db.errors:
            last_error = db.errors[-1]
            error_message += f"\n  Last error: {last_error[1]}\n  Error path: {last_error[0]}"

        # Check if scan has finished or been cancelled
        if not self.mudus_db.is_scanning:
            if db.cancel_scan:
                # Scan has been stopped after cancelling
                self.query_one("#scan_status_message").update(
                    Text.from_markup("[bold red]Scanner has been cancelled[/bold red]")
                )
            else:
                # Scan has finished
                self.query_one("#scan_status_message").update(
                    Text.from_markup(
                        "[green][bold]File system scan is done![/bold]"
                        f" Completed in {db.scanning_duration:.2f} seconds.[/green]"
                    )
                )
            self.query_one("#scan_status_info").update(
                Text.from_markup(
                    f"[dim]Scanned {db.num_scanned_files:,d} files"
                    f" and {db.num_scanned_directories:,d} directories[/]"
                    f"\n{error_message if db.errors else ''}"
                )
            )
            self.query_one("#scan_status_loading").styles.display = "none"
            self.query_one("#scan_now_button").disabled = False
            return

        # The scanner is still running
        self.query_one("#scan_status_message").update(
            Text.from_markup("[bold]Running file system scan ... please wait ...[/bold]")
        )
        current_scan_item = db.current_scan_item or "unknown"
        if len(current_scan_item) > 100:
            current_scan_item = current_scan_item[:100] + "..."
        self.query_one("#scan_status_info").update(
            Text.from_markup(
                f"[{self.app.current_theme.accent}]Scanned {db.num_scanned_files:,d} files"
                f" and {db.num_scanned_directories:,d} directories so far[/]"
                f"\nNow scanning:\n  {current_scan_item}"
                f"\n{error_message}"
            )
        )
        self.query_one("#scan_status_loading").styles.display = "block"
        self.query_one("#scan_now_button").disabled = True

        # Re-update the scanning status in a while
        self.set_timer(1.0, self.update_status)
