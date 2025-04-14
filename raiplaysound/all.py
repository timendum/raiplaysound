import argparse

from os import makedirs, path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .single import RaiParser

GENERI_URL = "https://www.raiplaysound.it/generi"
SITEMAP_ENTRYPOINT = "https://www.raiplaysound.it/sitemap.archivio.indice.xml"

REQ_TIMEOUT=3


class RaiPlaySound:
    def __init__(self):
        self._urls = set()
        self._base_path = path.join(path.dirname(path.abspath(__file__)), "dist")
        makedirs(self._base_path, exist_ok=True)
        self.programmi_url = "https://www.raiplaysound.it/programmi/"
        self.audiolibri_url = "https://www.raiplaysound.it/audiolibri/"
        self.playlist_url = "https://www.raiplaysound.it/playlist/"

    def _get_locs_from_sitemap_url(self, sitemap_url: str) -> set[str]:
        """Downloads sitemap from sitemap_url and returns all the urls contained in the <loc> tag."""

        urls = set()
        _r = requests.get(sitemap_url, timeout=REQ_TIMEOUT)
        _r.raise_for_status()
        _xml = BeautifulSoup(_r.text, "xml")
        _sitemaps = _xml.find_all("sitemap")
        for item in _sitemaps:
            url = item.findNext("loc").text
            urls.add(url)
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
            if 'programmi' in url:
                self._get_url_from_sitemap(url, self.programmi_url)
            elif 'audiolibri' in url:
                self._get_url_from_sitemap(url, self.audiolibri_url)
            elif 'playlist' in url:
                self._get_url_from_sitemap(url, self.playlist_url)
            elif 'generi' in url:
                self.parse_genere(url)
            else:
                print(f"Unsupported sitemap: {url}")

    def create_feeds(self, skip_programmi: bool, skip_film: bool):
        for url in self._urls:
            rai_parser = RaiParser(url, self._base_path)
            try:
                rai_parser.process(skip_programmi, skip_film)
            except Exception as e:
                print(f"Error with {url}: {e}")


def main(skip_programmi: bool, skip_film: bool):
    dumper = RaiPlaySound()
    dumper.parse_index()
    dumper.create_feeds(skip_programmi, skip_film)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera un RSS per ogni programma disponibile su RaiPlaySound.",
        epilog="Info su https://github.com/timendum/raiplaysound/",
    )
    parser.add_argument(
        "--film",
        help="Elabora il podcast anche se sembra un film.",
        action="store_true",
    )
    parser.add_argument(
        "--programma",
        help="Elabora il podcast anche se sembra un programma radio/tv.",
        action="store_true",
    )

    args = parser.parse_args()
    _skip_programmi = not args.programma
    _skip_film = not args.film
    main(_skip_programmi, _skip_film)
