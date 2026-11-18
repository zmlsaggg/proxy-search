# TELEGRAM PROXY SEARCHER

<p align="center">
  Поиск публичных Telegram-прокси на GitHub и проверка HTTP/SOCKS-подключений прямо из твоей сети.
</p>

<p align="center">
  <a href="https://pypi.org/project/proxy-search/"><img src="https://img.shields.io/pypi/v/proxy-search?style=flat-square&logo=pypi&logoColor=white&label=PyPI&color=0EA5E9" alt="PyPI version"></a>
  <a href="https://github.com/zmlsaggg/proxy-search/releases/latest"><img src="https://img.shields.io/github/v/release/zmlsaggg/proxy-search?style=flat-square&logo=github&label=release&color=0284C7" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <a href="https://github.com/zmlsaggg/proxy-search/releases/latest"><img src="https://img.shields.io/badge/Windows-EXE-0078D4?style=flat-square&logo=windows&logoColor=white" alt="Windows executable"></a>
</p>

## Установка через pip

Нужен Python 3.11 или новее. Имя пакета в PyPI — `proxy-search`, команда запуска — `telegram-proxy-searcher`.

### Windows (PowerShell)

```powershell
py -m pip install --upgrade proxy-search
telegram-proxy-searcher
```

### Linux и macOS

```sh
python3 -m pip install --upgrade proxy-search
telegram-proxy-searcher
```

Если система запрещает установку в системный Python (например, сообщает об externally managed environment), создай виртуальное окружение и устанавливай пакет внутри него:

```powershell
# Windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```sh
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

После активации окружения на любой системе:

```sh
python -m pip install --upgrade proxy-search
telegram-proxy-searcher
```

Обновить пакет: `python -m pip install --upgrade proxy-search`. Удалить: `python -m pip uninstall proxy-search`.

Для отдельной установки консольной утилиты также подойдёт `pipx install proxy-search`.
Локальная база и список рабочих прокси сохраняются в пользовательской папке данных Windows, macOS или Linux, а не внутри каталога Python.

## Запуск из исходников


Console utility by **zmlsag**. Searches GitHub repositories for Telegram proxy lists, extracts supported formats, checks HTTP/SOCKS proxies against Telegram from the user's current network, and stores results locally.

### Windows
1. Install Python 3.11+.
2. Run install.bat once.
3. Run start.bat.

Optional GitHub token (PowerShell):
    $env:GITHUB_TOKEN="github_pat_..."
    .\start.bat

### Menu
1. Find working proxies — search GitHub, index repositories, extract endpoints, check them.
2. Update proxy database — rescan repositories already saved locally.
3. Check application updates from this repository.
4. View results and copy confirmed working proxies.

Local database: data/database.json. Confirmed HTTP/SOCKS endpoints: data/working.txt.

### Verification
- HTTP and SOCKS5 are WORKING only after a request to Telegram HTTPS succeeds through that proxy.
- MTProto entries are marked REVIEW when the TCP port accepts a connection. TCP reachability alone does not prove an MTProto handshake, so they are excluded from automatic copy.
- Checks run from the computer launching the tool and reflect its current ISP/network route.
- Repository content is treated as untrusted text. No downloaded repository code is executed.
- Unauthenticated GitHub search is rate-limited; set GITHUB_TOKEN for higher limits.

Supported formats: tg://proxy links, t.me/proxy links, socks5/http URLs, and IPv4:port candidates.
