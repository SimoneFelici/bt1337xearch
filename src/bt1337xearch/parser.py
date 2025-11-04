from scrapling.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher

base_url = "https://1337x.to/category-search/Dexter/Movies/1/"

def parser() -> None:
    res = StealthyFetcher.fetch(base_url, headless=True, network_idle=True)
    print(res.status)
