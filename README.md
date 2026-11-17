# TELEGRAM PROXY SEARCHER

Console utility by **zmlsag**. Searches GitHub repositories for Telegram proxy lists, extracts supported formats, checks HTTP/SOCKS proxies against Telegram from the user's current network, and stores results locally.

## Windows
1. Install Python 3.11+.
2. Run install.bat once.
3. Run start.bat.

Optional GitHub token (PowerShell):
    $env:GITHUB_TOKEN="github_pat_..."
    .\start.bat

## Menu
1. Find working proxies — search GitHub, index repositories, extract endpoints, check them.
2. Update proxy database — rescan repositories already saved locally.
3. Check application updates from this repository.
4. View results and copy confirmed working proxies.

Local database: data/database.json. Confirmed HTTP/SOCKS endpoints: data/working.txt.

## Verification
- HTTP and SOCKS5 are WORKING only after a request to Telegram HTTPS succeeds through that proxy.
- MTProto entries are marked REVIEW when the TCP port accepts a connection. TCP reachability alone does not prove an MTProto handshake, so they are excluded from automatic copy.
- Checks run from the computer launching the tool and reflect its current ISP/network route.
- Repository content is treated as untrusted text. No downloaded repository code is executed.
- Unauthenticated GitHub search is rate-limited; set GITHUB_TOKEN for higher limits.

Supported formats: tg://proxy links, t.me/proxy links, socks5/http URLs, and IPv4:port candidates.
