from rich.table import Table

PRIMARY_GREEN = "#03e903"
SECONDARY_GREEN = "#089E08"

def make_pipboy_table(title: str, width: int = 60) -> Table:
    """
    Creates table styled like a Fallout Pip-Boy.
    Keeps consistent headers, colors, and spacing across commands.
    """
    return Table(
        title=f"[{PRIMARY_GREEN}]{title}[/{PRIMARY_GREEN}]",
        expand=False,
        width=width,
        show_lines=True,
        padding=(0, 1),
        header_style=f"bold {PRIMARY_GREEN}",
        border_style=PRIMARY_GREEN,
        row_styles=[PRIMARY_GREEN, SECONDARY_GREEN] # alternating row background
    )
