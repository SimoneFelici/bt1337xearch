from enum import Enum
import argparse
import logging
import threading
import time

import scrapling.engines.toolbelt.fingerprints as _fp

_MAX_KNOWN = 141
if _fp.chrome_version > _MAX_KNOWN:
    _fp.chrome_version = _MAX_KNOWN
if _fp.chromium_version > _MAX_KNOWN:
    _fp.chromium_version = _MAX_KNOWN

from scrapling.fetchers import StealthySession

from scrapling.fetchers import StealthySession
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, LoadingIndicator, Static

logging.getLogger("scrapling").setLevel(logging.CRITICAL)

roles = ["user", "uploader", "vip", "trial-uploader"]


class ResultWidget(Static):
    def __init__(self, result: dict, **kwargs):
        super().__init__(**kwargs)
        self.result = result

    def compose(self) -> ComposeResult:
        yield Label(f"[bold cyan]{self.result['name']}[/]")
        yield Label("[yellow]Link:[/]")
        yield Label(f"{self.result['link']}")
        yield Label(
            f"[green]Seeds:[/] {self.result['seeds']} | "
            f"[red]Leeches:[/] {self.result['leeches']}"
        )
        yield Label(
            f"[blue]Size:[/] {self.result['size']} | "
            f"[magenta]Date:[/] {self.result['date']}"
        )
        yield Label(f"[dim]Uploader: {self.result['uploader']}[/]")
        yield Label("[dim]─" * 50 + "[/]")


