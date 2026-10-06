--[[
  seo-schema.lua — emits one JSON-LD <script type="application/ld+json"> per HTML page.
  Declared project-wide in _quarto.yml (filters:). Pure Lua; needs only Quarto.

  Page types (from the input path relative to the project root):
    index.qmd        -> Organization + WebSite
    posts/**         -> + BlogPosting + BreadcrumbList
    faq.qmd          -> + FAQPage built from ::: {.faq-item} divs (first header = question, rest = answer)
    subscribe.qmd    -> + WebPage + Product/Offer[] from the `schema-offers:` frontmatter list
    nba/, wnba/, mlb/ -> + WebPage + BreadcrumbList (Home > <sport> Picks > page); a folder's index.qmd is the hub
    everything else  -> + WebPage
    Any page with ::: {.faq-item} blocks also gets a FAQPage node (faq.qmd gets it instead of WebPage).

  Frontmatter hooks:
    description, image, image-alt, date, date-modified, categories, subtitle  (standard Quarto keys)
    schema-type: none   -> skip this page entirely (used by 404.qmd)
    schema-offers: [{name, price, billing: P1W|P1M|P1Y}]

  Also emits, per page:
    <meta property="og:url"> and <meta property="og:type"> (article on posts, website elsewhere), plus
    article:published_time / article:modified_time / article:tag on posts (Quarto only writes the basic OG set).
  And on every body image whose file is a local PNG or JPEG: width/height attributes read from the file
  header (pure Lua), so the browser reserves space before the image loads (no layout shift). An explicit
  width= on the image is kept and the height is scaled to match.

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

-- A folder's index page is addressed as the folder (matches Quarto's canonical tag and the sitemap hook).
local function page_url(rel)
  local s = stem(rel)
  if s == "index" then return SITE .. "/" end
  local dir = s:match("^(.-)/index$")
  if dir then return SITE .. "/" .. dir .. "/" end
  return SITE .. "/" .. s .. ".html"
end

-- Sport hubs: folder -> breadcrumb label. Pages in these folders get Home > hub > page breadcrumbs.
local HUBS = { nba = "NBA Picks", wnba = "WNBA Picks", mlb = "MLB Picks" }

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

-- ---------- image dimensions ----------

local function be16(str, i) return str:byte(i) * 256 + str:byte(i + 1) end
local function be32(str, i) return ((str:byte(i) * 256 + str:byte(i + 1)) * 256 + str:byte(i + 2)) * 256 + str:byte(i + 3) end

-- Return width, height for a PNG or JPEG file, or nil for anything else / unreadable.
local function image_size(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local head = f:read(32)
  if not head or #head < 24 then f:close() return nil end
  if head:sub(1, 8) == "\137PNG\r\n\26\n" then
    f:close()
    return be32(head, 17), be32(head, 21)
  end
  if head:sub(1, 2) ~= "\255\216" then f:close() return nil end
  f:seek("set", 2)
  while true do
    local marker = f:read(2)
    if not marker or marker:byte(1) ~= 0xFF then break end
    local code = marker:byte(2)
    if code == 0xD8 or (code >= 0xD0 and code <= 0xD7) or code == 0x01 then
      -- standalone markers, no length
    else
      local lenb = f:read(2)
      if not lenb or #lenb < 2 then break end
      local len = be16(lenb, 1)
      if code == 0xC0 or code == 0xC1 or code == 0xC2 or code == 0xC3 or code == 0xC5 or code == 0xC6 or code == 0xC7
        or code == 0xC9 or code == 0xCA or code == 0xCB or code == 0xCD or code == 0xCE or code == 0xCF then
        local sof = f:read(5)
        f:close()
        if not sof or #sof < 5 then return nil end
        return be16(sof, 4), be16(sof, 2)
      end
      if code == 0xD9 or code == 0xDA then break end
      f:seek("cur", len - 2)
    end
  end
  f:close()
  return nil
end

-- Resolve an image src (root-absolute, relative to the page, or page-folder relative) to a filesystem path.
local function image_path(src, rel)
  if src == nil or src:match("^https?://") or src:match("^data:") then return nil end
  local root = quarto.project.directory
  if root == nil then return nil end
  if src:sub(1, 1) == "/" then return pandoc.path.join({ root, src:sub(2) }) end
  local dir = pandoc.path.directory(rel)
  if dir == "." or dir == "" then return pandoc.path.join({ root, src }) end
  return pandoc.path.join({ root, dir, src })
end

function Image(img)
  if not quarto.doc.is_format("html") then return nil end
  local rel = rel_input()
  if rel == nil then return nil end
  local attrs = img.attributes
  if attrs.height then return nil end
  local w, h = image_size(image_path(img.src, rel))
  if not w or not h or w == 0 then return nil end
  local want = attrs.width and tonumber(attrs.width:match("^(%d+)$"))
  if want then
    attrs.height = tostring(math.floor(want * h / w + 0.5))
  elseif attrs.width == nil then
    attrs.width = tostring(w)
    attrs.height = tostring(h)
  end
  return img
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
    local faq = faq_node(doc.blocks, url, title, desc)
    if faq then
      faq["@id"] = url .. "#faq"
      graph[#graph + 1] = faq
    end
    local folder = s:match("^([^/]+)/")
    if folder and HUBS[folder] then
      local crumbs = { { "Home", SITE .. "/" }, { HUBS[folder], SITE .. "/" .. folder .. "/" } }
      if s ~= folder .. "/index" then crumbs[#crumbs + 1] = { title, url } end
      graph[#graph + 1] = breadcrumb_node(crumbs)
    end
  end

  local json = quarto.json.encode({ ["@context"] = "https://schema.org", ["@graph"] = graph })
  json = json:gsub("</", "<\\/")
  quarto.doc.include_text("in-header", '<script type="application/ld+json">' .. json .. "</script>")

  -- Open Graph extras that Quarto does not write itself.
  local function meta_tag(prop, content)
    if content == nil or content == "" then return end
    content = tostring(content):gsub("&", "&amp;"):gsub('"', "&quot;")
    quarto.doc.include_text("in-header", '<meta property="' .. prop .. '" content="' .. content .. '">')
  end
  meta_tag("og:url", url)
  if s:match("^posts/") then
    meta_tag("og:type", "article")
    local published = iso_date(meta_str(m, "date"))
    meta_tag("article:published_time", published)
    meta_tag("article:modified_time", iso_date(meta_str(m, "date-modified")) or published)
    if m.categories then
      for _, c in ipairs(m.categories) do meta_tag("article:tag", stringify(c)) end
    end
  else
    meta_tag("og:type", "website")
  end
  return nil
end
