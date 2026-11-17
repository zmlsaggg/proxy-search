from __future__ import annotations
import asyncio, base64, ipaddress, json, os, re, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

APP="TELEGRAM PROXY SEARCHER"; VERSION="1.0.0"; OWNER="zmlsaggg"; REPO="proxy-search"
ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"; DB_FILE=DATA/"database.json"; WORKING_FILE=DATA/"working.txt"
QUERIES=["mtproxy", '"mtproto proxy"', '"telegram proxy"', "tg://proxy", '"telegram bypass" proxy', "mtproto", "telegram socks5 proxy", "telegram-proxy-list", "телеграм прокси"]
MAX_REPO_FILES=35; MAX_FILE_BYTES=450_000; TIMEOUT=7.0
console=Console()

def now(): return datetime.now(timezone.utc).isoformat()
def load_db():
    DATA.mkdir(exist_ok=True)
    if not DB_FILE.exists(): return {"version":1,"repositories":{},"proxies":{}}
    try:
        d=json.loads(DB_FILE.read_text("utf-8")); d.setdefault("repositories",{}); d.setdefault("proxies",{}); return d
    except (OSError,json.JSONDecodeError):
        try: shutil.copy2(DB_FILE,DB_FILE.with_suffix(".corrupt.json"))
        except OSError: pass
        return {"version":1,"repositories":{},"proxies":{}}
def save_db(db):
    DATA.mkdir(exist_ok=True); tmp=DB_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(db,ensure_ascii=False,indent=2),"utf-8"); tmp.replace(DB_FILE)
def gh_headers():
    h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":APP}
    token=os.getenv("GITHUB_TOKEN","").strip()
    if token: h["Authorization"]="Bearer "+token
    return h

def normalize(raw):
    v=raw.strip().strip(chr(96)+"'\\\"()[]{}<>,;")
    if not v or len(v)>700: return None
    if v.startswith(("tg://proxy?","tg://socks?","https://t.me/proxy?","https://t.me/socks?")):
        p=urlparse(v.replace("https://t.me/","tg://")); q=parse_qs(p.query)
        host=(q.get("server") or q.get("host") or [""])[0]; port=(q.get("port") or [""])[0]; secret=(q.get("secret") or [""])[0]
        try:
            ipaddress.ip_address(host); port=int(port)
            if 1<=port<=65535 and secret:
                return {"id":f"mtproto://{host}:{port}/{secret}","type":"MTProto","host":host,"port":port,"secret":secret,"source":""}
        except (ValueError,TypeError): pass
        return None
    if "://" in v:
        p=urlparse(v); scheme=p.scheme.lower()
        if scheme not in ("socks5","socks5h","http","https"): return None
        try: host,port=p.hostname,p.port
        except ValueError: return None
        if host and port: return {"id":f"{'socks5' if scheme.startswith('socks') else 'http'}://{host}:{port}","type":"SOCKS5" if scheme.startswith("socks") else "HTTP","host":host,"port":port,"username":p.username,"password":p.password,"source":""}
        return None
    m=re.fullmatch(r"((?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})",v)
    if m:
        try:
            host=m.group(1); ipaddress.IPv4Address(host); port=int(m.group(2))
            if 1<=port<=65535: return {"id":f"socks5://{host}:{port}","type":"SOCKS5","host":host,"port":port,"username":None,"password":None,"source":""}
        except ValueError: pass
    return None

def extract(text):
    pats=[r"tg://(?:proxy|socks)\?[^\s\\\"'<>]+",r"https://t\.me/(?:proxy|socks)\?[^\s\\\"'<>]+",r"(?:socks5h?|https?)://[^\s\\\"'<>]+",r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}(?!\d)"]
    out={}
    for pat in pats:
        for raw in re.findall(pat,text,re.I):
            item=normalize(raw)
            if item: out[item["id"]]=item
    return list(out.values())

async def gh_json(client,url,params=None):
    r=await client.get(url,params=params,headers=gh_headers()); r.raise_for_status(); return r.json()
async def search_repos(client,progress,task):
    found={}
    for query in QUERIES:
        progress.update(task,description=f"[cyan]GitHub: {query[:38]}")
        try:
            data=await gh_json(client,"https://api.github.com/search/repositories",{"q":query+" archived:false","sort":"updated","order":"desc","per_page":50,"page":1})
            for r in data.get("items",[]):
                if r.get("fork") or r.get("archived"): continue
                found[r["full_name"]]={"full_name":r["full_name"],"html_url":r["html_url"],"default_branch":r.get("default_branch") or "main","description":r.get("description") or "","stars":r.get("stargazers_count",0),"updated_at":r.get("updated_at"),"added_at":now()}
        except httpx.HTTPStatusError as e:
            if e.response.status_code==403:
                console.print("[yellow]GitHub ограничил поиск. Установи GITHUB_TOKEN для увеличения лимита.[/]"); break
            console.print(f"[dim]Пропуск {query}: HTTP {e.response.status_code}[/]")
        except (httpx.HTTPError,ValueError) as e: console.print(f"[dim]Ошибка поиска {query}: {e}[/]")
        progress.advance(task)
    return found

