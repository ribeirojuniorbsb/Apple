"""Monitor de retirada na loja (Apple Store NYC) com alerta via ntfy."""
import json
import os
import urllib.parse
import urllib.request

PARTS = {
    "MK1E4LL/A": "iPhone Duo 256GB Star White",
    "MK1F4LL/A": "iPhone Duo 256GB Night Sky",
    "MJW54LL/A": "iPhone 18 Pro Max 256GB Silver",
}

ZIP = "10001"          # Midtown: cobre as lojas de Manhattan
MAX_MILES = 10         # ignora lojas mais distantes (ex.: New Jersey)

URL = "https://www.apple.com/shop/retail/pickup-message"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.apple.com/shop/bag",
}
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
MANUAL_RUN = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"


def notify(title, msg, priority="high"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": priority,
                 "Click": "https://www.apple.com/shop/bag"},
    )
    urllib.request.urlopen(req, timeout=10)


def check():
    params = {"pl": "true", "mts.0": "regular", "location": ZIP}
    for i, p in enumerate(PARTS):
        params[f"parts.{i}"] = p
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)

    hits, n_stores = [], 0
    for s in data["body"]["stores"]:
        if float(s.get("storedistance", 0)) > MAX_MILES:
            continue
        n_stores += 1
        for part, info in s.get("partsAvailability", {}).items():
            if info.get("pickupDisplay") == "available":
                hits.append(f"• {PARTS.get(part, part)}\n  {s['storeName']} ({s.get('storeDistanceWithUnit', '')})")
    return hits, n_stores


def main():
    try:
        hits, n_stores = check()
    except Exception as e:  # 541/403/429 = bloqueio temporário, não "sem estoque"
        print(f"Falha na consulta: {e}")
        if MANUAL_RUN:
            notify("Apple monitor: erro", f"Falha na consulta: {e}", "default")
        return

    if hits:
        notify("🍏 Disponível para retirada!", "\n".join(hits))
        print("\n".join(hits))
    else:
        print(f"Nada disponível em {n_stores} lojas.")
        if MANUAL_RUN:
            notify("Apple monitor: teste OK", f"Nada disponível em {n_stores} lojas.", "default")


if __name__ == "__main__":
    main()
