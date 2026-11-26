#!/usr/bin/env python3
"""Fetch upstream update sources and create deterministic GitHub issue alerts."""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, sys, urllib.error, urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "watch-config.json").read_text())
UA = "unraid-p2p-kernel-upstream-watch/1.0"

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self, data): self.parts.append(data)

def request(url, token=None):
    headers={"User-Agent":UA,"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r: return r.read()

def version_tuple(s):
    m=re.search(r'(?<!\d)(\d+(?:\.\d+){1,3})(?!\d)',s or '')
    return tuple(map(int,m.group(1).split('.'))) if m else ()

def item(source, ident, title, url, summary="", status="released"):
    return {"source":source,"id":str(ident),"title":html.unescape(str(title))[:300],"url":str(url),"summary":html.unescape(str(summary))[:900],"status":status}

def normalize(source, raw):
    kind=source["kind"]; data=json.loads(raw) if kind in ("kernel_releases","github_commit","github_releases") else None
    out=[]
    if kind=="github_commit":
        for x in data:
            c=x.get("commit",{}); msg=c.get("message","").splitlines()[0]
            category=source.get("category","")
            status="stable-tree commit; backport context, not mainline" if category.startswith("linux-stable-") else "mainline commit; not a stable backport unless separately confirmed"
            out.append(item(source["id"],x.get("sha"),msg,x.get("html_url",""),c.get("message",""),status))
    elif kind=="github_releases":
        baseline=CONFIG["baseline"].get("nvidia_open_modules") if source["id"]=="nvidia-open-modules" else None
        for x in data:
            if x.get("draft") or x.get("prerelease"): continue
            tag=x.get("tag_name","")
            if baseline and version_tuple(tag) <= version_tuple(baseline): continue
            out.append(item(source["id"],tag,x.get("name") or tag,x.get("html_url",""),x.get("body", "")))
    elif kind=="kernel_releases":
        rows=data if isinstance(data,list) else data.get("releases",[])
        for x in rows:
            ver=x.get("version","")
            base=CONFIG["baseline"]["linux_stable_kernel"]
            # Only flag a newer version in the configured Unraid kernel series.
            if version_tuple(ver) > version_tuple(base) and ver.split(".",1)[0]==base.split(".",1)[0] and ver.split(".",1)[1].split(".",1)[0]==base.split(".",1)[1].split(".",1)[0]:
                out.append(item(source["id"],ver,"Linux LTS release "+ver,x.get("source") or x.get("gitweb") or "https://www.kernel.org/releases.html","Newer release in configured 6.18 baseline series"))
    elif kind=="unraid_notes":
        parser=Text(); parser.feed(raw.decode("utf-8","replace")); text=" ".join(parser.parts)
        # Discover version links and their release-note pages, retaining stable/preview lanes.
        matches=re.findall(r'href=["\']([^"\']*/(?:unraid-os/)?release-notes/([^/"\']+)/?)["\'][^>]*>(.*?)</a>',raw.decode("utf-8","replace"),re.I|re.S)
        for href,ver,label in matches:
            if version_tuple(ver) <= version_tuple(source.get("baseline","0")): continue
            channel="preview" if re.search(r'(rc|beta|next|preview)',ver,re.I) else "stable"
            if channel!=source.get("channel"): continue
            url=href if href.startswith("http") else "https://docs.unraid.net"+href
            kernel=""
            try:
                detail=request(url).decode("utf-8","replace")
                km=re.search(r'\b(\d+\.\d+\.\d+)-Unraid\b',detail)
                kernel=km.group(1) if km else ""
            except Exception: pass
            out.append(item(source["id"],ver,f"Unraid {channel} {ver}"+(f" (Linux {kernel}-Unraid)" if kernel else ""),url,"Release notes; shipped kernel version extracted from the linked release notes" if kernel else "Release notes; shipped kernel version not found", "preview" if channel=="preview" else "released"))
    elif kind=="html_page":
        parser=Text(); parser.feed(raw.decode("utf-8","replace")); text=" ".join(parser.parts)
        versions=sorted(set(re.findall(r'\b\d{4}\.\d{2,3}\.\d{2,3}\b',text)),key=version_tuple)
        if versions:
            ver=versions[-1]; out.append(item(source["id"],ver,"Intel GPU software release notes "+ver,source["url"],"Latest version listed on Intel GPU release notes"))
    return out

def relevant(x, source):
    if source["kind"] in ("kernel_releases","github_releases","unraid_notes","html_page"): return True
    text=(x["title"]+" "+x["summary"]).lower()
    terms=("p2pdma","peer-to-peer dma","dma-buf","dmabuf","drm/xe","xe:","i915","amdgpu","gpu","nvidia")
    # Mainline commit feeds are candidates; only accept explicitly targeted upstream paths.
    category=source.get("category","")
    if category.startswith("linux-drm-"):
        prefix={"linux-drm-xe":"drm/xe","linux-drm-i915":"drm/i915","linux-drm-amdgpu":"drm/amdgpu"}[category]
        if not (text.startswith(prefix+":") or text.startswith(prefix+"/")): return False
    elif category.endswith("p2pdma") and not ("p2pdma" in text or "peer-to-peer dma" in text): return False
    elif category=="linux-dmabuf" and not ("dma-buf" in text or "dmabuf" in text): return False
    return any(t in text for t in terms)

def fetch_all(fixtures=None):
    rows=[]; failures=[]
    fixtures=json.loads(Path(fixtures).read_text()) if fixtures else None
    for src in CONFIG["sources"]:
        try:
            raw=fixtures[src["id"]].encode() if fixtures and src["id"] in fixtures else request(src["url"])
            candidates=normalize(src,raw)
            rows.extend((x,src) for x in candidates if relevant(x,src))
        except Exception as e: failures.append({"source":src["id"],"error":str(e)[:250]})
    return rows,failures

def key(x): return hashlib.sha256((x["source"]+"\0"+x["id"]).encode()).hexdigest()[:20]
def digest(items):
    items=sorted(items,key=lambda x:(x["title"],x["id"]))
    source_id=items[0]["source"]
    digest_key=hashlib.sha256((source_id+"\0"+"\0".join(sorted(x["id"] for x in items))).encode()).hexdigest()[:20]
    lines=["- {} — {} [{}]".format(x["title"],x["url"],x["status"]) for x in items]
    markers="\n".join("<!-- upstream-item:{} -->".format(key(x)) for x in items)
    return {"key":digest_key,"source":source_id,"title":"{} upstream update(s) from {}".format(len(items),source_id),"url":items[0]["url"],"summary":"\n".join(lines),"status":"digest; {} items".format(len(items)),"item_count":len(items),"item_markers":markers}

def unseen_items(items, issue_bodies):
    """Exclude items already represented in any prior alert, including legacy digests."""
    known_keys=set()
    bodies="\n".join(issue_bodies)
    known_keys.update(re.findall(r'<!-- upstream-item:([0-9a-f]{20}) -->',bodies))
    # Older digests predate item markers; their rendered rows include the upstream URL.
    return [x for x in items if key(x) not in known_keys and x["url"] not in bodies]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--dry-run",action="store_true"); p.add_argument("--fixtures"); p.add_argument("--output"); a=p.parse_args()
    rows,failures=fetch_all(a.fixtures)
    unique={key(x):x for x,s in rows}
    groups={}
    for x in unique.values(): groups.setdefault(x["source"],[]).append(x)
    reports=[]
    for source_id,items in sorted(groups.items()):
        reports.append(digest(items))
    result={"alerts":reports,"failures":failures,"successful_feeds":len(CONFIG["sources"])-len(failures),"total_feeds":len(CONFIG["sources"]),"dry_run":a.dry_run}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: Path(a.output).write_text(text+"\n")
    print(text)
    if not a.dry_run and reports:
        token=os.environ.get("GITHUB_TOKEN"); repo=os.environ.get("GITHUB_REPOSITORY")
        if not token or not repo: print("issue creation requires GITHUB_TOKEN and GITHUB_REPOSITORY",file=sys.stderr); return 2
        # Only use the API for an issue body assembled from escaped upstream text. Search keys in existing issues.
        existing=json.loads(request("https://api.github.com/repos/"+repo+"/issues?state=all&per_page=100",token))
        known=set(re.findall(r'<!-- upstream-watch:([0-9a-f]{20}) -->',"\n".join(i.get("body","") for i in existing)))
        issue_bodies=[i.get("body","") for i in existing]
        unseen=[]
        for source_id,items in sorted(groups.items()):
            pending=unseen_items(items,issue_bodies)
            if pending: unseen.append(digest(pending))
        for r in unseen:
            if r["key"] in known: continue
            body=(f'<!-- upstream-watch:{r["key"]} -->\n{r["item_markers"]}\nSource: `{r["source"]}` · status: {r["status"]}\n\n'
                  f'[{html.escape(r["title"])}]({r["url"]})\n\n{html.escape(r["summary"])}\n\n'
                  'Review upstream status and compatibility with this repository baseline before changing build inputs. '
                  'This alert is informational; no build, branch, release, or plugin action is automated.')
            payload=json.dumps({"title":("Upstream update: "+r["title"])[:240],"body":body,"labels":["upstream-update"]}).encode()
            req=urllib.request.Request("https://api.github.com/repos/"+repo+"/issues",data=payload,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":UA},method="POST")
            with urllib.request.urlopen(req,timeout=30) as resp: print("created issue",json.loads(resp.read()).get("html_url"))
    if failures:
        print(f"partial scan: {len(failures)} of {len(CONFIG['sources'])} feeds failed; see failures above",file=sys.stderr)
        return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
