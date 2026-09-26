--[[
  seo-schema.lua — emits one JSON-LD <script type="application/ld+json"> per HTML page.
  Declared project-wide in _quarto.yml (filters:). Pure Lua; needs only Quarto.

  Page types (from the input path relative to the project root):
    index.qmd        -> Organization + WebSite
    posts/**         -> + BlogPosting + BreadcrumbList
    faq.qmd          -> + FAQPage built from ::: {.faq-item} divs (first header = question, rest = answer)
    subscribe.qmd    -> + WebPage + Product/Offer[] from the `schema-offers:` frontmatter list
    everything else  -> + WebPage

  Frontmatter hooks:
    description, image, image-alt, date, date-modified, categories, subtitle  (standard Quarto keys)
    schema-type: none   -> skip this page entirely (used by 404.qmd)
    schema-offers: [{name, price, billing: P1W|P1M|P1Y}]

  Descriptions must still be written in YAML: Quarto builds the Open Graph tags before this filter runs.
]]

local SITE = "https://slamdunk.bet"
local SITE_NAME = "Slam Dunk Bets"
local SITE_DESC = "Model-driven NBA, WNBA and MLB prop picks from a team of data scientists: first baskets, home runs and NRFI/YRFI, refreshed every 30 minutes and tracked to 8,000+ net units since 2021-22."
local DEFAULT_IMAGE = SITE .. "/images/brand/og-default.png"
local LOGO = SITE .. "/images/brand/logo-square.png"
local ORG_ID = SITE .. "/#organization"
local SITE_ID = SITE .. "/#website"
local SUBSCRIBE_URL = "https://sharpduel.com/slam_dunk_bets"

local stringify = pandoc.utils.stringify

-- ---------- metadata helpers ----------

local function meta_str(m, key)
  local v = m[key]
  if v == nil or type(v) == "boolean" then return nil end
  local s = stringify(v)
  if s == "" then return nil end
  return s
end

local function meta_true(m, key)
  local v = m[key]
  if v == nil then return false end
  if type(v) == "boolean" then return v end
  return stringify(v) == "true"
end

local MONTHS = { january=1, february=2, march=3, april=4, may=5, june=6, july=7,
                 august=8, september=9, october=10, november=11, december=12 }

-- Return YYYY-MM-DD from an ISO string or a "Month D, YYYY" display string.
local function iso_date(s)
  if s == nil then return nil end
  local y, mo, d = s:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)")
  if y then return string.format("%s-%s-%s", y, mo, d) end
  local mname, day, year = s:match("^(%a+)%s+(%d+),%s+(%d%d%d%d)")
  if mname and MONTHS[mname:lower()] then
    return string.format("%s-%02d-%02d", year, MONTHS[mname:lower()], tonumber(day))
  end
  local mm, dd, yy = s:match("^(%d+)/(%d+)/(%d%d%d%d)")
  if mm then return string.format("%s-%02d-%02d", yy, tonumber(mm), tonumber(dd)) end
  return s
end

-- ---------- path helpers ----------

local function rel_input()
  local input = quarto.doc.input_file
  if input == nil then return nil end
  local dir = quarto.project.directory
  if dir then return pandoc.path.make_relative(input, dir) end
  return pandoc.path.filename(input)
end

local function stem(rel)
  return (rel:gsub("%.[^./]+$", ""))
end

local function page_url(rel)
  local s = stem(rel)
  if s == "index" then return SITE .. "/" end
  return SITE .. "/" .. s .. ".html"
end

-- Resolve /images/.., ../../images/.., images/.. (relative to the page's folder) to an absolute URL.
local function abs_url(p, rel)
  if p == nil or p == "" then return nil end
  if p:match("^https?://") then return p end
  local segs = {}
  if p:sub(1, 1) ~= "/" then
    local dir = pandoc.path.directory(rel)
    if dir ~= "." and dir ~= "" then
      for s in dir:gmatch("[^/]+") do segs[#segs + 1] = s end
    end
  end
  for s in p:gmatch("[^/]+") do
    if s == ".." then table.remove(segs) elseif s ~= "." then segs[#segs + 1] = s end
  end
  return SITE .. "/" .. table.concat(segs, "/")
end

-- Make every href in an HTML fragment absolute (used for FAQ answers).
local function absolutize_hrefs(html)
  return (html:gsub('href="([^"]+)"', function(h)
    if h:match("^https?://") or h:match("^mailto:") or h:match("^#") then
      return 'href="' .. h .. '"'
    end
    h = h:gsub("%.qmd$", ".html"):gsub("^/", "")
    return 'href="' .. SITE .. "/" .. h .. '"'
  end))
end

-- ---------- node builders ----------

local function org_node()
  return {
    ["@type"] = "Organization",
    ["@id"] = ORG_ID,
    name = SITE_NAME,
    legalName = "Slam Dunk Betting Services LLC",
    url = SITE .. "/",
    description = SITE_DESC,
    foundingDate = "2020",
    email = "slamdunkbettingservices@gmail.com",
    logo = { ["@type"] = "ImageObject", url = LOGO, width = 512, height = 512 },
    image = DEFAULT_IMAGE,
    sameAs = {
      "https://x.com/slam_dunk_bets",
      "https://x.com/jimtheflash",
      "https://sharpduel.com/slam_dunk_bets",
      "https://whop.com/slam-dunk-bets",
      "https://app.slamdunk.bet",
    },
  }
end

local function website_node()
  return {
    ["@type"] = "WebSite",
    ["@id"] = SITE_ID,
    url = SITE .. "/",
    name = SITE_NAME,
    description = SITE_DESC,
    inLanguage = "en-US",
    publisher = { ["@id"] = ORG_ID },
  }
end

local function breadcrumb_node(items)
  local list = {}
  for i, it in ipairs(items) do
    list[i] = { ["@type"] = "ListItem", position = i, name = it[1], item = it[2] }
  end
  return { ["@type"] = "BreadcrumbList", itemListElement = list }
end

local function webpage_node(url, title, desc, image)
  return {
    ["@type"] = "WebPage",
    ["@id"] = url,
    url = url,
    name = title,
    description = desc,
    inLanguage = "en-US",
    isPartOf = { ["@id"] = SITE_ID },
    primaryImageOfPage = { ["@type"] = "ImageObject", url = image },
    publisher = { ["@id"] = ORG_ID },
  }
end

local function blogposting_node(m, url, title, desc, image)
  local cats = {}
  if m.categories then
    for _, c in ipairs(m.categories) do cats[#cats + 1] = stringify(c) end
  end
  local published = iso_date(meta_str(m, "date"))
  local modified = iso_date(meta_str(m, "date-modified")) or published
  local node = {
    ["@type"] = "BlogPosting",
    ["@id"] = url .. "#article",
    mainEntityOfPage = url,
    url = url,
    headline = title,
    description = desc,
    image = image,
    datePublished = published,
    dateModified = modified,
    inLanguage = "en-US",
    author = { ["@id"] = ORG_ID },
    publisher = { ["@id"] = ORG_ID },
    isPartOf = { ["@type"] = "Blog", ["@id"] = SITE .. "/articles.html#blog", name = SITE_NAME .. " Articles" },
  }
  local subtitle = meta_str(m, "subtitle")
  if subtitle then node.alternativeHeadline = subtitle end
  if #cats > 0 then node.keywords = table.concat(cats, ", ") end
  return node
end

local function faq_node(blocks, url, title, desc)
  local items = {}
  for _, b in ipairs(blocks) do
    if b.t == "Div" and b.classes:includes("faq-item") then
      local question, answer = nil, pandoc.List()
      for _, inner in ipairs(b.content) do
        if inner.t == "Header" and question == nil then
          question = stringify(inner)
        else
          answer:insert(inner)
        end
      end
      if question then
        local html = absolutize_hrefs(pandoc.write(pandoc.Pandoc(answer), "html"))
        items[#items + 1] = {
          ["@type"] = "Question",
          name = question,
          acceptedAnswer = { ["@type"] = "Answer", text = html },
        }
      end
    end
  end
  if #items == 0 then return nil end
  return {
    ["@type"] = "FAQPage",
    ["@id"] = url,
    url = url,
    name = title,
    description = desc,
    inLanguage = "en-US",
    isPartOf = { ["@id"] = SITE_ID },
    publisher = { ["@id"] = ORG_ID },
    mainEntity = items,
  }
end

local BILLING_UNIT = { P1W = "WEE", P1M = "MON", P1Y = "ANN" }

local function product_node(m, url, desc)
  local list = m["schema-offers"]
  if list == nil then return nil end
  local offers = {}
  for _, o in ipairs(list) do
    local name = o.name and stringify(o.name) or nil
    local price = o.price and stringify(o.price) or nil
    local billing = o.billing and stringify(o.billing) or nil
    if name and price then
      local offer = {
        ["@type"] = "Offer",
        name = name,
        price = price,
        priceCurrency = "USD",
        url = SUBSCRIBE_URL,
        availability = "https://schema.org/InStock",
        category = "Subscription",
      }
      if billing and BILLING_UNIT[billing] then
        offer.priceSpecification = {
          ["@type"] = "UnitPriceSpecification",
          price = price,
          priceCurrency = "USD",
          billingDuration = 1,
          referenceQuantity = { ["@type"] = "QuantitativeValue", value = 1, unitCode = BILLING_UNIT[billing] },
        }
      end
      offers[#offers + 1] = offer
    end
  end
  if #offers == 0 then return nil end
  return {
    ["@type"] = "Product",
    ["@id"] = url .. "#product",
    name = SITE_NAME .. " subscription",
    description = desc,
    url = url,
    image = DEFAULT_IMAGE,
    -- Google's validator does not resolve @id refs here; it wants a typed Brand inline.
    brand = { ["@type"] = "Brand", name = SITE_NAME },
    offers = offers,
  }
end

-- ---------- main ----------

function Pandoc(doc)
  if not quarto.doc.is_format("html") then return nil end
  local m = doc.meta
  if meta_str(m, "schema-type") == "none" then return nil end
  if meta_true(m, "draft") then return nil end

  local rel = rel_input()
  if rel == nil then return nil end
  local s = stem(rel)
  local url = page_url(rel)
  local title = meta_str(m, "title") or meta_str(m, "pagetitle") or SITE_NAME
  local desc = meta_str(m, "description") or SITE_DESC
  local image = abs_url(meta_str(m, "image"), rel) or DEFAULT_IMAGE

  local graph = { org_node(), website_node() }

  if s:match("^posts/") then
    graph[#graph + 1] = blogposting_node(m, url, title, desc, image)
    graph[#graph + 1] = breadcrumb_node({
      { "Home", SITE .. "/" },
      { "Articles", SITE .. "/articles.html" },
      { title, url },
    })
  elseif s == "faq" then
    graph[#graph + 1] = faq_node(doc.blocks, url, title, desc) or webpage_node(url, title, desc, image)
  elseif s == "index" then
    -- Organization + WebSite carry the homepage.
  else
    graph[#graph + 1] = webpage_node(url, title, desc, image)
    local product = product_node(m, url, desc)
    if product then graph[#graph + 1] = product end
  end

  local json = quarto.json.encode({ ["@context"] = "https://schema.org", ["@graph"] = graph })
  json = json:gsub("</", "<\\/")
  quarto.doc.include_text("in-header", '<script type="application/ld+json">' .. json .. "</script>")
  return nil
end
