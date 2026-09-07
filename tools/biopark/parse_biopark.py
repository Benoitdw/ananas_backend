"""Extrait biopark_raw.csv des fiches telechargees par fetch_biopark.py.

Une fiche BioPark est une page produit Odoo. On y lit:

  - le titre (``h1[itemprop=name]``) et le logo (``span[itemprop=image]``);
  - le bloc libre ``div.oe_structure`` de ``#product_details``, qui contient
    l'adresse (apres l'epingle ``fa-map-marker``), le bouton "VISIT THEIR
    WEBSITE" et le texte de presentation — dans cet ordre, sans balisage propre,
    d'ou le decoupage a la main;
  - les attributs de variante Odoo, lisibles sur les ``<input data-*>``: selon
    la categorie ils s'appellent "Partner type" ou "Member type", plus
    "Core Business", "Size", "Technology" et "Therapeutic Area".

    python3 parse_biopark.py
"""
import csv, html, os, re
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://www.biopark.be"


class Grab(HTMLParser):
    """Recupere le contenu brut du premier div dont `attr` contient `value`."""

    def __init__(self, attr, value, exact=False):
        super().__init__(convert_charrefs=False)
        self.attr, self.value, self.exact = attr, value, exact
        self.depth, self.done, self.out = None, False, []

    def _open(self):
        return self.depth is not None and not self.done

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if self.depth is None:
            got = dict(attrs).get(self.attr) or ""
            if tag == "div" and (got == self.value if self.exact else self.value in got):
                self.depth = 0
            return
        if tag == "div":
            self.depth += 1
        self.out.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self._open():
            self.out.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if not self._open():
            return
        if tag == "div":
            if self.depth == 0:
                self.done = True  # le div cible vient d'etre referme
                return
            self.depth -= 1
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self._open():
            self.out.append(data)

    def handle_entityref(self, name):
        if self._open():
            self.out.append(f"&{name};")

    def handle_charref(self, name):
        if self._open():
            self.out.append(f"&#{name};")

    @property
    def html(self):
        return "".join(self.out)


def grab(page, attr, value, exact=False):
    p = Grab(attr, value, exact)
    p.feed(page)
    return p.html


def text(fragment):
    fragment = re.sub(r"<(script|style)\b.*?</\1>", "", fragment, flags=re.S)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"</(p|div|li|h\d)>", "\n", fragment)
    out = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")
    out = re.sub(r"[ \t]+", " ", out)
    return "\n".join(l.strip() for l in out.split("\n")).strip()


def parse(slug, page):
    d = {"slug_biopark": slug, "url": f"{BASE}/community/{slug}"}
    m = re.search(r'<h1 itemprop="name">(.*?)</h1>', page, re.S)
    d["name"] = text(m.group(1)) if m else ""
    m = re.search(r'itemprop="image"[^>]*>(.*?)</span>', page, re.S)
    d["logo"] = html.unescape(m.group(1).strip()).split("?")[0] if m else ""

    details = grab(page, "id", "product_details", exact=True)
    block = grab(details, "class", "oe_structure", exact=True)
    d["website"] = ""
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S):
        if "VISIT THEIR WEBSITE" in text(label).upper():
            d["website"] = html.unescape(href.strip())
            break
    addr = ""
    m = re.search(r"fa-map-marker.*?</span>(.*?)(?:<br|<a\b|</span>|</p>|$)", block, re.S)
    if m:
        addr = " ".join(text(m.group(1)).split())
    d["address"] = addr

    desc = re.sub(r"<a\b.*?</a>", "", block, flags=re.S)
    desc = re.sub(r".*?fa-map-marker.*?</span>", "", desc, flags=re.S)
    desc = text(desc)
    if addr:
        desc = desc.replace(addr, "")
    d["description"] = " ".join(desc.split())

    attrs = {}
    for m in re.finditer(r"<input\b[^>]*>", page):
        tag = m.group(0)
        k = re.search(r'data-attribute_name="([^"]*)"', tag)
        v = re.search(r'data-value_name="([^"]*)"', tag)
        if k and v:
            attrs.setdefault(html.unescape(k.group(1)).strip(),
                             html.unescape(v.group(1)).strip())
    d["type"] = attrs.pop("Partner type", "") or attrs.pop("Member type", "")
    d["core_business"] = attrs.pop("Core Business", "")
    d["size"] = attrs.pop("Size", "")
    d["other_attrs"] = "; ".join(f"{k}: {v}" for k, v in sorted(attrs.items()))
    return d


def main():
    entries = [l.rstrip("\n").split("\t")
               for l in open(os.path.join(HERE, "biopark_list.tsv"), encoding="utf-8") if l.strip()]
    cats = {}
    for cat, fname in (("member", "cat_members-1.txt"), ("partner", "cat_partners-24.txt")):
        for line in open(os.path.join(HERE, fname), encoding="utf-8"):
            cats[line.strip().split("?")[0]] = cat

    rows = []
    for slug, name in entries:
        page = open(os.path.join(HERE, "pages", slug + ".html"), encoding="utf-8").read()
        row = parse(slug, page)
        row["category"] = cats.get(slug, "")
        if not row["name"]:
            row["name"] = html.unescape(name)
        rows.append(row)

    fields = ["slug_biopark", "name", "category", "type", "core_business", "size",
              "address", "website", "logo", "description", "url", "other_attrs"]
    with open(os.path.join(HERE, "biopark_raw.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    for k in fields:
        print(f"  {k:14} rempli sur {sum(1 for r in rows if r[k].strip()):3}/{len(rows)}")


if __name__ == "__main__":
    main()
