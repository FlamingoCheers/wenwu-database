import glob
import json

JADE = ("jade", "nephrite", "serpentine", "turquoise")
BRONZE = ("bronze", "brass", "copper", "metal", "silver", "gold", "gilt")
fixed_cat = fixed_img = 0
for f in glob.glob(r"E:\codingProject\52-文物数据库\data\relics\SMI-*.json"):
    d = json.load(open(f, encoding="utf-8"))
    ch = False
    imgs = d.get("images")
    if imgs and isinstance(imgs[0], str):
        d["images"] = [{"url": u} for u in imgs]
        ch = fixed_img == fixed_img
        fixed_img += 1
    if d.get("category") == "杂":
        med = (d.get("dimensions") or "") + " " + (d.get("name_en") or "") + " " + (d.get("summary") or "")
        low = med.lower()
        if any(k in low for k in JADE):
            d["category"] = "玉器"
        elif any(k in low for k in BRONZE):
            d["category"] = "青铜器"
        else:
            d["category"] = "杂器"
        fixed_cat += 1
        ch = True
    if ch:
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fixed_img=%d fixed_cat=%d" % (fixed_img, fixed_cat))
