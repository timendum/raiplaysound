from collections import namedtuple
from datetime import date
from html import escape
from os import path
from pathlib import Path
from unicodedata import normalize

from feedendum import from_rss_file

GENERI_URL = "https://www.raiplaysound.it/generi"

Entry = namedtuple("Entry", ["title", "sort", "text", "file", "categories"])


def sort_title(title: str) -> str:
    return normalize("NFD", title.lstrip("#'\"« ")).lower()


class Indexer:
    def __init__(self):
        self.entries = []
        self._seen_url = set()
        self._base_path = Path(path.join(".", "out"))

    def generate(self) -> None:
        xfiles = self._base_path.glob("*.xml")
        for xfile in xfiles:
            filename = xfile.name
            feed = from_rss_file(xfile)
            try:
                e = Entry(
                    feed.title,
                    sort_title(feed.title),
                    feed.description,
                    filename,
                    [
                        c["@text"]
                        for c in feed._data.get(
                            "{http://www.itunes.com/dtds/podcast-1.0.dtd}category", []
                        )
                    ],
                )
            except TypeError:
                # Podcast with ony one category
                e = Entry(
                    feed.title,
                    sort_title(feed.title),
                    feed.description,
                    filename,
                    [feed._data["{http://www.itunes.com/dtds/podcast-1.0.dtd}category"]["@text"]],
                )
            self.entries.append(e)
        with open(path.join(path.dirname(path.abspath(__file__)), "index.template")) as t:
            output = t.read()
        output = output.replace("%%lastupdate%%", date.today().isoformat())
        output = output.replace("%%list%%", self.generate_list())
        output = output.replace("%%tag%%", self.generate_tag())
        with open(path.join(self._base_path, "index.html"), "w", encoding="utf8") as text_file:
            text_file.write(output)

    def generate_list(self):
        index = {}
        for entry in self.entries:
            letter = entry.sort[0]
            if letter not in index:
                index[letter] = []
            index[letter].append(entry)
        # Sort entries
        for letter in index:
            index[letter] = sorted(index[letter], key=lambda entry: entry.sort)
        text = "<p>Salta a: "
        for k in sorted(index.keys()):
            text += f"<a href='#list-{k.upper()}'>{k.upper()}</a> "
        text += "</p>\n"
        for k in sorted(index.keys()):
            text += f"<h4 id='list-{k.upper()}'>{k.upper()}</h4>\n"
            for v in index[k]:
                text += (
                    '<p x-show="show_feed($el)">'
                    + f'<a href="{v.file}">{escape(v.title)}</a> - {escape(v.text)}</p>\n'
                )
        return text

    def generate_tag(self):
        tags = {}
        for entry in self.entries:
            for tag in entry.categories:
                if tag not in tags:
                    tags[tag] = []
                tags[tag].append(entry)
        # Remove duplicates
        keys = list(tags.keys())
        duplicates = []
        for key in keys:
            skey = key.translate(str.maketrans("à", "a", " '/"))
            if skey == key:
                continue
            if skey in keys:
                duplicates.append(skey)
        for dup in duplicates:
            del tags[dup]
        # Sort entries
        for tag in tags:
            tags[tag] = sorted(tags[tag], key=lambda entry: entry.title.lower())
        text = "<p>Salta a: "
        for tag in sorted(tags.keys()):
            text += f"<a x-show='show_item($el)' href='#tag-{tag}'>{tag}</a> "
        text += "</p>\n"
        for tag in sorted(tags.keys()):
            text += f"<div x-show='show_header($el)'>\n<h4 id='tag-{tag}'>{tag}</h4>\n"
            for v in tags[tag]:
                text += f'<p><a href="{v.file}">{escape(v.title)}</a> - {escape(v.text)}</p>\n'
            text += "</div>\n"
        return text
