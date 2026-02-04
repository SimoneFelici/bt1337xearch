# **bt1337xearch**
Better search for 1337x[.]to with basic filters

## What it does
**bt1337xearch** is a command-line tool that searches 1337x[.]to torrents with:
- Category filtering (Movies, TV, Games, etc.)
- Sorting options (by time, size, seeders, leechers)
- Keyword filtering (include/exclude keywords)

## Prerequisites
**bt1337xearch** uses scrapling StealthyFetcher for bypassing the Cloudflare Captcha. \
The StealthyFetcher uses a custom playwrigth build to made that happen. \
You can install this playwright version using Scrapling:

```bash
uvx scrapling[shell] install
```
> [!WARNING]
> If the "Installing Playwright dependencies..." step fails, **bt1337xearch** should still work (e.g., Arch-based distros).

## Installation
```bash
uv tool install bt1337xearch
```
or
```bash
git clone https://github.com/SimoneFelici/bt1337xearch.git
cd bt1337xearch
uv tool install .
```

## Usage
> [!TIP]
> Use "ctrl + p" to display the TUI keybindings!


### Basic search
```bash
bt1337xearch -n "Dexter"
```

### Search with category (Recommended)
```bash
bt1337xearch -n "Lupin" -c ANIME
```

### Search with sorting
```bash
bt1337xearch -n "Alien" -c MOVIE -s TIME -o DESC
```

### Advanced filtering
Use `+` to include words and `~` to exclude words:
```bash
# Include only results with "1080p" or "BluRay"
bt1337xearch -n "Dexter" -f +1080p +BluRay

# Exclude results with "CAM" or "TS"
bt1337xearch -n "Movie" -f ~CAM ~TS

# Combine include and exclude
bt1337xearch -n "Dexter" -c TV -f +1080p "~x265 HEVC" ~CAM
```

## Options

| Option | Description | Choices |
|--------|-------------|---------|
| `-n, --name` | Name of the media (required) | - |
| `-c, --category` | Filter by category | MOVIE, TV, GAME, MUSIC, APP, DOCU, ANIME, OTHER, XXX |
| `-s, --sort` | Sort results by | TIME, SIZE, SEED, LEECH |
| `-o, --order` | Sort order (default: DESC) | ASC, DESC |
| `-f, --filter` | Filter by keywords | Use `+word` to include, `~word` to exclude |

## Examples
```bash
# Search for Dexter TV series, sorted by seeders
bt1337xearch -n Dexter -c TV -s SEED

# Search for movies with "1080p", exclude "CAM" releases
bt1337xearch -n "Angel's Egg" -c MOVIE -s TIME -o DESC -f +1080p '~CAM'

# Search for games, sorted by upload time
bt1337xearch -n "Peak" -c GAME -s TIME -o ASC
```

## Output

For each result, the tool displays:
- Name
- Link
- Seeders
- Leechers
- Upload date
- File size
- Uploader

<img width="1920" height="1119" alt="image" src="https://github.com/user-attachments/assets/0174586f-5a31-4a42-a7fb-b378257a2fd3" />
