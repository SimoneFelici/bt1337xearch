from enum import Enum

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
    url1 = URL("Inception", sort=Sort.TIME)
    print(url1.generate())
    
    url2 = URL("Inception", category=Category.MOVIES)
    print(url2.generate())
    
    url3 = URL("Inception", category=Category.MOVIES, sort=Sort.TIME, ord=Ord.ASC)
    print(url3.generate())
    
    url4 = URL("Inception")
    print(url4.generate())
