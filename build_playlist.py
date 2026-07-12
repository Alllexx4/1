from __future__ import annotations

import re
import urllib.request
from pathlib import Path

SOURCES = {
    "Россия": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "Украина": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ua.m3u",
    "Израиль": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/il.m3u",
}

CATEGORY_RULES = [
    ("Спорт", ["sport", "спорт", "khl", "fight", "football", "футбол", "hockey", "хоккей"]),
    ("Музыка", ["music", "музык", "muz", "ru.tv", "m2", "songtv", "dance"]),
    ("Кино", ["kino", "кино", "cinema", "film", "movie", "tv1000", "dom kino", "rodnoe kino"]),
    ("Познавательные", ["history", "science", "doctor", "travel", "nature", "zoopark", "big asia", "univer"]),
    ("Детские", ["kids", "дет", "nick", "disney", "junior", "tiji", "multilandia", "ryzhiy", "hop"]),
    ("Новости", ["news", "новост", "24", "i24", "freedom", "rt", "knesset"]),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_m3u(text: str):
    lines = [line.strip() for line in text.replace("\r", "").split("\n")]
    entry = []
    for line in lines:
        if not line or line == "#EXTM3U":
            continue
        if line.startswith("#EXTINF"):
            if entry:
                entry = []
            entry = [line]
        elif entry and line.startswith("#EXTVLCOPT"):
            entry.append(line)
        elif entry and not line.startswith("#"):
            entry.append(line)
            yield entry
            entry = []


def channel_name(extinf: str) -> str:
    return extinf.rsplit(",", 1)[-1].strip()


def classify(name: str, country: str) -> str:
    n = name.lower()
    for category, keys in CATEGORY_RULES:
        if any(key in n for key in keys):
            return category
    return country


def set_group(extinf: str, group: str) -> str:
    if 'group-title=' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"', 1)


def main() -> None:
    all_entries = []
    seen_urls = set()
    for country, url in SOURCES.items():
        text = fetch(url)
        for entry in parse_m3u(text):
            stream_url = entry[-1]
            if stream_url in seen_urls:
                continue
            seen_urls.add(stream_url)
            name = channel_name(entry[0])
            group = classify(name, country)
            entry[0] = set_group(entry[0], group)
            all_entries.append((group, name.lower(), entry))

    order = {name: i for i, name in enumerate(["Россия", "Украина", "Израиль", "Кино", "Познавательные", "Спорт", "Музыка", "Детские", "Новости"])}
    all_entries.sort(key=lambda x: (order.get(x[0], 99), x[1]))

    out = ['#EXTM3U url-tvg="https://iptv-org.github.io/epg/guides/ru.xml,https://iptv-org.github.io/epg/guides/il.xml,https://iptv-org.github.io/epg/guides/ua.xml"']
    for _, _, entry in all_entries:
        out.extend(entry)
    Path("AlexanderTV.m3u").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Created AlexanderTV.m3u with {len(all_entries)} channels")


if __name__ == "__main__":
    main()
