from enum import Enum
from scrapling.fetchers import StealthySession
import argparse
import logging
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label, LoadingIndicator
from textual.containers import VerticalScroll, Vertical
from textual.binding import Binding
import asyncio
import threading
from queue import Queue

logging.getLogger('scrapling').setLevel(logging.WARNING)
logging.getLogger('scrapling').setLevel(logging.CRITICAL)

roles = [
    "user",
    'uploader',
    "vip",
    "trial-uploader"
]

class ResultWidget(Static):
    def __init__(self, result: dict, **kwargs):
        super().__init__(**kwargs)
        self.result = result
        
    def compose(self) -> ComposeResult:
        yield Label(f"[bold cyan]{self.result['name']}[/]")
        yield Label(f"[yellow]Link:[/]")
        yield Label(f"{self.result['link']}")
        yield Label(f"[green]Seeds:[/] {self.result['seeds']} | [red]Leeches:[/] {self.result['leeches']}")
        yield Label(f"[blue]Size:[/] {self.result['size']} | [magenta]Date:[/] {self.result['date']}")
        yield Label(f"[dim]Uploader: {self.result['uploader']}[/]")
        yield Label("[dim]─" * 50 + "[/]")

class MyApp(App):
    TITLE = "bt1337xearch"
    
    BINDINGS = [
        Binding("left,h", "prev_page", "Previous 5", show=True),
        Binding("right,l", "next_page", "Next 5", show=True),
        Binding("q", "quit", "Esci", show=True),
    ]
    
    def __init__(self, kitchen, **kwargs):
        super().__init__(**kwargs)
        self.kitchen = kitchen
        self.all_results = []
        self.current_page = 0
        self.results_per_page = 5
        self.fetched_pages = set()
        self.fetching_pages = set()
        self.max_page_number = None
        self.session = None
        self.fetch_queue = Queue()
        self.fetch_thread = None
        self.should_stop = False
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="results-container"):
            yield LoadingIndicator(id="loading")
        yield Static(id="status")
        yield Footer()
        
    def on_mount(self):
        self.update_status("Initializing...")
        self.fetch_thread = threading.Thread(target=self._fetch_worker, daemon=True)
        self.fetch_thread.start()
        self.update_status("Loading...")
        self.fetch_page_async(1)
        
    def on_unmount(self):
        self.should_stop = True
        if self.fetch_queue:
            self.fetch_queue.put(None)
        
    def _fetch_worker(self):
        with StealthySession(headless=True, solve_cloudflare=True) as session:
            self.session = session
            while not self.should_stop:
                page_number = self.fetch_queue.get()
                if page_number is None:
                    break
                self._fetch_page_sync(page_number)
                self.fetch_queue.task_done()
        
    def fetch_page_async(self, page_number: int):
        if page_number in self.fetched_pages or page_number in self.fetching_pages:
            return
            
        if self.max_page_number and page_number > self.max_page_number:
            return
            
        self.fetching_pages.add(page_number)
        self.fetch_queue.put(page_number)
        
    def _fetch_page_sync(self, page_number: int):
        cook = self.kitchen.generate()
        url = cook + str(page_number) + '/'
        
        try:
            page = self.session.fetch(url, google_search=False)
            
            if page.status != 200:
                self.max_page_number = page_number - 1
                self.fetching_pages.discard(page_number)
                return
                
            if page.find_by_text('No results were returned.'):
                self.max_page_number = page_number - 1
                self.fetching_pages.discard(page_number)
                return
                
            rows = page.xpath('//tbody/tr')
            page_results = []
            
            for row in rows:
                name = row.css('td.coll-1.name a::text').get()
                if not name:
                    continue
                    
                if self.kitchen.remove and any(word.lower() in name.lower() for word in self.kitchen.remove):
                    continue
                if self.kitchen.search and not any(word.lower() in name.lower() for word in self.kitchen.search):
                    continue
                    
                link = self.kitchen.base_url + row.css('td.coll-1.name a:not(.icon)::attr(href)').get()
                seeds = row.css('td.coll-2.seeds::text').get()
                leeches = row.css('td.coll-3.leeches::text').get()
                date = row.css('td.coll-date::text').get()
                
                size = None
                uploader = None
                for role in roles:
                    size = row.css(f'td.coll-4.size.mob-{role}::text').get()
                    uploader = row.css(f'td.coll-5.{role} a::text').get()
                    if size and uploader:
                        break
                
                page_results.append({
                    'name': name,
                    'link': link,
                    'seeds': seeds,
                    'leeches': leeches,
                    'date': date,
                    'size': size,
                    'uploader': uploader,
                    'page': page_number
                })
            
            self.all_results.extend(page_results)
            self.fetched_pages.add(page_number)
            self.fetching_pages.discard(page_number)
            
            self.call_from_thread(self.show_current_page)
            
        except Exception as e:
            self.fetching_pages.discard(page_number)
            self.call_from_thread(self.update_status, f"Page error {page_number}: {str(e)}")
        
    def get_results_for_display_page(self, display_page: int) -> list:
        start_idx = display_page * self.results_per_page
        end_idx = start_idx + self.results_per_page
        return self.all_results[start_idx:end_idx]
    
    def show_current_page(self):
        container = self.query_one("#results-container")
        container.remove_children()
        
        page_results = self.get_results_for_display_page(self.current_page)
        
        if not page_results and self.current_page == 0:
            container.mount(LoadingIndicator())
            self.update_status("Loading...")
        elif not page_results:
            container.mount(Label("[yellow]No results[/]"))
        else:
            for result in page_results:
                container.mount(ResultWidget(result))
        
        total_results = len(self.all_results)
        fetched_count = len(self.fetched_pages)
        fetching_count = len(self.fetching_pages)
        
        total_pages = (total_results + self.results_per_page - 1) // self.results_per_page if total_results > 0 else 1
        start_idx = self.current_page * self.results_per_page + 1
        end_idx = min((self.current_page + 1) * self.results_per_page, total_results)
        
        status_msg = f"Page {self.current_page + 1}/{total_pages} | Results {start_idx}-{end_idx} of {total_results}"
        if fetching_count > 0:
            status_msg += f" | Loading... (pages: {fetched_count})"
        else:
            status_msg += f" | Loaded pages: {fetched_count}"
            
        self.update_status(status_msg)
        
        self.prefetch_pages()
        
    def prefetch_pages(self):
        current_result_start = self.current_page * self.results_per_page
        current_result_end = current_result_start + self.results_per_page
        
        results_per_site_page = 20
        
        pages_ahead = 3
        future_result_end = current_result_end + (pages_ahead * self.results_per_page)
        
        site_pages_needed = (future_result_end // results_per_site_page) + 2
        
        for site_page in range(1, site_pages_needed + 1):
            self.fetch_page_async(site_page)
        
    def update_status(self, message: str):
        try:
            status = self.query_one("#status")
            status.update(message)
        except:
            pass
        
    def action_next_page(self):
        total_results = len(self.all_results)
        max_page = (total_results - 1) // self.results_per_page
        
        if total_results == 0 or self.current_page < max_page:
            self.current_page += 1
            self.show_current_page()
            
    def action_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_current_page()

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

    def __init__(self, name: str, category: Category = None, sort: Sort = None, ord: Ord = Ord.DESC, search: list[str] = None, remove: list[str] = None):
        self.name = name
        self.category = category
        self.sort = sort
        self.ord = ord
        self.search = search or []
        self.remove = remove or []
    
    def generate(self) -> str:
        search_name = self.name.replace(" ", "+")

        if self.sort and self.category:
            return f"{self.base_url}/sort-category-search/{search_name}/{self.category.value}/{self.sort.value}/{self.ord.value}/"
        elif self.sort:
            return f"{self.base_url}/sort-search/{search_name}/{self.sort.value}/{self.ord.value}/"
        elif self.category:
            return f"{self.base_url}/category-search/{search_name}/{self.category.value}/"
        else:
            return f"{self.base_url}/search/{search_name}/"

def argo() -> Url:
    parser = argparse.ArgumentParser(
        prog='bt1337xearch',
        description='Better search for 1337x[.]to',
        epilog='Example:\nbt1337xearch -n Dexter -c TV -s TIME -o ASC'
    )
    parser.add_argument("-n", "--name", help="Name of the Media", required=True)
    parser.add_argument("-c", "--category", help="Category", choices=['MOVIE', 'TV', 'GAME', 'MUSIC', 'APP', 'DOCU', 'ANIME', 'OTHER', 'XXX'])
    parser.add_argument("-s", "--sort", help="Sort by", choices=['TIME', 'SIZE', 'SEED', 'LEECH'])
    parser.add_argument("-o", "--order", help="Order by", choices=['ASC', 'DESC'], default='DESC')
    parser.add_argument("-f", "--filter", nargs='+', help="Filter by words\nYou can use '~' and '+' to filter with or without that word.")

    args = parser.parse_args()

    search = []
    remove = []

    if args.filter:
        for filter_word in args.filter:
            if filter_word[0] == '+':
                search.append(filter_word[1:].strip())
            elif filter_word[0] == '~':
                remove.append(filter_word[1:].strip())

    kitchen = Url(
        args.name, 
        category=Category[args.category] if args.category else None,
        sort=Sort[args.sort] if args.sort else None,
        ord=Ord[args.order],
        search=search,
        remove=remove
    )
    return kitchen

def parser() -> None:
    try:
        kitchen = argo()
        app = MyApp(kitchen, ansi_color=True)
        app.run()
                
    except KeyboardInterrupt:
        print("\n\nSearch interrupted")
        exit(0)

if __name__ == "__main__":
    parser()
