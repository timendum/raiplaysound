from os import makedirs, path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from raiplaysound.single import RaiParser

GENERI_URL = "https://www.raiplaysound.it/generi"
SITEMAP_ENTRYPOINT = "https://www.raiplaysound.it/sitemap.archivio.indice.xml"
PROGRAMMI_URL = "https://www.raiplaysound.it/programmi/"
AUDIOLIBRI_URL = "https://www.raiplaysound.it/audiolibri/"
PLAYLIST_URL = "https://www.raiplaysound.it/playlist/"

REQ_TIMEOUT = 3


class RaiPlaySound:
    def __init__(self):
        self._urls = set()
        self._base_path = path.join(".", "out")
        makedirs(self._base_path, exist_ok=True)

    def _get_locs_from_sitemap_url(self, sitemap_url: str) -> set[str]:
        """Downloads sitemap from url and returns all urls contained in the <loc> tag."""

        urls = set()
        _r = requests.get(sitemap_url, timeout=REQ_TIMEOUT)
        _r.raise_for_status()
        _xml = BeautifulSoup(_r.text, "xml")
        _sitemaps = _xml.find_all("sitemap")
        for item in _sitemaps:
            loc = item.find_next("loc")
            if loc:
                urls.add(loc.text)
        return urls

    def _get_url_from_sitemap(self, sitemap_url: str, url_base: str):
        """Generate the url of a program given a sitemap and a base_url."""

        locs = self._get_locs_from_sitemap_url(sitemap_url)
        for loc in locs:
            podcast_name = loc.split(".")[-2]
            url = urljoin(url_base, podcast_name)
            self._urls.add(url)

    def parse_genere(self, url: str):
        """Parses the a genere page."""

        result = requests.get(url, timeout=REQ_TIMEOUT)
        result.raise_for_status()
        soup = BeautifulSoup(result.content, "html.parser")
        elements = soup.find_all("article")
        for element in elements:
            url = urljoin(url, element.find("a")["href"])
            self._urls.add(url)

    def parse_index(self):
        """Parses main sitemap descending into sitemaps."""

        sitemaps_url = self._get_locs_from_sitemap_url(SITEMAP_ENTRYPOINT)

        for url in sitemaps_url:
            if "programmi" in url:
                self._get_url_from_sitemap(url, PROGRAMMI_URL)
            elif "audiolibri" in url:
                self._get_url_from_sitemap(url, AUDIOLIBRI_URL)
            elif "playlist" in url:
                self._get_url_from_sitemap(url, PLAYLIST_URL)
            elif "generi" in url:
                self.parse_genere(url)
            else:
                print(f"Unsupported sitemap: {url}")

    def create_feeds(self, skip_programmi: bool, skip_film: bool):
        for url in self._urls:
            rai_parser = RaiParser(url, self._base_path, skip_programmi, skip_film)
            try:
                rai_parser.process()
            except Exception as e:
                print(f"Error with {url}: {e}")
