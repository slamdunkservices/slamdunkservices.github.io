/* Slam Dunk Bets — lightweight GA4 event layer.
 * Loaded site-wide via _includes/after-body.html (see _quarto.yml). Depends on the gtag()
 * function that Quarto's google-analytics option defines in <head>; no-ops if it's missing.
 *
 * Events:
 *   cta_click    — a click on any link to Sharpduel, Whop, or the Dashboard, with where on the page it was.
 *   ai_referral  — first pageview of a session that arrived from an AI assistant / answer engine.
 *
 * X (Twitter) Pixel: the base code (pixel oqeds) loads on every page from _includes/head.html. Once
 * X_CTA_EVENT_ID is set (X Ads > Events Manager), each Sharpduel/Whop click also fires that conversion event.
 */
(() => {
  const CTA_HOSTS = ["sharpduel.com", "whop.com", "app.slamdunk.bet"];
  const AI_REFERRERS = /(^|\.)(chatgpt\.com|openai\.com|perplexity\.ai|claude\.ai|anthropic\.com|copilot\.microsoft\.com|gemini\.google\.com|you\.com|meta\.ai|poe\.com|duckduckgo\.com|grok\.com|x\.ai|mistral\.ai|deepseek\.com|kagi\.com)$/i;
  const X_CTA_EVENT_ID = "";  // e.g. "tw-oqeds-o1abd"
  const SECTIONS = ".hero, .final-cta, .sticky-cta, .lp-stats, .lp-faq, .feature-list, .track-record, .subscribe-ctas, .pricing, .faq-item, .navbar, footer, main";

  const send = (name, params) => {
    if (typeof window.gtag !== "function") return;
    window.gtag("event", name, params);
  };

  const hostMatches = (hostname) =>
    CTA_HOSTS.some((h) => hostname === h || hostname.endsWith("." + h));

  document.addEventListener(
    "click",
    (event) => {
      const link = event.target.closest && event.target.closest("a[href]");
      if (!link) return;
      let url;
      try {
        url = new URL(link.href, window.location.href);
      } catch {
        return;
      }
      if (!hostMatches(url.hostname)) return;
      const section = link.closest(SECTIONS);
      const location = section
        ? (section.className || "").split(/\s+/).filter(Boolean)[0] || section.tagName.toLowerCase()
        : "body";
      send("cta_click", {
        cta_destination: url.hostname.replace(/^www\./, ""),
        cta_text: (link.textContent || "").trim().slice(0, 100),
        cta_location: location,
        link_url: url.href,
        page_path: window.location.pathname,
      });
      if (X_CTA_EVENT_ID && url.hostname !== "app.slamdunk.bet" && typeof window.twq === "function") {
        window.twq("event", X_CTA_EVENT_ID, {});
      }
    },
    { capture: true }
  );

  try {
    if (document.referrer && !sessionStorage.getItem("sdb_ai_ref")) {
      const refHost = new URL(document.referrer).hostname;
      if (AI_REFERRERS.test(refHost)) {
        sessionStorage.setItem("sdb_ai_ref", "1");
        send("ai_referral", { referrer_host: refHost, page_path: window.location.pathname });
      }
    }
  } catch {
    /* sessionStorage or URL parsing unavailable; skip silently */
  }
})();
