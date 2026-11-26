/* Data store: cart, checkout and downloads for the static /data/ pages.
 *
 * The site is static; the only server is the small function in _store/fulfillment/main.py.
 * Its URL arrives in <meta name="sdb-store-api">, and the price list in
 * <script type="application/json" id="sdb-store-prices">, both written by _scripts/store/build.py.
 *
 *   any /data/ page     "Add" buttons ([data-store-add]) put {league, dataset, season} in the cart
 *   /data/cart.html     the cart, with the total and the Stripe checkout button
 *   /data/thanks.html   ?session_id=cs_...  trades the paid checkout for a library token
 *   /data/library.html  #t=<token>  lists the files that token unlocks and downloads them
 *   recover form        email + receipt number -> the same token
 *
 * Prices shown here are for display. The server prices the cart again from Stripe at checkout,
 * so editing this page changes nothing a buyer pays. The library token lives in the URL fragment
 * (never sent to a server by the browser, never in analytics) and in localStorage.
 */
(function () {
  'use strict';

  var apiMeta = document.querySelector('meta[name="sdb-store-api"]');
  var API = apiMeta ? apiMeta.content.replace(/\/+$/, '') : '';
  var pricesNode = document.getElementById('sdb-store-prices');
  var STORE = {};
  try { STORE = pricesNode ? JSON.parse(pricesNode.textContent) : {}; } catch (e) { STORE = {}; }
  var TOKEN_KEY = 'sdb_store_token';
  var CART_KEY = 'sdb_store_cart';
  var root = document.querySelector('[data-store-view]');
  var view = root ? root.getAttribute('data-store-view') : '';

  // ---------- small helpers ----------

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }

  function read(key, fallback) {
    try { return JSON.parse(window.localStorage.getItem(key)) || fallback; } catch (e) { return fallback; }
  }

  function write(key, value) {
    try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ }
  }

  function status(message, kind) {
    var box = root && root.querySelector('[data-store-status]');
    if (!box) return;
    box.textContent = message;
    box.className = 'store-status' + (kind ? ' store-status-' + kind : '');
    box.hidden = !message;
  }

  function call(path, options) {
    if (!API) {
      return Promise.reject(new Error('Checkout and downloads are not switched on yet. Email us and we will sort you out by hand.'));
    }
    return fetch(API + path, options).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        if (!res.ok) throw new Error(body.error || 'Something went wrong. Try again in a minute.');
        return body;
      });
    });
  }

  function money(dollars) {
    return '$' + Number(dollars).toLocaleString('en-US');
  }

  function size(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  function pageUrl(name) {
    return new URL(name, window.location.href).toString();
  }

  // ---------- prices ----------

  function league(code) { return STORE[code] || null; }

  function datasetName(item) {
    var lg = league(item.league);
    if (item.season === 'archive') return 'Complete archive';
    if (item.dataset === 'all') return 'Complete set';
    return (lg && lg.names && lg.names[item.dataset]) || item.dataset.replace(/-/g, ' ');
  }

  function seasonLabel(item) {
    var lg = league(item.league);
    if (item.season === 'archive') return 'every completed season';
    return item.season + (lg && lg.current === item.season ? ' season pass' : '');
  }

  function priceOf(item) {
    var lg = league(item.league);
    if (!lg) return null;
    if (item.season === 'archive') return lg.archive == null ? null : lg.archive;
    var row = lg.prices[item.dataset];
    if (!row) return null;
    return lg.current === item.season ? row.pass : row.season;
  }

  // ---------- cart ----------

  function same(a, b) {
    return a.league === b.league && a.dataset === b.dataset && a.season === b.season;
  }

  function cart() {
    return read(CART_KEY, []).filter(function (i) {
      return i && i.league && i.dataset && i.season && priceOf(i) != null;
    });
  }

  function inCart(item) {
    return cart().some(function (i) { return same(i, item); });
  }

  function setCart(items) {
    write(CART_KEY, items);
    paintButtons();
    paintBar();
    if (view === 'cart') paintCart();
  }

  function toggle(item) {
    var items = cart();
    if (inCart(item)) {
      items = items.filter(function (i) { return !same(i, item); });
    } else {
      items.push(item);
      if (window.gtag) {
        window.gtag('event', 'data_add_to_cart', { item_id: [item.league, item.dataset, item.season].join('/') });
      }
    }
    setCart(items);
  }

  function total(items) {
    return items.reduce(function (sum, i) { return sum + priceOf(i); }, 0);
  }

  function itemOf(button) {
    return {
      league: button.getAttribute('data-league'),
      dataset: button.getAttribute('data-dataset'),
      season: button.getAttribute('data-season')
    };
  }

  function paintButtons() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-store-add]'), function (button) {
      var on = inCart(itemOf(button));
      button.textContent = on ? 'In cart' : (button.getAttribute('data-label') || 'Add');
      button.classList.toggle('is-in-cart', on);
      button.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function paintBar() {
    var bar = document.querySelector('.store-cartbar');
    var items = cart();
    if (!items.length || view === 'cart') {
      if (bar) bar.remove();
      return;
    }
    if (!bar) {
      bar = el('div', { class: 'store-cartbar', role: 'status' });
      document.body.appendChild(bar);
    }
    bar.textContent = '';
    bar.appendChild(el('span', { text: items.length + (items.length === 1 ? ' file set' : ' file sets') + ' · ' + money(total(items)) }));
    bar.appendChild(el('a', { class: 'btn btn-primary btn-sm', href: pageUrl(bar.getAttribute('data-cart') || cartHref()), text: 'View cart' }));
  }

  function cartHref() {
    var link = document.querySelector('[data-store-cart-link]');
    return link ? link.getAttribute('href') : 'cart.html';
  }

  // Cheaper ways to buy what is already in the cart: the league's complete set for a season.
  function suggestions(items) {
    var out = [];
    var groups = {};
    items.forEach(function (i) {
      if (i.dataset === 'all' || i.season === 'archive') return;
      var key = i.league + '|' + i.season;
      (groups[key] = groups[key] || []).push(i);
    });
    Object.keys(groups).forEach(function (key) {
      var parts = key.split('|');
      var bundle = { league: parts[0], dataset: 'all', season: parts[1] };
      var bundlePrice = priceOf(bundle);
      var sum = total(groups[key]);
      if (bundlePrice != null && groups[key].length > 1 && sum > bundlePrice) {
        out.push({ bundle: bundle, replaces: groups[key], saves: sum - bundlePrice });
      }
    });
    return out;
  }

  function paintCart() {
    var list = root.querySelector('[data-store-cart]');
    var foot = root.querySelector('[data-store-cart-foot]');
    var items = cart();
    list.textContent = '';
    foot.textContent = '';
    if (!items.length) {
      list.appendChild(el('p', { class: 'store-empty', text: 'Nothing in the cart yet.' }));
      return;
    }
    var rows = items.map(function (item) {
      var remove = el('button', { type: 'button', class: 'btn btn-link btn-sm store-remove', text: 'Remove' });
      remove.addEventListener('click', function () { toggle(item); });
      return el('tr', {}, [
        el('td', { text: (league(item.league).name || item.league.toUpperCase()) + ' ' + datasetName(item) }),
        el('td', { text: seasonLabel(item) }),
        el('td', { class: 'num', text: money(priceOf(item)) }),
        el('td', { class: 'num' }, [remove])
      ]);
    });
    list.appendChild(el('table', { class: 'table store-table' }, [
      el('thead', {}, [el('tr', {}, [
        el('th', { text: 'Files' }), el('th', { text: 'Season' }),
        el('th', { class: 'num', text: 'Price' }), el('th', {})
      ])]),
      el('tbody', {}, rows),
      el('tfoot', {}, [el('tr', {}, [
        el('th', { colspan: '2', text: 'Total, one-time' }),
        el('th', { class: 'num', text: money(total(items)) }), el('th', {})
      ])])
    ]));

    suggestions(items).forEach(function (s) {
      var lg = league(s.bundle.league);
      var swap = el('button', { type: 'button', class: 'btn btn-outline-primary btn-sm', text: 'Switch to the complete set' });
      swap.addEventListener('click', function () {
        var kept = cart().filter(function (i) {
          return !s.replaces.some(function (r) { return same(r, i); });
        });
        kept.push(s.bundle);
        setCart(kept);
      });
      list.appendChild(el('p', { class: 'store-hint' }, [
        el('span', {
          text: 'The ' + lg.name + ' ' + s.bundle.season + ' complete set is ' + money(priceOf(s.bundle)) +
            ' and includes all of these, plus the rest. That is ' + money(s.saves) + ' less. '
        }),
        swap
      ]));
    });

    var pay = el('button', { type: 'button', class: 'btn btn-primary btn-lg', text: 'Check out · ' + money(total(items)) });
    pay.addEventListener('click', function () {
      pay.disabled = true;
      status('Opening secure checkout…');
      call('/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: items })
      }).then(function (body) {
        if (window.gtag) window.gtag('event', 'data_begin_checkout', { value: total(items), currency: 'USD' });
        window.location.href = body.url;
      }).catch(function (err) {
        pay.disabled = false;
        status(err.message, 'warn');
      });
    });
    foot.appendChild(pay);
  }

  // ---------- thanks: checkout -> token ----------

  function thanks() {
    var session = new URLSearchParams(window.location.search).get('session_id');
    if (!session) {
      status('No checkout reference on this page. If you just paid, use the link Stripe sent you back with, or recover your library below.', 'warn');
      return;
    }
    status('Confirming your purchase…');
    call('/claim?session_id=' + encodeURIComponent(session)).then(function (body) {
      write(TOKEN_KEY, body.token);
      write(CART_KEY, []);
      status('');
      var href = pageUrl('library.html#t=' + body.token);
      var done = root.querySelector('[data-store-claimed]');
      if (done) done.hidden = false;
      var link = root.querySelector('[data-store-library-link]');
      if (link) link.href = href;
      var keep = root.querySelector('[data-store-keep]');
      if (keep) keep.value = href;
      if (window.gtag) window.gtag('event', 'data_purchase_claimed');
    }).catch(function (err) { status(err.message, 'warn'); });
  }

  // ---------- library: token -> files ----------

  function paintFiles(token, body) {
    var list = root.querySelector('[data-store-files]');
    list.textContent = '';
    if (!body.files.length) {
      status('Your purchase is confirmed and its files are not posted yet. In-season files appear after the next morning build. Nothing after a full day? Email us.', 'warn');
      return;
    }
    status('');
    var groups = {};
    body.files.forEach(function (f) {
      var key = f.league.toUpperCase() + ' ' + f.season;
      (groups[key] = groups[key] || []).push(f);
    });
    Object.keys(groups).sort().reverse().forEach(function (key) {
      var rows = groups[key].map(function (f) {
        var href = API + '/download?t=' + encodeURIComponent(token) + '&f=' + encodeURIComponent(f.path);
        return el('tr', {}, [
          el('td', {}, [el('a', { href: href, rel: 'nofollow', class: 'store-file', text: f.name })]),
          el('td', { text: f.dataset.replace(/-/g, ' ') }),
          el('td', { class: 'num', text: size(f.bytes) }),
          el('td', { text: f.updated ? f.updated.slice(0, 10) : '' })
        ]);
      });
      list.appendChild(el('h2', { text: key }));
      list.appendChild(el('table', { class: 'table store-table' }, [
        el('thead', {}, [el('tr', {}, [
          el('th', { text: 'File' }), el('th', { text: 'Dataset' }),
          el('th', { class: 'num', text: 'Size' }), el('th', { text: 'Updated' })
        ])]),
        el('tbody', {}, rows)
      ]));
    });
  }

  function library() {
    var fromHash = (window.location.hash.match(/t=([A-Za-z0-9_.-]+)/) || [])[1];
    var token = fromHash || read(TOKEN_KEY, '');
    if (!token) {
      status('No library on this device yet. Open the link from your purchase, or recover it with your receipt below.', 'warn');
      return;
    }
    status('Loading your files…');
    call('/library?t=' + encodeURIComponent(token)).then(function (body) {
      write(TOKEN_KEY, token);
      paintFiles(token, body);
    }).catch(function (err) { status(err.message, 'warn'); });
  }

  // ---------- recover: email + receipt -> token ----------

  function wireRecover() {
    var form = document.querySelector('[data-store-recover]');
    if (!form) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var out = form.querySelector('[data-store-recover-status]');
      out.textContent = 'Checking…';
      call('/recover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.elements.email.value, receipt: form.elements.receipt.value })
      }).then(function (body) {
        write(TOKEN_KEY, body.token);
        window.location.href = pageUrl('library.html#t=' + body.token);
        if (view === 'library') window.location.reload();
      }).catch(function (err) { out.textContent = err.message; });
    });
  }

  // ---------- wire up ----------

  document.addEventListener('click', function (event) {
    var button = event.target.closest && event.target.closest('[data-store-add]');
    if (!button) return;
    event.preventDefault();
    toggle(itemOf(button));
  });

  paintButtons();
  paintBar();
  if (view === 'cart') paintCart();
  if (view === 'thanks') thanks();
  if (view === 'library') library();
  wireRecover();
  window.addEventListener('storage', function (event) {
    if (event.key === CART_KEY) { paintButtons(); paintBar(); if (view === 'cart') paintCart(); }
  });
})();
