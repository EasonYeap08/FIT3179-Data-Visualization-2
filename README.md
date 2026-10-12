# Plugged In: Australia's Home Appliances

FIT3179 Data Visualisation 2 · Monash University · Semester 2, 2026 · by Eason (EasonYeap08)

**Live page:** https://easonyeap08.github.io/FIT3179-Data-Visualization-2/

A scrolling data story for everyday Australians about the appliances we buy:
the small-appliance import boom, when and where we spend, where appliances are made,
what energy star ratings are worth on a power bill, and how happy owners are.

## Layout

| Path | What it is |
|---|---|
| `index.html`, `css/`, `js/main.js` | The web page; `main.js` embeds every chart with vega-embed |
| `specs/*.vg.json` | One Vega-Lite specification per chart (human-readable JSON) |
| `data/` | Small, pre-summarised data files the charts load (≈ 0.7 MB in total) |
| `scripts/prepare_data.py` | Turns the raw downloads into the files in `data/` |
| `scripts/format_specs.py` | Keeps the spec files consistently formatted |

## Charts

| # | Spec | Idiom |
|---|---|---|
| 1 | `01_import_slope` | Slopegraph |
| 2 | `02_import_heatmap` | Heatmap (diverging) |
| 3 | `03_spending_calendar` | Calendar heatmap |
| 4 | `04_state_choropleth` | **Map 1: choropleth**, linked to an indexed multi-line chart |
| 5 | `05_import_flow_map` | **Map 2: flow map**, with a ranked bar chart |
| 6 | `06_origin_symbols` | **Map 3: proportional symbol map** |
| 7 | `07_brand_efficiency` | Brand heatmap linked to a faceted jittered strip plot |
| 8 | `08_running_cost_boxplot` | Box plot with a price slider |
| 9 | `09_ratings_diverging` | Diverging stacked bar chart |
| 10 | `10_price_rating_heatmap` | Heatmap |
| 11 | `11_reviews_stream` | Streamgraph |

## Data sources

* Energy Rating registration data (labelled products), DCCEEW via data.gov.au, CC BY 3.0 AU
* UN Comtrade, Australian imports by HS code, 2015–2025
* ABS Monthly Household Spending Indicator, and ABS National, state and territory population, CC BY 4.0
* Amazon Reviews 2023 (Hou et al., McAuley Lab, UC San Diego)
* Boundaries: ABS ASGS 2021 State and Territory boundaries (CC BY 4.0); Natural Earth 110m via vega-datasets

Full citations, the story outline and every reference are in [`RESOURCES.md`](RESOURCES.md).
How each source and claim was fact-checked, and what changed as a result, is logged in
[`SOURCE_CHANGES.md`](SOURCE_CHANGES.md).

To rebuild `data/`, download the raw files listed at the top of `scripts/prepare_data.py` into `../raw`, then run
`python3 scripts/prepare_data.py ../raw`.
