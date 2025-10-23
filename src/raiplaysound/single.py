import os
import tempfile
from datetime import datetime as dt
from datetime import timedelta
from itertools import chain
from os.path import join as pathjoin
from urllib.parse import urljoin

import requests
from feedendum import Feed, FeedItem, from_rss_file, to_rss_string
from feedendum.exceptions import FeedXMLError

NSITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def url_to_filename(url: str) -> str:
    return url.split("/")[-1] + ".xml"


def _datetime_parser(s: str) -> dt | None:
    if not s:
        return None
    formats = ["%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return dt.strptime(s, fmt)
        except ValueError:
            pass
    print("Unparsed ", s)
    return None


class RaiParser:
    session = requests.Session()

    def __init__(
        self,
        url: str,
        folder_path: str,
    ) -> None:
        self.url = url
        self.folderPath = folder_path
        self.inner: list[Feed] = []
        self.skip_programmi = True
        self.skip_film = True
        self.date_ok = False
        self.reverse = False
        self.verbose = True

    def log(self, msg: str, level = 20) -> None:
        if self.verbose:
            print(msg)

    def extend(self, url: str) -> None:
        url = urljoin(self.url, url)
        if url == self.url:
            return
        if url in (f.url for f in self.inner):
            return
        parser = RaiParser(url, self.folderPath)
        self.inner.extend(parser.process())

    def _json_to_feed(self, feed: Feed, rdata) -> None:
        feed.title = rdata["title"]
        feed.description = rdata["podcast_info"].get("description", "")
        feed.description = (feed.description or rdata["title"]).strip()
        feed.url = self.url
        feed._data["image"] = {"url": urljoin(self.url, rdata["podcast_info"]["image"])}
        feed._data[f"{NSITUNES}author"] = "RaiPlaySound"
        feed._data["language"] = "it-it"
        feed._data[f"{NSITUNES}owner"] = {f"{NSITUNES}email": "timedum@gmail.com"}
        # Categories
        categories = set()  # to prevent duplicates
        for c in chain(
            rdata["podcast_info"]["genres"],
            rdata["podcast_info"]["subgenres"],
            rdata["podcast_info"]["dfp"].get("escaped_genres", []),
            rdata["podcast_info"]["dfp"].get("escaped_typology", []),
        ):
            categories.add(c["name"])
        try:
            for c in rdata["podcast_info"]["metadata"]["product_sources"]:
                categories.add(c["name"])
        except KeyError:
            pass
        feed._data[f"{NSITUNES}category"] = [{"@text": c} for c in categories]
        cards = []
        try:
            feed.update = _datetime_parser(rdata["block"]["update_date"])
            cards = rdata["block"]["cards"]
        except KeyError:
            pass
        if not feed.update:
            feed.update = _datetime_parser(rdata["track_info"]["date"])
        for item in cards:
            if "/playlist/" in item.get("weblink", ""):
                self.extend(item["weblink"])
            if not item.get("audio", None):
                continue
            fitem = FeedItem()
            fitem.title = item["toptitle"]
            fitem.id = "timendum-raiplaysound-" + item["uniquename"]
            # Keep original ordering by tweaking update seconds
            # Fix time in case of bad ordering
            dupdate = _datetime_parser(item["create_date"] + " " + item["create_time"])
            fitem.update = dupdate
            fitem.url = urljoin(self.url, item["track_info"]["page_url"])
            fitem.content = item.get("description", item["title"]).strip()
            fitem._data = {
                "enclosure": {
                    "@type": "audio/mpeg",
                    "@url": urljoin(self.url, item["audio"]["url"]),
                },
                f"{NSITUNES}title": fitem.title,
                f"{NSITUNES}summary": fitem.content,
                f"{NSITUNES}duration": item["audio"]["duration"],
                "image": {"url": urljoin(self.url, item["image"])},
            }
            if item.get("downloadable_audio", None) and item["downloadable_audio"].get("url", None):
                fitem._data["enclosure"]["@url"] = urljoin(
                    self.url, item["downloadable_audio"]["url"]
                ).replace("http:", "https:")
            if item.get("season", None) and item.get("episode", None):
                fitem._data[f"{NSITUNES}season"] = item["season"]
                fitem._data[f"{NSITUNES}episode"] = item["episode"]
            feed.items.append(fitem)

    def _fix_dates(self, feed: Feed) -> None:
        if not self.date_ok and all([item.update for item in feed.items]):
            # Try to fix the update timestamp
            dates = [i.update.date() for i in feed.items]
            increasing = all(map(lambda a, b: b >= a, dates[0:-1], dates[1:]))
            decreasing = all(map(lambda a, b: b <= a, dates[0:-1], dates[1:]))
            if increasing and not decreasing:
                # Dates never decrease
                last_update = dt.fromtimestamp(0)
                for item in feed.items:
                    if item.update <= last_update:
                        item.update = last_update + timedelta(seconds=1)
                    last_update = item.update
            elif decreasing and not increasing:
                # Dates never decrease
                last_update = feed.items[0].update + timedelta(seconds=1)
                for item in feed.items:
                    if item.update >= last_update:
                        item.update = last_update - timedelta(seconds=1)
                    last_update = item.update
        if all([i._data.get(f"{NSITUNES}episode") for i in feed.items]) and all(
            [i._data.get(f"{NSITUNES}season") for i in feed.items]
        ):
            try:
                feed.items = sorted(
                    feed.items,
                    key=lambda e: int(e._data[f"{NSITUNES}episode"])
                    + int(e._data[f"{NSITUNES}season"]) * 10000,
                    reverse=self.reverse,
                )
            except ValueError:
                # season or episode not an int
                feed.items = sorted(
                    feed.items,
                    key=lambda e: str(e._data[f"{NSITUNES}season"]).zfill(5)
                    + str(e._data[f"{NSITUNES}episode"]).zfill(5),
                    reverse=self.reverse,
                )
        else:
            feed.sort_items()

    def process(self) -> list[Feed]:
        result = self.session.get(self.url + ".json")
        try:
            result.raise_for_status()
        except requests.HTTPError as e:
            self.log(f"Error with {self.url}: {e}")
            return self.inner
        rdata = result.json()
        typology = rdata["podcast_info"].get("typology", "").lower()
        if self.skip_programmi and (typology in ("programmi radio", "informazione notiziari")):
            self.log(f"Skipped programmi: {self.url} ({typology})")
            return []
        if self.skip_film and (typology in ("film", "fiction")):
            self.log(f"Skipped film: {self.url} ({typology})")
            return []
        for tab in rdata["tab_menu"]:
            if tab["content_type"] == "playlist":
                self.extend(tab["weblink"])
        feed = Feed()
        self._json_to_feed(feed, rdata)
        if not feed.items and not self.inner:
            self.log(f"Empty: {self.url}")
        if feed.items:
            self._fix_dates(feed)
            filename = pathjoin(self.folderPath, url_to_filename(self.url))
            if atomic_write(filename, feed):
                self.log(f"Written {filename}")
            else:
                self.log(f"No changes for {filename}")
        return [feed] + self.inner


def atomic_write(filename: str, content: Feed, always=True) -> bool:
    if not always:
        try:
            with open(filename, encoding="utf8") as f:
                old_feed = from_rss_file(f)
                if compare_feed(old_feed, content):
                    return False
        except (OSError, FeedXMLError):
            pass
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf8",
        delete=False,
        dir=os.path.dirname(filename),
        prefix=".tmp-single-",
        suffix=".xml",
    )
    tmp.write(to_rss_string(content))
    tmp.close()
    os.replace(tmp.name, filename)
    return True


def compare_feed(a: Feed, b: Feed) -> bool:
    if a.title != b.title:
        return False
    if a.description != b.description:
        return False
    if a.url != b.url:
        return False
    if a._data.get("image", {}).get("url", None) != b._data.get("image", {}).get("url", None):
        return False
    # TODO? feed._data[f"{NSITUNES}category"]
    # not update
    if len(a.items) != len(b.items):
        return False
    for ia, ib in zip(a.items, b.items, strict=True):
        if ia.title != ib.title:
            return False
        if ia.id != ib.id:
            return False
        # not update
        if ia.url != ib.url:
            return False
        if ia.content != ib.content:
            return False
        if ia._data.get("enclosure", {}).get("@url", None) != ib._data.get("enclosure", {}).get(
            "@url", None
        ):
            return False
        if ia._data.get(f"{NSITUNES}duration", None) != ib._data.get(f"{NSITUNES}duration", None):
            return False
        if ia._data.get(f"{NSITUNES}episode", None) != ib._data.get(f"{NSITUNES}episode", None):
            return False
        if ia._data.get(f"{NSITUNES}season", None) != ib._data.get(f"{NSITUNES}season", None):
            return False
    return True
