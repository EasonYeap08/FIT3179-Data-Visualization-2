"""Turn the raw downloads in ../raw into the small files in data/ used by the charts.

Raw sources (downloaded 12 Oct 2026, not committed because of size):
  raw/er/*.csv          Energy Rating registration data, data.gov.au (labelled products)
  raw/comtrade/*.json   UN Comtrade public API, Australian imports by HS6 code
  raw/abs/HSI_M.csv     ABS Monthly Household Spending Indicator (category 30)
  raw/abs/erp.csv       ABS Quarterly Estimated Resident Population
  raw/amazon/*.jsonl.gz Amazon Reviews 2023, Appliances (McAuley Lab, UCSD)
  raw/geo/*             ABS ASGS 2021 state boundaries (geo.abs.gov.au) + world-110m;
                        the state map was simplified separately with mapshaper (see SOURCE_CHANGES.md)

Run:  python3 scripts/prepare_data.py ../raw
"""
import collections
import gzip
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "../raw")
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- Comtrade
HS = {
    "850811": "Vacuum cleaners",
    "851671": "Coffee & tea makers",
    "851660": "Ovens, cookers & air fryers",
    "850940": "Blenders & food mixers",
    "851650": "Microwave ovens",
    "841810": "Fridge-freezers",
    "841821": "Fridges",
    "845011": "Washing machines",
    "845121": "Clothes dryers",
    "842211": "Dishwashers",
    "841510": "Split-system air conditioners",
    "852872": "Televisions",
}
SMALL = {"850811", "851671", "851660", "850940", "851650"}
# UN M49 codes that differ from the ISO numeric ids in world-110m
M49_TO_ISO = {842: 840, 251: 250, 699: 356, 757: 756}


def comtrade_rows(path):
    return json.load(open(path))["data"]


trend = []
for y in range(2015, 2026):
    files = [RAW / f"comtrade/f{y}.json"]
    files.append(RAW / (f"comtrade/w{y}.json" if y <= 2023 else f"comtrade/p{y}.json"))
    for f in files:
        for r in comtrade_rows(f):
            if r["partnerCode"] == 0:
                trend.append({
                    "year": y, "hs": r["cmdCode"], "category": HS[r["cmdCode"]],
                    "group": "Small appliances" if r["cmdCode"] in SMALL else "Large appliances & electronics",
                    "units": round(r["qty"]) if r["qty"] else None,  # 0 means quantity not reported
                    "value_usd_m": round(r["primaryValue"] / 1e6, 2),
                })
trend = pd.DataFrame(trend)
trend["units"] = trend.units.astype("Int64")
trend.sort_values(["category", "year"]).to_csv(OUT / "imports_trend.csv", index=False)

cent = {c["id"]: c for c in json.load(open(RAW / "geo/centroids.json"))}
flows = []
for r in comtrade_rows(RAW / "comtrade/p2025.json") + comtrade_rows(RAW / "comtrade/f2025.json"):
    code = M49_TO_ISO.get(r["partnerCode"], r["partnerCode"])
    if code not in cent or code == 36:
        continue  # skips World, "Areas nes", "Other Asia nes" and Australia itself
    flows.append({
        "iso": code, "country": r["partnerDesc"].replace("Rep. of Korea", "South Korea")
        .replace("China, Hong Kong SAR", "Hong Kong").replace("Viet Nam", "Vietnam"),
        "lon": cent[code]["lon"], "lat": cent[code]["lat"],
        "category": HS[r["cmdCode"]], "value_usd_m": r["primaryValue"] / 1e6,
    })
flows = pd.DataFrame(flows)
flows = flows[flows.value_usd_m >= 0.05]
flows["value_usd_m"] = flows.value_usd_m.round(2)
flows.to_csv(OUT / "import_flows_2025.csv", index=False)

# ---------------------------------------------------------------- ABS spending + population
STATES = {"1": "NSW", "2": "VIC", "3": "QLD", "4": "SA", "5": "WA", "6": "TAS", "7": "NT", "8": "ACT", "AUS": "Australia"}
STATE_NAMES = {"1": "New South Wales", "2": "Victoria", "3": "Queensland", "4": "South Australia",
               "5": "Western Australia", "6": "Tasmania", "7": "Northern Territory",
               "8": "Australian Capital Territory", "AUS": "Australia"}
