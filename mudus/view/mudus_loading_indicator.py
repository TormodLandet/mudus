from typing import Literal, TypeAlias

from rich.text import Text
from textual.widget import Widget
from textual.containers import Vertical
from textual.widgets import Label, LoadingIndicator


IdOrAll: TypeAlias = int | Literal["all"]


class MudusLoadingIndicator(Widget):
    DEFAULT_CSS = """
    /* #d75faf == hot_pink2, see https://rich.readthedocs.io/en/stable/appendix/colors.html */
    MudusLoadingIndicator {
        height: 5;
        width: 80;
        align: center middle;
        color: #d75faf;
    }
    Label {
        width: 100%;
        height: 1;
        margin: 1 5 1 5;
        color: #d75faf;
    }
    LoadingIndicator {
        width: 40;
        height: 1;
        margin: 0 5 1 5;
        color: #d75faf;
    }
    """

    def __init__(self, message: str = "Loading..."):
        super().__init__()
        self.message: str = message

    def compose(self):
        yield Vertical(
            Label(self.message, id="mudus_loading_label"),
            LoadingIndicator(id="mudus_loading_indicator"),
        )

    def show(self, show: bool = True):
        self.styles.display = "block" if show else "none"