class MyApp(App):
    TITLE = "bt1337xearch"

    BINDINGS = [
        Binding("left,h", "prev_page", "Previous 5", show=True),
        Binding("right,l", "next_page", "Next 5", show=True),
        Binding("q", "quit", "Exit", show=True),
    ]

    RESULTS_PER_PAGE = 5
    PREFETCH_PAGES = 2
    REQUEST_DELAY = 2.0
    DEBUG_LINES = 3

    current_page: reactive[int] = reactive(0)
    is_loading: reactive[bool] = reactive(True)

    def __init__(self, kitchen, **kwargs):
        super().__init__(**kwargs)
        self.kitchen = kitchen
        self.all_results: list[dict] = []
        self.debug_lines: list[str] = []

        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()

        self._next_site_page = 1
        self._loaded_results = 0
        self._target_results = self.RESULTS_PER_PAGE
        self._reached_end = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(id="results-container")
        yield Static(id="status")
        yield Static(id="debug")
        yield Footer()

    def on_mount(self) -> None:
        self.render()
        threading.Thread(target=self.fetch_worker, daemon=True).start()

    def on_unmount(self) -> None:
        self._stop.set()
        self._wake.set()

    def add_debug_line(self, message: str) -> None:
        self.debug_lines.append(message)
        self.debug_lines = self.debug_lines[-self.DEBUG_LINES :]
        self.query_one("#debug").update(
            "\n".join(f"[dim]{line}[/]" for line in self.debug_lines)
        )

    def log_from_thread(self, message: str) -> None:
        self.call_from_thread(self.add_debug_line, message)

    def page_start(self) -> int:
        return self.current_page * self.RESULTS_PER_PAGE

    def page_end(self) -> int:
        return self.page_start() + self.RESULTS_PER_PAGE

    def wanted_results(self) -> int:
        if len(self.all_results) < self.page_end():
            return self.page_end()

        return self.page_end() + self.PREFETCH_PAGES * self.RESULTS_PER_PAGE

    def request_results(self) -> None:
        if self._reached_end:
            return

        with self._lock:
            self._target_results = max(self._target_results, self.wanted_results())

        self.is_loading = True
        self._wake.set()

    def fetch_worker(self) -> None:
        with StealthySession(headless=False, solve_cloudflare=True) as session:
            while not self._stop.is_set():
                with self._lock:
                    page_number = self._next_site_page
                    loaded = self._loaded_results
                    target = self._target_results

                if self._reached_end or loaded >= target:
                    self.call_from_thread(self.finish_loading)
                    self._wake.wait()
                    self._wake.clear()
                    continue

                url = self.kitchen.generate() + str(page_number) + "/"
                self.log_from_thread(f"fetch page={page_number}")

                if page_number > 1:
                    time.sleep(self.REQUEST_DELAY)

                try:
                    page = session.fetch(url, google_search=False)
                except Exception as e:
                    self._reached_end = True
                    self.call_from_thread(self.set_status, f"Fetch error: {e}")
                    break

                self.log_from_thread(f"status page={page_number}: {page.status}")

                if page.status != 200:
                    self._reached_end = True
                    self.call_from_thread(
                        self.set_status,
                        f"HTTP {page.status} on page {page_number}",
                    )
                    break

                if page.find_by_text("No results were returned."):
                    self._reached_end = True
                    break

                rows_count = len(page.xpath("//tbody/tr"))
                new_results = self.parse_page(page)

                with self._lock:
                    self._next_site_page += 1
                    self._loaded_results += len(new_results)
                    loaded = self._loaded_results
                    target = self._target_results

                self.log_from_thread(
                    f"page={page_number} rows={rows_count} "
                    f"matched={len(new_results)} loaded={loaded}/{target}"
                )

                if new_results:
                    self.call_from_thread(self.append_results, new_results)

        self.call_from_thread(self.finish_loading)

    def finish_loading(self) -> None:
        self.is_loading = False
        self.render()

    def parse_page(self, page) -> list[dict]:
        results = []

        for row in page.xpath("//tbody/tr"):
            name = row.css("td.coll-1.name a::text").get()
            if not name or not self.matches_filters(name):
                continue

            href = row.css("td.coll-1.name a:not(.icon)::attr(href)").get()
            if not href:
                continue

            size, uploader = self.extract_size_and_uploader(row)

            results.append(
                {
                    "name": name,
                    "link": self.kitchen.base_url + href,
                    "seeds": row.css("td.coll-2.seeds::text").get(),
                    "leeches": row.css("td.coll-3.leeches::text").get(),
                    "date": row.css("td.coll-date::text").get(),
                    "size": size,
                    "uploader": uploader,
                }
            )

        return results

    def matches_filters(self, name: str) -> bool:
        name = name.lower()

        if any(word.lower() in name for word in self.kitchen.remove):
            return False

        if not self.kitchen.search:
            return True

        match_fn = all if self.kitchen.match_all else any
        return match_fn(word.lower() in name for word in self.kitchen.search)

    def extract_size_and_uploader(self, row) -> tuple[str | None, str | None]:
        for role in roles:
            size = row.css(f"td.coll-4.size.mob-{role}::text").get()
            uploader = row.css(f"td.coll-5.{role} a::text").get()

            if size and uploader:
                return size, uploader

        return None, None

    def append_results(self, new_results: list[dict]) -> None:
        self.all_results.extend(new_results)
        self.render()
        self.request_results()

    def set_status(self, message: str) -> None:
        self.query_one("#status").update(message)

    def watch_current_page(self, _: int) -> None:
        self.render()

    def watch_is_loading(self, _: bool) -> None:
        self.render()

    def render(self) -> None:
        container = self.query_one("#results-container")
        container.remove_children()

        start = self.page_start()
        end = self.page_end()
        page_results = self.all_results[start:end]

        page_ready = len(page_results) == self.RESULTS_PER_PAGE
        last_partial_page = self._reached_end and bool(page_results)

        if page_ready or last_partial_page:
            for result in page_results:
                container.mount(ResultWidget(result))
        elif self.is_loading:
            container.mount(LoadingIndicator())
        else:
            container.mount(Label("[yellow]No results[/]"))

        total = len(self.all_results)
        total_pages = max(
            1, (total + self.RESULTS_PER_PAGE - 1) // self.RESULTS_PER_PAGE
        )
        visible_end = min(end, total)
        suffix = " | Loading..." if self.is_loading else ""

        if total == 0:
            range_text = "Results 0 of 0"
        elif page_ready or last_partial_page:
            range_text = f"Results {start + 1}-{visible_end} of {total}"
        else:
            range_text = f"Loaded {total} results"

        self.query_one("#status").update(
            f"Page {self.current_page + 1}/{total_pages} | {range_text}{suffix}"
        )

    def action_next_page(self) -> None:
        next_page = self.current_page + 1
        next_page_start = next_page * self.RESULTS_PER_PAGE

        if len(self.all_results) > next_page_start:
            self.current_page = next_page

        if not self._reached_end:
            self.request_results()

    def action_prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1

        if not self._reached_end:
            self.request_results()