hsi = pd.read_csv(RAW / "abs/HSI_M.csv", dtype=str)
hsi = hsi[(hsi.CATEGORY == "30") & (hsi.TSEST == "10")]
hsi = pd.DataFrame({
    "month": hsi.TIME_PERIOD, "state_code": hsi.STATE, "state": hsi.STATE.map(STATES),
    "spend_m": hsi.OBS_VALUE.astype(float).round(1),
}).sort_values(["state_code", "month"])
hsi.to_csv(OUT / "spending_monthly.csv", index=False)

erp = pd.read_csv(RAW / "abs/erp.csv", dtype=str)
latest_q = erp.TIME_PERIOD.max()
pop = erp[erp.TIME_PERIOD == latest_q].set_index("REGION").OBS_VALUE.astype(int)
last12 = sorted(hsi.month.unique())[-12:]
per = (hsi[hsi.month.isin(last12)].groupby("state_code").spend_m.sum()).reset_index()
per["state"] = per.state_code.map(STATES)
per["state_name"] = per.state_code.map(STATE_NAMES)
per["population"] = per.state_code.map(pop)
per["per_person"] = (per.spend_m * 1e6 / per.population).round(0)
per["spend_12m_m"] = per.spend_m.round(0)
per[["state_code", "state", "state_name", "spend_12m_m", "population", "per_person"]].to_csv(
    OUT / "spending_per_person.csv", index=False)
print("12 months:", last12[0], "to", last12[-1], "| population quarter:", latest_q)

# ---------------------------------------------------------------- Energy Rating models
TYPES = {  # file: (label, star column, size column, size unit)
    "rf": ("Fridges & freezers", "Star2009", "Tot Vol", "L"),
    "cw": ("Washing machines", "New Star", "Cap", "kg"),
    "dw": ("Dishwashers", "New Star", "Cap", "place settings"),
    "cd": ("Clothes dryers", "New Star", "Cap", "kg"),
    "tv": ("Televisions", "Star2", "screensize", "cm"),
}
BRAND_FIX = {
    "SAMSUNG ELECTRONICS": "Samsung", "SAMSUNG": "Samsung", "LG": "LG", "LG ELECTRONICS": "LG",
    "FISHER & PAYKEL": "Fisher & Paykel", "FISHER AND PAYKEL": "Fisher & Paykel", "TCL": "TCL",
    "CHIQ": "CHiQ", "AEG": "AEG", "BOSCH": "Bosch", "MIELE": "Miele", "ASKO": "Asko",
    "WESTINGHOUSE": "Westinghouse", "ELECTROLUX": "Electrolux", "HISENSE": "Hisense",
    "SONY": "Sony", "PHILIPS": "Philips", "HAIER": "Haier", "SMEG": "Smeg", "BEKO": "Beko",
    "PANASONIC": "Panasonic", "MIDEA": "Midea", "SIMPSON": "Simpson", "WESTINGHOUSE ": "Westinghouse",
}


def norm_brand(b):
    b = str(b).strip()
    if b.upper() in BRAND_FIX:
        return BRAND_FIX[b.upper()]
    return b.title() if (b.isupper() or b.islower()) and len(b) > 4 else b.capitalize() if b.islower() else b


rows = []
for f, (label, star, size, unit) in TYPES.items():
    d = pd.read_csv(RAW / f"er/{f}.csv", low_memory=False)
    sold = d["SoldIn" if f == "tv" else "Sold_in"].fillna("")
    d = d[sold.str.contains("Australia") & (d.SubmitStatus == "Approved") & (d["Availability Status"] == "Available")]
    out = pd.DataFrame({
        "type": label,
        "brand": d["Brand_Reg" if f == "tv" else "Brand"].map(norm_brand),
        "stars": pd.to_numeric(d[star], errors="coerce"),
        "kwh": pd.to_numeric(d["Labelled energy consumption (kWh/year)"], errors="coerce"),
        "size": pd.to_numeric(d[size], errors="coerce"),
        "country": d.Country.fillna("Unknown").str.split(",").str[0].str.strip(),
        "countries": d.Country.fillna("Unknown"),
    })
    if f == "rf":  # keep household units with a sensible volume
        out = out[out["size"].between(30, 1200)]
    rows.append(out.dropna(subset=["stars", "kwh"]))
