from enum import Enum
from scrapling.fetchers import Fetcher
# from scrapling.fetchers import StealthyFetcher
import argparse
import logging
from curl_cffi.requests.exceptions import SessionClosed

# StealthyFetcher.adaptive = True
Fetcher.adaptive = True
logging.getLogger('scrapling').setLevel(logging.WARNING)
logging.getLogger('scrapling').setLevel(logging.CRITICAL)

roles = [
    "user",
    'uploader',
    "vip",
    "trial-uploader"
]

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
        self.search = [] or search
        self.remove = [] or remove
    
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
    parser.add_argument("-f", "--filter", nargs='+', help="Filter by words\nYou can use \'~\' and \'+\' to filter with or without that word.")

    args = parser.parse_args()

    search = []
    remove = []

    if (args.filter):
        for filter in args.filter:
            if (filter[0] == '+'):
                search.append(filter[1:].strip())
            elif (filter[0] == '~'):
                remove.append(filter[1:].strip())

    kitchen = Url(
        args.name, 
        category=Category[args.category] if args.category else None,
        sort=Sort[args.sort] if args.sort else None,
        ord=Ord[args.order],
        search=search,
        remove=remove
    )
    return(kitchen)

def parser() -> None:
    try:
        kitchen = argo()
        cook = kitchen.generate()
        idx = 0
        while True:
            idx += 1
            print(f"Visiting page: {idx}")
            url = cook + str(idx) + '/'
            
            try:
                page = Fetcher.get(url)
            except SessionClosed:
                raise KeyboardInterrupt
            
            if page.status != 200:
                print(f"Error: status: {page.status}")
                break
            if page.find_by_text('No results were returned.'):
                break
                
            rows = page.xpath('//tbody/tr')
            for row in rows:
                name = row.css('td.coll-1.name a::text').get()
                if kitchen.remove and any(word.lower() in name.lower() for word in kitchen.remove):
                    continue
                if kitchen.search and not any(word.lower() in name.lower() for word in kitchen.search):
                    continue
                    
                link = kitchen.base_url + row.css('td.coll-1.name a:not(.icon)::attr(href)').get()
                seeds = row.css('td.coll-2.seeds::text').get()
                leeches = row.css('td.coll-3.leeches::text').get()
                date = row.css('td.coll-date::text').get()
                
                for role in roles:
                    size = row.css(f'td.coll-4.size.mob-{role}::text').get()
                    uploader = row.css(f'td.coll-5.{role} a::text').get()
                    if size and uploader:
                        break
                        
                print(name)
                print(link)
                print(seeds)
                print(leeches)
                print(date)
                print(size)
                print(uploader)
                print('---------')
                
    except KeyboardInterrupt:
        print("\n\nSearch interrupted")
        exit(0)