class Category(Enum):
    MOVIE = "Movies"
    TV = "TV"
    GAME = "Games"
    MUSIC = "Music"
    APP = "Apps"
    DOCU = "Documentaries"
    ANIME = "Anime"
    OTHER = "Other"
    XXX = "XXX"


class Sort(Enum):
    TIME = "time"
    SIZE = "size"
    SEED = "seeders"
    LEECH = "leechers"


class Ord(Enum):
    ASC = "asc"
    DESC = "desc"


class Url:
    base_url = "https://1337x.to"

    def __init__(
        self,
        name: str,
        category: Category = None,
        sort: Sort = None,
        ord: Ord = Ord.DESC,
        search: list[str] = None,
        remove: list[str] = None,
        match_all: bool = False,
    ):
        self.name = name
        self.category = category
        self.sort = sort
        self.ord = ord
        self.search = search or []
        self.remove = remove or []
        self.match_all = match_all

    def generate(self) -> str:
        search_name = self.name.replace(" ", "+")

        if self.sort and self.category:
            return (
                f"{self.base_url}/sort-category-search/"
                f"{search_name}/{self.category.value}/{self.sort.value}/{self.ord.value}/"
            )

        if self.sort:
            return (
                f"{self.base_url}/sort-search/"
                f"{search_name}/{self.sort.value}/{self.ord.value}/"
            )

        if self.category:
            return (
                f"{self.base_url}/category-search/{search_name}/{self.category.value}/"
            )

        return f"{self.base_url}/search/{search_name}/"


def argo() -> Url:
    arg_parser = argparse.ArgumentParser(
        prog="bt1337xearch",
        description="Better search for 1337x[.]to",
        epilog="Example:\nbt1337xearch -n Dexter -c TV -s TIME -o ASC",
    )
    arg_parser.add_argument("-n", "--name", help="Name of the Media", required=True)
    arg_parser.add_argument(
        "-c",
        "--category",
        choices=[
            "MOVIE",
            "TV",
            "GAME",
            "MUSIC",
            "APP",
            "DOCU",
            "ANIME",
            "OTHER",
            "XXX",
        ],
    )
    arg_parser.add_argument("-s", "--sort", choices=["TIME", "SIZE", "SEED", "LEECH"])
    arg_parser.add_argument("-o", "--order", choices=["ASC", "DESC"], default="DESC")
    arg_parser.add_argument("-f", "--filter", nargs="+")
    arg_parser.add_argument("--match-all", action="store_true")

    args = arg_parser.parse_args()

    search: list[str] = []
    remove: list[str] = []

    for word in args.filter or []:
        word = word.strip()

        if word.startswith("+"):
            search.append(word[1:].strip())
        elif word.startswith("~"):
            remove.append(word[1:].strip())
        else:
            arg_parser.error(f"Invalid filter {word!r}. Use +word or ~word.")

    return Url(
        args.name,
        category=Category[args.category] if args.category else None,
        sort=Sort[args.sort] if args.sort else None,
        ord=Ord[args.order],
        search=search,
        remove=remove,
        match_all=args.match_all,
    )


def parser() -> None:
    try:
        app = MyApp(argo(), ansi_color=True)
        app.run()
    except KeyboardInterrupt:
        print("\n\nSearch interrupted")
        exit(0)