models = pd.concat(rows)
models = models[models.kwh > 0]
models["size"] = models["size"].round(0)
models[["type", "brand", "stars", "kwh", "size", "country"]].to_csv(OUT / "models.csv", index=False)
print("models:", len(models), models.groupby("type").size().to_dict())

COUNTRY_ISO = {
    "China": 156, "Vietnam": 704, "Türkiye": 792, "Germany": 276, "Italy": 380, "South Korea": 410,
    "Austria": 40, "Indonesia": 360, "Thailand": 764, "United States of America": 840, "Bulgaria": 100,
    "India": 356, "Japan": 392, "Australia": 36, "Poland": 616, "Switzerland": 756, "Romania": 642,
    "Czechia": 203, "Slovenia": 705, "Slovakia": 703, "Spain": 724, "Bangladesh": 50, "Malaysia": 458,
    "Mexico": 484, "Netherlands": 528, "Egypt": 818, "Hungary": 348, "New Zealand": 554, "Canada": 124,
}
orig = collections.Counter()
star_sum = collections.Counter()
for _, r in models.iterrows():  # a model made in several countries counts once for each
    for c in str(r.countries).split(","):
        c = c.strip()
        if c in COUNTRY_ISO:
            orig[(c, r.type)] += 1
            star_sum[(c, r.type)] += r.stars
origins = pd.DataFrame([{
    "country": c, "iso": COUNTRY_ISO[c], "lon": cent[COUNTRY_ISO[c]]["lon"], "lat": cent[COUNTRY_ISO[c]]["lat"],
    "type": t, "models": n, "avg_stars": round(star_sum[(c, t)] / n, 2)} for (c, t), n in orig.items()])

# Map 3 circles overlap in Europe and South-East Asia, so push overlapping circles apart on screen
# (Dorling-style) and keep the true location for a leader line. Must match specs/06_origin_symbols.vg.json:
SCALE, ROTATE = 110, -60            # world panel: projection scale and rotate[0] (equalEarth)
AREA_MIN, AREA_MAX, MODELS_MAX = 6, 1800, 3000  # size scale: linear, [0, MODELS_MAX] -> [AREA_MIN, AREA_MAX] px²
EUROPE = (-12, 32, 35, 60)          # lon/lat box shown enlarged in its own panel, so it is not nudged
A1, A2, A3, A4, EM = 1.340264, -0.081106, 0.000893, 0.003796, math.sqrt(3) / 2


def equal_earth(lon, lat):  # d3.geoEqualEarthRaw, radians in, unscaled plane out
    t = math.asin(EM * math.sin(lat))
    t2, t6 = t * t, t ** 6
    return (lon * math.cos(t) / (EM * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2))),
            t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2)))


def equal_earth_inv(x, y):  # Newton's method, as in d3-geo
    t = y
    for _ in range(20):
        t2, t6 = t * t, t ** 6
        step = (t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2)) - y) / (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2))
        t -= step
        if abs(step) < 1e-12:
            break
    t2, t6 = t * t, t ** 6
    return EM * x * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)) / math.cos(t), math.asin(math.sin(t) / EM)


def to_px(lon, lat):
    x, y = equal_earth(math.radians(((lon + ROTATE + 180) % 360) - 180), math.radians(lat))
    return SCALE * x, -SCALE * y


def from_px(px, py):
    lon, lat = equal_earth_inv(px / SCALE, -py / SCALE)
    return ((math.degrees(lon) - ROTATE + 180) % 360) - 180, math.degrees(lat)


def dodge(group):
    anchors = [to_px(lo, la) for lo, la in zip(group.lon, group.lat)]
    pos = [list(a) for a in anchors]
    radii = [math.sqrt((AREA_MIN + (AREA_MAX - AREA_MIN) * m / MODELS_MAX) / math.pi) + 1.5 for m in group.models]
    for step in range(600):
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                dist = math.hypot(dx, dy) or 1e-6
                gap = radii[i] + radii[j] - dist
                if gap > 0:  # the smaller circle moves more
                    wi = radii[j] ** 2 / (radii[i] ** 2 + radii[j] ** 2)
                    ux, uy = dx / dist, dy / dist
                    pos[i][0] -= ux * gap * wi; pos[i][1] -= uy * gap * wi
                    pos[j][0] += ux * gap * (1 - wi); pos[j][1] += uy * gap * (1 - wi)
        if step < 500:  # gentle pull home, then a final pass of pure separation
            for p, a in zip(pos, anchors):
                p[0] += 0.03 * (a[0] - p[0]); p[1] += 0.03 * (a[1] - p[1])
    for i in range(len(pos)):  # self-check: no two circles overlap by more than half a pixel
        for j in range(i + 1, len(pos)):
            assert math.hypot(pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]) > radii[i] + radii[j] - 0.5
    out = [from_px(*p) for p in pos]
    group = group.copy()
    group["lon_d"] = [round(o[0], 3) for o in out]
    group["lat_d"] = [round(o[1], 3) for o in out]
    group["moved_px"] = [round(math.hypot(p[0] - a[0], p[1] - a[1]), 1) for p, a in zip(pos, anchors)]
    return group


