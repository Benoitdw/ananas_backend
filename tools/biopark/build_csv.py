"""biopark_raw.csv -> api/data/biopark.csv, au format attendu par ananas.seed."""
import csv, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
OUT = os.path.join(DATA, "biopark.csv")

# Deja presentes dans partners.csv / biotech-belgique.csv sous un autre libelle.
# La cle est le nom biopark, la valeur le nom deja en base (pour la trace).
ALIASES = {
    "Forem": "Le Forem",
    "Wallonie Entreprendre Life Sciences": "Wallonie Entreprendre",
    "Thermo Fisher Scientific": "Thermo Fisher Scientific – Henogen",
}
# Le vocabulaire de type doit rester celui des facettes existantes.
TYPE_FIXES = {
    "Public/non-profit organisation": "Public/Non-profit organisation",
    "Public/non-profit organization": "Public/Non-profit organisation",
}
# Adresses que la fiche BioPark ecrit dans un format que split_address ne sait
# pas lire (ponctuation exotique, ville absente): corrigees a la main.
ADDRESS_FIXES = {
    "CHU Tivoli": ("Avenue Max Buset 34", "7100", "La Louvière", "Belgium"),
    "Elkedonia Belgium": ("32 Allée de la Robertsau", "67000", "Strasbourg", "France"),
    "REDSYSTEM": ("Rue du Progrès 15", "7500", "Tournai", "Belgium"),
    "USIL Therapeutics": ("Route d'Esch 15", "1470", "Luxembourg", "Luxembourg"),
}
COUNTRIES = {"belgium", "belgique", "france", "netherlands", "germany", "luxembourg",
             "switzerland", "spain", "italy", "united kingdom", "usa", "united states"}

FIELDS = ["name", "type", "core_business", "other_tags", "baseline", "description",
          "street", "city", "postal_code", "country", "address", "website", "email",
          "phone", "linkedin", "logo", "source", "url", "lat", "lon", "geo_precision"]


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"\b(sa|nv|bv|srl|sprl|bvba|group|belgium|belgique|holdings?)\b", "", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def split_address(addr):
    """'16 Rue Clement Ader, 6041 Charleroi, Belgium' -> (rue, cp, ville, pays)."""
    if not addr:
        return "", "", "", ""
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    country = ""
    if parts and parts[-1].lower() in COUNTRIES:
        country = parts.pop().title()
    postal = city = ""
    for i in range(len(parts) - 1, -1, -1):
        # "6041 Charleroi" / "B-1050 Bruxelles" / "B7100 La Louviere"
        m = re.match(r"^(?:[A-Z]{1,2}-?)?(\d{4,5})\s+(.+)$", parts[i])
        if m:
            postal, city = m.group(1), m.group(2).strip()
            parts.pop(i)
            break
        # code postal et ville separes par une virgule: "..., 5031, Namur, ..."
        if re.fullmatch(r"(?:[A-Z]{1,2}-?)?\d{4,5}", parts[i]) and i + 1 < len(parts):
            postal = re.sub(r"\D", "", parts[i])
            city = parts[i + 1]
            del parts[i:i + 2]
            break
    if not country and postal:
        country = "Belgium" if len(postal) == 4 else ""
    return ", ".join(parts), postal, city, country


def main():
    existing = {}
    for fname in ("partners.csv", "biotech-belgique.csv"):
        for row in csv.DictReader(open(os.path.join(DATA, fname), encoding="utf-8")):
            existing.setdefault(norm(row["name"]), row["name"])

    rows, skipped = [], []
    for r in csv.DictReader(open(os.path.join(HERE, "biopark_raw.csv"), encoding="utf-8")):
        name = r["name"].strip()
        already = existing.get(norm(name)) or ALIASES.get(name)
        if already:
            skipped.append((name, already))
            continue

        street, postal, city, country = ADDRESS_FIXES.get(name) or split_address(r["address"])

        # Quelques fiches n'ont pas de texte de presentation: le gabarit y laisse
        # l'encart "HERE FOR YOU / votre contact", qui n'est pas une description.
        description = r["description"].strip()
        phone = ""
        if description.upper().startswith("HERE FOR YOU"):
            m = re.search(r"(\+\d[\d ().-]{7,})", description)
            phone = m.group(1).strip() if m else ""
            description = ""
        tags = []
        if r["category"]:
            tags.append("BioPark " + ("membre" if r["category"] == "member" else "partenaire"))
        if r["size"]:
            tags.append("Taille " + r["size"])
        for part in r["other_attrs"].split("; "):
            if part.strip():
                tags.append(part.split(": ", 1)[-1].strip())

        rows.append({
            "name": name,
            "type": TYPE_FIXES.get(r["type"].strip(), r["type"].strip()),
            "core_business": r["core_business"].strip(),
            "other_tags": ", ".join(tags),
            "baseline": "",
            "description": description,
            "street": street, "city": city, "postal_code": postal, "country": country,
            "address": r["address"].strip(),
            "website": r["website"].strip(),
            "email": "", "phone": phone, "linkedin": "",
            "logo": r["logo"].strip(),
            "source": "biopark",
            "url": r["url"],
            "lat": "", "lon": "", "geo_precision": "",
        })

    # Le geocodage coute une seconde par ligne: on le recupere de la version
    # precedente du fichier tant que l'adresse resolue n'a pas change.
    previous = {}
    if os.path.exists(OUT):
        for old in csv.DictReader(open(OUT, encoding="utf-8")):
            key = (old["street"], old["postal_code"], old["city"], old["country"])
            if old.get("lat"):
                previous[(old["name"], key)] = (old["lat"], old["lon"], old["geo_precision"])
    kept = 0
    for row in rows:
        key = (row["street"], row["postal_code"], row["city"], row["country"])
        hit = previous.get((row["name"], key))
        if hit:
            row["lat"], row["lon"], row["geo_precision"] = hit
            kept += 1
    print(f"{kept} geocodages repris de la version precedente")

    rows.sort(key=lambda x: x["name"].lower())
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} entreprises ecrites dans {OUT}")
    print(f"{len(skipped)} doublons ignores:")
    for a, b in sorted(skipped):
        print(f"  - {a}" + (f"  (deja en base sous '{b}')" if a != b else ""))
    print("sans adresse:", sum(1 for r in rows if not r["address"]))
    print("sans site web:", sum(1 for r in rows if not r["website"]))



if __name__ == "__main__":
    main()
