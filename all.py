from os import makedirs, path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from single import RaiParser

GENERI_URL = "https://www.raiplaysound.it/generi"


class RaiPlaySound:
    def __init__(self):
        self._seen_url = set()
        self._base_path = path.join(path.dirname(path.abspath(__file__)), "dist")
        makedirs(self._base_path, exist_ok=True)

    def parse_genere(self, url):
        result = requests.get(url)
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


def main():
    dumper = RaiPlaySound()
    dumper.parse_generi()


if __name__ == "__main__":
    main()
