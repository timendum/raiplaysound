from os import makedirs, path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

from raiplaysound.single import REQ_TIMEOUT, RaiParser

GENERI_URL = "https://www.raiplaysound.it/generi"
SITEMAP_ENTRYPOINT = "https://www.raiplaysound.it/sitemap.archivio.indice.xml"
PROGRAMMI_URL = "https://www.raiplaysound.it/programmi/"
AUDIOLIBRI_URL = "https://www.raiplaysound.it/audiolibri/"
PLAYLIST_URL = "https://www.raiplaysound.it/playlist/"


class RaiPlaySound:
    session = httpx.Client(timeout=REQ_TIMEOUT)  # To reuse connections in all instances

    def __init__(self) -> None:
        self._urls = set()
        self._base_path = path.join(".", "out")
        self.workers = 0
        makedirs(self._base_path, exist_ok=True)

    def _get_locs_from_sitemap_url(self, sitemap_url: str) -> set[str]:
        """Downloads sitemap from url and returns all urls contained in the <loc> tag."""

        urls = set()
        _r = self.session.get(sitemap_url)
        _r.raise_for_status()
        _xml = BeautifulSoup(_r.text, "xml")
        _sitemaps = _xml.find_all("sitemap")
        for item in _sitemaps:
            loc = item.find_next("loc")
            if loc:
                urls.add(loc.text)
        return urls

    def _get_url_from_sitemap(self, sitemap_url: str, url_base: str) -> None:
        """Generate the url of a program given a sitemap and a base_url."""

        locs = self._get_locs_from_sitemap_url(sitemap_url)
        for loc in locs:
            podcast_name = loc.split(".")[-2]
            url = urljoin(url_base, podcast_name)
            self._urls.add(url)

    def parse_genere(self, url: str) -> None:
        """Parses the a genere page."""

        result = self.session.get(url, timeout=REQ_TIMEOUT)
        result.raise_for_status()
        soup = BeautifulSoup(result.content, "html.parser")
        elements = soup.find_all("article")
        for element in elements:
            a = element.find("a")
            if a and isinstance(a["href"], str):
                url = urljoin(url, a["href"])
                self._urls.add(url)

    def parse_index(self) -> None:
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

    def _create_feeds_simple(self, skip_programmi: bool, skip_film: bool) -> None:
        RaiParser.session = self.session
        for url in tqdm(self._urls, unit="feed"):
            rai_parser = RaiParser(url, self._base_path)
            rai_parser.skip_film = skip_film
            rai_parser.skip_programmi = skip_programmi
            rai_parser.verbose = False
            try:
                rai_parser.process()
            except Exception as e:
                print(f"Error with {url}: {e}")

    def _create_feeds_thread(self, skip_programmi: bool, skip_film: bool) -> None:
        # Use threads to process multiple feeds in parallel
        import signal
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _run(url: str) -> tuple[str, Exception | None]:
            try:
                rai_parser = RaiParser(url, self._base_path)
                rai_parser.skip_film = skip_film
                rai_parser.skip_programmi = skip_programmi
                rai_parser.verbose = False
                rai_parser.process()
                return (url, None)
            except Exception as e:
                return (url, e)

        def handle_sigint(signum, frame):
            print("\nReceived Ctrl+C. Cancelling running tasks...")
            for fut in futures:
                fut.cancel()
            exe.shutdown(wait=False, cancel_futures=True)
            raise KeyboardInterrupt

        RaiParser.session = self.session  # It can be shared between threads.
        with tqdm(total=len(self._urls), unit="feed") as pbar:
            with ThreadPoolExecutor(max_workers=self.workers) as exe:
                # Set up signal handler
                signal.signal(signal.SIGINT, handle_sigint)

                futures = {exe.submit(_run, url): url for url in self._urls}
                try:
                    for fut in as_completed(futures):
                        url = futures[fut]
                        pbar.update(1)
                        try:
                            _, err = fut.result()
                            if err:
                                print(f"Error with {url}: {err}")
                        except Exception as e:
                            print(f"Unhandled error with {url}: {e}")
                except KeyboardInterrupt:
                    print("\nStopped by user. Cleaning up...")

    def create_feeds(self, skip_programmi: bool, skip_film: bool) -> None:
        """Creates feeds for all collected URLs."""
        if self.workers <= 1:
            self._create_feeds_simple(skip_programmi, skip_film)
            return
        self._create_feeds_thread(skip_programmi, skip_film)
