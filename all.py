import argparse

from os import makedirs, path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from single import RaiParser

GENERI_URL = "https://www.raiplaysound.it/generi"

REQ_TIMEOUT=3


class RaiPlaySound:
    def __init__(self):
        self._seen_url = set()
        self._base_path = path.join(path.dirname(path.abspath(__file__)), "dist")
        makedirs(self._base_path, exist_ok=True)

    def parse_genere(self, url):
        result = requests.get(url, timeout=REQ_TIMEOUT)
        result.raise_for_status()
        soup = BeautifulSoup(result.content, "html.parser")
        elements = soup.find_all("article")
        for element in elements:
            url = urljoin(url, element.find("a")["href"])
            if url in self._seen_url:
                continue
            parser = RaiParser(url, self._base_path)
            try:
                parser.process()
                self._seen_url.add(url)
            except Exception as e:
                print(f"Error with {url}: {e}")

    def parse_generi(self) -> None:
        result = requests.get(GENERI_URL)
        result.raise_for_status()
        soup = BeautifulSoup(result.content, "html.parser")
        elements = soup.find_all("a", class_="block")
        generi = []
        for element in elements:
            url = urljoin(result.url, element["href"])
            generi.append(url)
        for genere in generi:
            self.parse_genere(genere)


def main(skip_programmi: bool, skip_film: bool):
    dumper = RaiPlaySound()
    dumper.parse_generi()


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
