"""Small HTML structure parser for evidence-based listings and program pages."""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    children: list = field(default_factory=list)
    text_offset: int = 0

    def text(self):
        parts = [child.text() if isinstance(child, Element) else child for child in self.children]
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def find(self, tags):
        for child in self.children:
            if isinstance(child, Element):
                if child.tag in tags:
                    yield child
                yield from child.find(tags)


class ProgramDocument(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {})
        self.stack = [self.root]
        self.hidden = 0
        self.tokens = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "noscript"):
            self.hidden += 1
        if self.hidden:
            return
        node = Element(tag, dict(attrs), text_offset=len(self.tokens))
        self.stack[-1].children.append(node)
        if tag not in (
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "source",
            "wbr",
        ):
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "noscript") and self.hidden:
            self.hidden -= 1
            return
        if self.hidden:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, value):
        if not self.hidden:
            self.tokens.append(value)
            self.stack[-1].children.append(value)

    def find(self, *tags):
        return list(self.root.find(set(tags)))

    def links(self, base_url):
        for node in self.find("a"):
            href = node.attrs.get("href", "")
            if href and not href.startswith(("#", "mailto:", "javascript:")):
                yield urljoin(base_url, href).split("#", 1)[0], node.text()

    def labeled_values(self):
        for row in self.find("tr"):
            cells = list(row.find({"th", "td"}))
            if len(cells) >= 2:
                yield cells[0].text().rstrip(":"), " ".join(c.text() for c in cells[1:]), row.text()
        for node in self.find("dl"):
            label = None
            for child in node.children:
                if isinstance(child, Element):
                    if child.tag == "dt":
                        label = child.text()
                    elif child.tag == "dd" and label:
                        yield label, child.text(), label + " " + child.text()

    def sections(self):
        # Keep content scope: a new heading terminates the previous section.
        heading = None
        pieces = []
        main = self.find("main")
        root = main[0] if main else self.root
        for node in root.find({"h1", "h2", "h3", "h4", "p", "li"}):
            if node.tag.startswith("h"):
                if heading and pieces:
                    yield heading, " ".join(pieces)
                heading, pieces = node.text(), []
            elif heading:
                text = node.text()
                if text and (not pieces or text not in pieces[-1]):
                    pieces.append(text)
        if heading and pieces:
            yield heading, " ".join(pieces)

    def source_sections(self):
        """Contiguous visible source spans, retaining nested headings and table context."""
        full = re.sub(r"\s+", " ", " ".join(self.tokens)).strip()
        headings = self.find("h1", "h2", "h3", "h4", "h5", "h6")
        locations = []
        for heading in headings:
            prefix = re.sub(r"\s+", " ", " ".join(self.tokens[: heading.text_offset])).strip()
            start = full.find(heading.text(), len(prefix))
            locations.append(start)
        for i, heading in enumerate(headings):
            start = locations[i]
            if start < 0:
                continue
            end = len(full)
            for j in range(i + 1, len(headings)):
                if headings[j].tag <= heading.tag and locations[j] >= 0:
                    end = locations[j]
                    break
            yield heading.text(), full[start + len(heading.text()) : end].strip()
