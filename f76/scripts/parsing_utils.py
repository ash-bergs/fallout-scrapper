import re
from bs4 import Tag, NavigableString

QTY_AFTER_LINK = re.compile(r"\b(?:x|×)\s*(\d+)\b", re.I)
FOOTNOTE_RE = re.compile(r"\[\d+\]")

def clean_text(s: str) -> str:
    s = FOOTNOTE_RE.sub("", s or "")
    return " ".join(s.replace("\xa0", " ").split())

# Class name on the Junk Items table - also belongs to several other tables
TARGET = {"va-table", "va-table-center", "va-table-full"}


# Tag - bs4 type - has things like tag.name, tag.attrs, etc 
def has_all_classes(tag: Tag) -> bool:
    return (
        tag.name == "table"
        # issubset - return `True` if all elements of TARGET are present in passed set
        # set - converts the list into Python `set` - no duplicate values
        # tag.get(attr_name, default) - return the attr value if exists - otherwise default 
        and TARGET.issubset(set(tag.get("class", [])))
    )


def parse_components_cell(cell: Tag):
    """
    Parse a components <td> that looks like:
    <a>Steel</a><br><a>Lead</a>
    or:
    <a>Steel</a> x2<br><a>Lead</a> x3
    Returns: list[(qty:int, name:str)]
    """
    groups, current = [], []
    for child in cell.children:
        if getattr(child, "name", None) == "br":
            if current:
                groups.append(current); current = []
            continue
        current.append(child)
    if current: # last group
        groups.append(current)

    results = []
    for nodes in groups:
        # Find the component link
        link = next((n for n in nodes if isinstance(n, Tag) and n.name == "a"), None)
        if not link:
            # fallback to plain text
            text = " ".join(str(n).strip() for n in nodes if isinstance(n, (NavigableString,)))
            text = re.sub(r"\s+", " ", text).strip(" .;")
            if text:
                # try "Name x2" pattern
                m = QTY_AFTER_LINK.search(text)
                qty = int(m.group(1)) if m else 1
                name = QTY_AFTER_LINK.sub("", text).strip()
                if name:
                    results.append((qty, name))
            continue
        
        name = link.get_text(strip=True)
        # Look for qty in the text immediately after the link (e.g., " x2")
        qty = 1
        sib = link.next_sibling
        if isinstance(sib, NavigableString):
            m = QTY_AFTER_LINK.search(str(sib))
            if m:
                qty = int(m.group(1))

        if name:
            results.append((qty, name))
    return results
