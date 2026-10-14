#!/usr/bin/env python3
"""Tell IndexNow-enabled search engines (Bing, Yandex, Naver, Seznam, Yep; Google does not take part) which
pages changed. Run by _scripts/publish.sh after `quarto publish`; can also be run by hand from the repo root.

  _scripts/indexnow.py --previous OLD_SITEMAP   # pages whose <lastmod> differs from the previously published sitemap
  _scripts indexnow.py --all                    # every URL in _site/sitemap.xml
  _scripts/indexnow.py URL [URL ...]            # just these
  add --dry-run to print the URLs without submitting, --wait to poll until the key file is live first.

The key is the 32-hex-character .txt file at the repo root (its content equals its name), served from the site
root via the `resources` list in _quarto.yml. IndexNow fetches it to confirm the submission came from the site owner.
HTTP goes through curl (the python.org Python on this Mac has no CA bundle, so urllib cannot verify certificates).
"""
import argparse, glob, json, os, re, subprocess, sys, time

HOST = "slamdunk.bet"
ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def key():
    files = [f for f in glob.glob(os.path.join(ROOT, "*.txt")) if re.fullmatch(r"[0-9a-f]{32}\.txt", os.path.basename(f))]
    if len(files) != 1:
        sys.exit("expected exactly one 32-hex-character .txt key file at the repo root, found %d" % len(files))
    name = os.path.basename(files[0])[:-4]
    with open(files[0]) as fh:
        if fh.read().strip() != name:
            sys.exit("key file %s does not contain its own name" % files[0])
    return name


def parse_sitemap(path):
    """{url: lastmod} from a sitemap.xml; empty when the file is missing or empty."""
    if not path or not os.path.exists(path):
        return {}
    text = open(path, encoding="utf-8").read()
    out = {}
    for block in re.findall(r"<url>(.*?)</url>", text, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        mod = re.search(r"<lastmod>(.*?)</lastmod>", block)
        if loc:
            out[loc.group(1).strip()] = mod.group(1).strip() if mod else ""
    return out


def changed(previous, current):
    return [u for u, m in current.items() if previous.get(u) != m]


def curl(args, timeout):
    """(status, body) via curl; status is 0 when the request itself failed, with curl's error in body."""
    p = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-o", "-", "-w", "\n%{http_code}"] + args,
                       capture_output=True, text=True)
    if p.returncode != 0:
        return 0, p.stderr.strip()
    body, _, status = p.stdout.rpartition("\n")
    return int(status or 0), body


def wait_for_key(k, timeout=600):
    url = "https://%s/%s.txt" % (HOST, k)
    deadline = time.time() + timeout
    last = ""
    while True:
        status, body = curl([url], 15)
        if status == 200 and body.strip() == k:
            return True
        last = "HTTP %d" % status if status else body
        if time.time() >= deadline:
            print("indexnow: last attempt: %s" % last, file=sys.stderr)
            return False
        time.sleep(15)


def submit(k, urls):
    body = json.dumps({"host": HOST, "key": k, "keyLocation": "https://%s/%s.txt" % (HOST, k), "urlList": urls})
    return curl(["-X", "POST", "-H", "Content-Type: application/json; charset=utf-8", "--data-binary", body, ENDPOINT], 30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--previous", help="previously published sitemap.xml to diff against")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait", action="store_true", help="poll until the key file is live on the site before submitting")
    a = ap.parse_args()

    k = key()
    current = parse_sitemap(os.path.join(ROOT, "_site", "sitemap.xml"))
    if a.urls:
        urls = a.urls
    elif a.all:
        urls = list(current)
    elif a.previous is not None:
        urls = changed(parse_sitemap(a.previous), current)
    else:
        ap.error("give URLs, --all, or --previous OLD_SITEMAP")

    if not urls:
        print("indexnow: nothing changed, nothing submitted")
        return
    print("indexnow: %d URL(s)" % len(urls))
    for u in urls:
        print("  " + u)
    if a.dry_run:
        return
    if a.wait and not wait_for_key(k):
        sys.exit("indexnow: key file is not live at https://%s/%s.txt after waiting; not submitting" % (HOST, k))
    status, text = submit(k, urls)
    ok = status in (200, 202)
    print("indexnow: HTTP %d %s" % (status, {200: "OK", 202: "accepted, key validation pending"}.get(status, text.strip())))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
