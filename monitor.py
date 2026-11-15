"""Monitor de retirada na loja (Apple Store NYC) com alerta via ntfy.

Só envia push quando um iPhone Duo estiver disponível; nesse caso,
inclui também a disponibilidade do iPhone 18 Pro Max.
"""
import json
import os
import urllib.parse
import urllib.request

PARTS = {
    "MK1E4LL/A": "iPhone Duo 256GB Star White",
    "MK1F4LL/A": "iPhone Duo 256GB Night Sky",
    "MJW54LL/A": "iPhone 18 Pro Max 256GB Silver",
}
PRIORITY = {"MK1E4LL/A", "MK1F4LL/A"}   # só dispara push se algum destes estiver disponível

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
                 "Actions": "view, Abrir bag, https://www.apple.com/shop/bag"},
    )
    urllib.request.urlopen(req, timeout=10)


def check():
    params = {"pl": "true", "mts.0": "regular", "location": ZIP}
    for i, p in enumerate(PARTS):
        params[f"parts.{i}"] = p
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)

    hits, n_stores = [], 0   # lista de (part, texto)
    for s in data["body"]["stores"]:
        if float(s.get("storedistance", 0)) > MAX_MILES:
            continue
        n_stores += 1
        for part, info in s.get("partsAvailability", {}).items():
            if info.get("pickupDisplay") == "available":
                hits.append((part, f"• {PARTS.get(part, part)}\n  {s['storeName']} "
                                   f"({s.get('storeDistanceWithUnit', '')})"))
    return hits, n_stores


def main():
    try:
        hits, n_stores = check()
    except Exception as e:  # 541/403/429 = bloqueio temporário, não "sem estoque"
        print(f"Falha na consulta: {e}")
        if MANUAL_RUN:
            notify("Apple monitor: erro", f"Falha na consulta: {e}", "default")
        return

    duo = [t for p, t in hits if p in PRIORITY]
    others = [t for p, t in hits if p not in PRIORITY]

    if duo:
        msg = "📱 iPhone Duo:\n" + "\n".join(duo)
        if others:
            msg += "\n\n➕ Também disponível:\n" + "\n".join(others)
        notify("🍏 iPhone Duo disponível!", msg, "urgent")
        print(msg)
    else:
        status = f"{n_stores} lojas consultadas: nenhuma com iPhone Duo."
        if others:
            status += "\n\n➕ Outros com estoque:\n" + "\n".join(others)
        print(status)
        if MANUAL_RUN:
            notify("Apple monitor: teste OK", status, "default")


if __name__ == "__main__":
    main()
