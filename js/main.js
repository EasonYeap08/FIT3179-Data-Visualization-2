// Embeds every Vega-Lite spec from specs/ into its placeholder on the page.
// Shared styling lives here so each spec file only describes its own chart.

const theme = {
  background: null,
  font: "Barlow, system-ui, sans-serif",
  view: {stroke: null},
  axis: {
    labelColor: "#5b6670",
    titleColor: "#5b6670",
    labelFontSize: 11,
    titleFontSize: 12,
    titleFontWeight: 500,
    domainColor: "#d6d4ce",
    tickColor: "#d6d4ce",
    gridColor: "#eeede9",
    labelLimit: 240
  },
  legend: {
    labelColor: "#5b6670",
    titleColor: "#1f1f1d",
    labelFontSize: 11,
    titleFontSize: 12,
    titleFontWeight: 600,
    labelLimit: 300,
    titleLimit: 400
  },
  header: {labelColor: "#1e252b", titleColor: "#1e252b", labelFont: "Barlow Condensed", labelFontSize: 15},
  text: {color: "#1f1f1d"},
  tooltipFormat: {numberFormat: ",.0f"}
};

const charts = [
  ["#vis-slope", "specs/01_import_slope.vg.json"],
  ["#vis-heat", "specs/02_import_heatmap.vg.json"],
  ["#vis-calendar", "specs/03_spending_calendar.vg.json"],
  ["#vis-states", "specs/04_state_choropleth.vg.json"],
  ["#vis-flow", "specs/05_import_flow_map.vg.json"],
  ["#vis-origins", "specs/06_origin_symbols.vg.json"],
  ["#vis-brands", "specs/07_brand_efficiency.vg.json", "canvas"],
  ["#vis-cost", "specs/08_running_cost_boxplot.vg.json"],
  ["#vis-stream", "specs/11_reviews_stream.vg.json"],
  ["#vis-diverge", "specs/09_ratings_diverging.vg.json"],
  ["#vis-price", "specs/10_price_rating_heatmap.vg.json"]
];

const views = {};  // kept for debugging in the browser console

for (const [el, spec, renderer] of charts) {
  vegaEmbed(el, spec, {
    actions: {export: true, source: true, compiled: false, editor: true},
    config: theme,
    renderer: renderer || "svg"
  }).then(result => {
    views[el] = result.view;
  }).catch(err => {
    document.querySelector(el).textContent = "Chart failed to load: " + err.message;
    console.error(spec, err);
  });
}