in_europe = origins.lon.between(*EUROPE[:2]) & origins.lat.between(*EUROPE[2:])
origins["panel"] = in_europe.map({True: "Europe", False: "World"})
europe = origins[in_europe].assign(lon_d=origins.lon, lat_d=origins.lat, moved_px=0.0)
origins = pd.concat([europe] + [dodge(g) for _, g in origins[~in_europe].groupby("type")])
assert origins.models.max() <= MODELS_MAX
origins.sort_values(["type", "models"], ascending=[True, False]).to_csv(OUT / "model_origins.csv", index=False)

# ---------------------------------------------------------------- Amazon reviews
KEEP = {
    "Refrigerators": "Fridges", "Freezers": "Freezers", "Beverage Refrigerators": "Drinks fridges",
    "Ice Makers": "Ice makers", "Washers & Dryers": "Washers & dryers", "Built-In Dishwashers": "Dishwashers",
    "Countertop Dishwashers": "Benchtop dishwashers", "Ranges": "Ovens & stoves", "Wall Ovens": "Ovens & stoves",
    "Cooktops": "Cooktops", "Range Hoods": "Rangehoods",
}
item_cat, item_price = {}, {}
with gzip.open(RAW / "amazon/meta.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        c = r.get("categories") or []
        if len(c) >= 3 and c[0] == "Appliances" and c[2] in KEEP:
            item_cat[r["parent_asin"]] = KEEP[c[2]]
            try:
                item_price[r["parent_asin"]] = float(r["price"])
            except (TypeError, ValueError):
                pass

dist = collections.Counter()
monthly = collections.Counter()
price_band = collections.defaultdict(lambda: [0, 0])
BANDS = [(0, 100, "Under $100"), (100, 250, "$100–249"), (250, 500, "$250–499"),
         (500, 1000, "$500–999"), (1000, 1e9, "$1,000+")]
with gzip.open(RAW / "amazon/reviews.jsonl.gz", "rt") as fh:
    for line in fh:
        r = json.loads(line)
        cat = item_cat.get(r["parent_asin"])
        if not cat:
            continue
        stars = int(r["rating"])
        dist[(cat, stars)] += 1
        ts = datetime.fromtimestamp(r["timestamp"] / 1000, tz=timezone.utc)
        if 2016 <= ts.year:
            monthly[(ts.strftime("%Y-%m"), cat)] += 1
        p = item_price.get(r["parent_asin"])
        if p is not None:
            band = next(b for lo, hi, b in BANDS if lo <= p < hi)
            price_band[(cat, band)][0] += stars
            price_band[(cat, band)][1] += 1

pd.DataFrame([{"category": c, "stars": s, "reviews": n} for (c, s), n in dist.items()]) \
    .sort_values(["category", "stars"]).to_csv(OUT / "ratings_distribution.csv", index=False)
pd.DataFrame([{"month": m, "category": c, "reviews": n} for (m, c), n in monthly.items()]) \
    .sort_values(["category", "month"]).to_csv(OUT / "reviews_monthly.csv", index=False)
pd.DataFrame([{"category": c, "price_band": b, "band_order": [x[2] for x in BANDS].index(b),
               "avg_rating": round(s / n, 2), "reviews": n}
              for (c, b), (s, n) in price_band.items() if n >= 30]) \
    .sort_values(["category", "band_order"]).to_csv(OUT / "rating_by_price.csv", index=False)

for f in sorted(OUT.iterdir()):
    print(f"{f.name:28s} {f.stat().st_size/1024:8.1f} KB")
