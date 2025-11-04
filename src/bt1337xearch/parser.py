from enum import Enum
from scrapling.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher

StealthyFetcher.adaptive = True

roles = [
    "user",
    'uploader',
    "vip",
    "trial-uploader"
]

class Category(Enum):
    MOVIES = "Movies"
    TV = "TV"
    GAMES = "Games"
    MUSIC = "Music"
    APPS = "Apps"
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

class URL:
    base_url = "https://1337x.to"

    def __init__(self, name: str, category: Category = None, sort: Sort = None, ord: Ord = Ord.DESC):
        self.name = name
        self.category = category
        self.sort = sort
        self.ord = ord
    
    def generate(self) -> str:
        search_name = self.name.replace(" ", "+")

        if self.sort and self.category:
            return f"{self.base_url}/sort-category-search/{search_name}/{self.category.value}/{self.sort.value}/{self.ord.value}/1/"
        elif self.sort:
            return f"{self.base_url}/sort-search/{search_name}/{self.sort.value}/{self.ord.value}/1/"
        elif self.category:
            return f"{self.base_url}/category-search/{search_name}/{self.category.value}/1/"
        else:
            return f"{self.base_url}/search/{search_name}/1/"


def parser() -> None:
    # Those 2 get filtered by cloudflare idk why
    # kitchen = URL("Inception", sort=Sort.TIME)
    # kitchen = URL("Inception")

    kitchen = URL("Dexter", category=Category.MOVIES, sort=Sort.TIME, ord=Ord.DESC)
    # kitchen = URL("Inception", category=Category.MOVIES)

    url = kitchen.generate()
    page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
    print(page.status)

    rows = page.xpath('//tbody/tr')

    for row in rows:
        name = row.css('td.coll-1.name a::text').get()
        print(name)

        seeds = row.css('td.coll-2.seeds::text').get()
        print(seeds)

        leeches = row.css('td.coll-3.leeches::text').get()
        print(leeches)

        date = row.css('td.coll-date::text').get()
        print(date)

        for role in roles:
            size = row.css(f'td.coll-4.size.mob-{role}::text').get()
            uploader = row.css(f'td.coll-5.{role} a::text').get()
            if size and uploader:
                break

        print(size)
        print(uploader)

        # exit(1)
        print('---------')