async def scan_repo(client,repo):
    full=repo["full_name"]; branch=repo.get("default_branch") or "main"
    try: tree=await gh_json(client,f"https://api.github.com/repos/{full}/git/trees/{branch}",{"recursive":"1"})
    except (httpx.HTTPError,ValueError): return []
    paths=[]
    for n in tree.get("tree",[]):
        path=n.get("path",""); low=path.lower()
        if n.get("type")=="blob" and n.get("size",MAX_FILE_BYTES+1)<=MAX_FILE_BYTES and low.endswith((".md",".txt",".json",".yaml",".yml",".conf",".ini",".list",".csv")) and any(k in low for k in ("readme","proxy","config","list","server","mtproto","telegram","socks","sub")):
            paths.append(path)
    found={}
    for path in paths[:MAX_REPO_FILES]:
        try:
            r=await client.get(f"https://raw.githubusercontent.com/{full}/{branch}/{path}",headers={"User-Agent":APP})
            if r.status_code!=200: continue
            for item in extract(r.text):
                item["source"]=f"https://github.com/{full}/blob/{branch}/{path}"; found[item["id"]]=item
        except httpx.HTTPError: pass
    return list(found.values())

async def collect(db,refresh=False):
    async with httpx.AsyncClient(timeout=httpx.Timeout(15,connect=8),limits=httpx.Limits(max_connections=12),follow_redirects=True) as client:
        if not refresh:
            with Progress(SpinnerColumn(),TextColumn("{task.description}"),BarColumn(),TimeElapsedColumn(),console=console) as p:
                task=p.add_task("[cyan]Ищу GitHub-репозитории...",total=len(QUERIES)); repos=await search_repos(client,p,task)
            for name,info in repos.items():
                db["repositories"].setdefault(name,info); db["repositories"][name].update({k:v for k,v in info.items() if k in ("stars","updated_at","description","default_branch","html_url")})
            console.print(f"[green]Найдено: {len(repos)} новых/обновлённых совпадений. В базе репозиториев: {len(db['repositories'])}[/]")
        repos=list(db["repositories"].values()); sem=asyncio.Semaphore(8); added=0
        async def run(repo):
            async with sem: return repo,await scan_repo(client,repo)
        with Progress(SpinnerColumn(),TextColumn("{task.description}"),BarColumn(),TextColumn("{task.completed}/{task.total}"),console=console) as p:
            task=p.add_task("[cyan]Сканирую сохранённые репозитории...",total=len(repos))
            for future in asyncio.as_completed([run(r) for r in repos]):
                repo,items=await future; repo["scanned_at"]=now()
                for item in items:
                    item["last_seen"]=now(); old=db["proxies"].get(item["id"])
                    if old is None: added+=1
                    db["proxies"][item["id"]]={**(old or {}),**item}
                p.advance(task)
        save_db(db); console.print(f"[green]Новых прокси: {added}. Всего уникальных: {len(db['proxies'])}[/]")

async def probe(item):
    kind,host,port=item["type"],item["host"],int(item["port"])
    if kind=="MTProto":
        try:
            reader,writer=await asyncio.wait_for(asyncio.open_connection(host,port),TIMEOUT); writer.close(); await writer.wait_closed()
            return "REVIEW","TCP открыт; MTProto handshake ещё не подтверждён"
        except Exception as e: return "DEAD",type(e).__name__
    scheme="socks5" if kind=="SOCKS5" else "http"; auth=""
    if item.get("username"): auth=f"{item['username']}:{item.get('password') or ''}@"
    try:
        async with httpx.AsyncClient(proxy=f"{scheme}://{auth}{host}:{port}",timeout=TIMEOUT,follow_redirects=True) as c:
            r=await c.get("https://api.telegram.org/")
            if r.status_code<500: return "WORKING",f"Telegram HTTPS HTTP {r.status_code}"
            return "DEAD",f"Telegram HTTPS HTTP {r.status_code}"
    except Exception as e: return "DEAD",type(e).__name__

def proxy_string(x):
    if x["type"]=="MTProto": return "tg://proxy?"+urlencode({"server":x["host"],"port":x["port"],"secret":x["secret"]})
    return f"{'socks5' if x['type']=='SOCKS5' else 'http'}://{x['host']}:{x['port']}"

async def check_all(db):
    items=list(db["proxies"].values())
    if not items: console.print("[yellow]База пуста. Сначала выполни поиск.[/]"); return
    sem=asyncio.Semaphore(70)
    async def run(x):
        async with sem:
            x["status"],x["check_detail"]=await probe(x); x["checked_at"]=now(); return x
    with Progress(SpinnerColumn(),TextColumn("{task.description}"),BarColumn(),TextColumn("{task.completed}/{task.total}"),console=console) as p:
        task=p.add_task("[cyan]Проверяю с текущего подключения...",total=len(items))
        for f in asyncio.as_completed([run(x) for x in items]): await f; p.advance(task)
    save_db(db)
    good=[x for x in items if x.get("status")=="WORKING"]
    WORKING_FILE.write_text("\\n".join(proxy_string(x) for x in good)+("\\n" if good else ""),"utf-8")
    console.print(f"[green]Рабочие: {len(good)}[/]  [yellow]На ручную проверку: {sum(x.get('status')=='REVIEW' for x in items)}[/]  [red]Мёртвые: {sum(x.get('status')=='DEAD' for x in items)}[/]")

