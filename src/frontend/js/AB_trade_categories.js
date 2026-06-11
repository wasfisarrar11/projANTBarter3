/**
 * Canonical blue-collar trade categories — JS mirror of
 * src/backend/python/app/trade_categories.py.
 *
 * Keep the two in sync. Slugs are referenced by:
 *   - Homepage category button onclick handlers (AB_Home_UI2_Update.html)
 *   - AB_find_bp.html ?category= filter
 *   - Future matching / search UI
 */
window.AB_TRADE_CATEGORIES = Object.freeze({
  plumbing: [
    "drain", "faucet", "leak", "pipe", "plumber", "plumbing",
    "sewer", "toilet", "water heater",
  ],
  electrical: [
    "amp", "breaker", "circuit", "electric", "electrical",
    "electrician", "outlet", "panel", "rewire", "wiring",
  ],
  carpentry: [
    "cabinet", "carpenter", "carpentry", "deck", "drywall",
    "framing", "trim", "wood",
  ],
  hvac: [
    "ac", "air conditioner", "ductwork", "furnace", "heat pump",
    "hvac", "mini split", "thermostat", "vent",
  ],
  roofing: ["flashing", "gutter", "roof", "roofer", "roofing", "shingle"],
  landscaping: [
    "irrigation", "landscaping", "lawn", "leaf removal", "mowing",
    "mulch", "snow removal", "sprinkler", "tree",
  ],
  auto_repair: [
    "auto", "brake", "car repair", "engine", "mechanic",
    "oil change", "tire", "transmission",
  ],
  painting: ["paint", "painter", "painting", "primer", "stain"],
  moving: ["haul", "loading", "move", "mover", "moving", "packing"],
  handyman: ["fix", "handyman", "install", "odd jobs", "repair"],
});

(function () {
  /**
   * Return [slug, hits] pairs sorted by descending hit count.
   * Lowercased word-boundary matching.
   */
  window.AB_categorize = function (text) {
    if (!text || typeof text !== "string") return [];
    const lower = text.toLowerCase();
    const scored = [];
    for (const slug of Object.keys(window.AB_TRADE_CATEGORIES)) {
      let hits = 0;
      for (const kw of window.AB_TRADE_CATEGORIES[slug]) {
        // \b doesn't behave well for phrases with spaces, so use a custom
        // boundary that allows start-of-string and non-word neighbors.
        const re = new RegExp(
          "(^|[^a-z0-9])" +
            kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
            "([^a-z0-9]|$)",
          "g"
        );
        const m = lower.match(re);
        if (m) hits += m.length;
      }
      if (hits) scored.push([slug, hits]);
    }
    scored.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    return scored;
  };
})();