def show_results(db):
    items=sorted((x for x in db["proxies"].values() if x.get("status") in ("WORKING","REVIEW")),key=lambda x:(x.get("status")!="WORKING",x["type"],x["host"]))
    t=Table(title="ПРОКСИ ДЛЯ РУЧНОГО ОТБОРА",expand=True)
    for name in ("#","STATUS","TYPE","ADDRESS","SOURCE"): t.add_column(name,overflow="ellipsis")
    for i,x in enumerate(items,1):
        color="green" if x["status"]=="WORKING" else "yellow"
        t.add_row(str(i),f"[{color}]{x['status']}[/]",x["type"],f"{x['host']}:{x['port']}",x.get("source",""))
    console.print(t); return items

def copy_results(items):
    good=[x for x in items if x.get("status")=="WORKING"]
    if not good: console.print("[yellow]Нет подтверждённых рабочих прокси.[/]"); return
    payload="\\n".join(proxy_string(x) for x in good)
    try:
        import pyperclip; pyperclip.copy(payload); console.print(f"[green]Скопировано в буфер: {len(good)}[/]")
    except Exception:
        WORKING_FILE.write_text(payload+"\\n","utf-8"); console.print(f"[yellow]Буфер недоступен; сохранено в {WORKING_FILE}[/]")

async def remote_version():
    url=f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/version.json"
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=True) as c:
            r=await c.get(url)
            if r.status_code==200:
                d=r.json(); return d.get("version"),d.get("download_url") or f"https://github.com/{OWNER}/{REPO}/archive/refs/heads/main.zip"
    except Exception: pass
    return None,None

def install_update(url):
    if not url: return
    try:
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/"update.zip"
            with httpx.stream("GET",url,timeout=35,follow_redirects=True) as r:
                r.raise_for_status()
                with archive.open("wb") as f:
                    for chunk in r.iter_bytes(): f.write(chunk)
            with zipfile.ZipFile(archive) as z:
                prefix=z.namelist()[0].split("/")[0]+"/"
                for name in z.namelist():
                    rel=name.removeprefix(prefix)
                    if rel in {"main.py","requirements.txt","README.md","version.json","install.bat","start.bat"}:
                        (ROOT/rel).write_bytes(z.read(name))
        console.print("[green]Обновление установлено. Перезапусти программу.[/]")
    except Exception as e: console.print(f"[red]Не удалось обновить: {e}[/]")

def check_version():
    latest,url=asyncio.run(remote_version())
    if not latest: console.print(f"[yellow]Не удалось проверить обновления. Текущая версия v{VERSION}.[/]")
    elif latest==VERSION: console.print(f"[green]У вас последняя версия v{VERSION}.[/]")
    else:
        console.print(f"[bold yellow]Вышла новая версия v{latest}![/]")
        if Confirm.ask("Скачать и установить?",default=False): install_update(url)

def banner():
    console.clear()
    console.print(Panel(Text(APP,justify="center",style="bold bright_cyan"),subtitle="GitHub repository scanner · Telegram proxy checker",border_style="bright_cyan"))
    console.print("[dim]by zmlsag[/]\\n")

def main():
    DATA.mkdir(exist_ok=True)
    while True:
        banner()
        console.print("[bold cyan]1.[/] Найти рабочие прокси [dim](найти репозитории + проверить)[/]")
        console.print("[bold cyan]2.[/] Обновить базу прокси [dim](повторно просканировать известные репозитории)[/]")
        console.print("[bold cyan]3.[/] Проверить обновления программы")
        console.print("[bold cyan]4.[/] Показать результаты / скопировать рабочие")
        console.print("[bold cyan]0.[/] Выход\\n")
        choice=Prompt.ask("Выбери действие",choices=["1","2","3","4","0"],default="1")
        if choice=="0": break
        db=load_db()
        try:
            if choice=="1":
                asyncio.run(collect(db,False)); asyncio.run(check_all(db))
                items=show_results(db)
                if items and Confirm.ask("Скопировать все подтверждённые рабочие прокси?",default=True): copy_results(items)
            elif choice=="2": asyncio.run(collect(db,True)); asyncio.run(check_all(db))
            elif choice=="3": check_version()
            elif choice=="4":
                items=show_results(db)
                if items and Confirm.ask("Скопировать все подтверждённые рабочие прокси?",default=True): copy_results(items)
        except KeyboardInterrupt: console.print("\\n[yellow]Остановлено. Сохранённые данные не потеряны.[/]")
        except Exception as e: console.print(f"[red]Ошибка: {e}[/]")
        Prompt.ask("\\nEnter — назад в меню",default="")
    console.print("[dim]by zmlsag[/]")
if __name__=="__main__": main()
