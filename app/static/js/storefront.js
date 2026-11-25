(function () {
  "use strict";
  const KEY = "storefront_cart_v1";
  const WISH_KEY = "storefront_wishlist_v1";
  const money = value => new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(Number(value) || 0);
  const readCart = () => {
    try {
      const value = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(value) ? value : [];
    } catch (_) { return []; }
  };
  const drawer = () => document.getElementById("store-cart-drawer");
  const readWishlist = () => {
    try { const value = JSON.parse(localStorage.getItem(WISH_KEY) || "[]"); return Array.isArray(value) ? value.filter(item => item && item.id != null) : []; }
    catch (_) { return []; }
  };
  function productSnapshot(card) {
    const image = card.querySelector(".product-photo img, .product-detail-main-image img");
    return { id:String(card.dataset.productId), slug:card.dataset.productSlug || "", name:card.dataset.productName || "Product",
      price:Number(card.dataset.productPrice) || 0, description:card.dataset.productDescription || "",
      category:card.dataset.categoryName || card.dataset.productCategory || "", image:image ? image.currentSrc || image.src : "",
      url:card.querySelector(".product-card-image-link")?.href || (card.dataset.productSlug ? "/product/" + encodeURIComponent(card.dataset.productSlug) : "") };
  }
  function updateWishlist(items) {
    const ids = new Set(items.map(item => String(item.id)));
    document.querySelectorAll("[data-wishlist-count]").forEach(el => { el.textContent = items.length; });
    document.querySelectorAll("[data-wishlist-tab-count]").forEach(el => { el.textContent = items.length; });
    document.querySelectorAll("[data-product-card]").forEach(card => {
      const button = card.querySelector("[data-wishlist-toggle]");
      if (!button) return;
      const saved = ids.has(String(card.dataset.productId));
      button.classList.toggle("is-saved", saved);
      button.setAttribute("aria-pressed", saved ? "true" : "false");
      button.setAttribute("aria-label", (saved ? "Remove " : "Save ") + (card.dataset.productName || "product") + (saved ? " from wishlist" : " to wishlist"));
      if (button.querySelector("span")) button.querySelector("span").textContent = saved ? "♥" : "♡";
      else button.textContent = saved ? "♥" : "♡";
    });
  }
  function createWishlistCard(item) {
    const card = document.createElement("article");
    card.className = "product-card luxury-product-card";
    card.dataset.productCard = ""; card.dataset.productId = String(item.id); card.dataset.productSlug = item.slug || "";
    card.dataset.productName = item.name || "Product"; card.dataset.productPrice = String(item.price || 0);
    card.dataset.productDescription = item.description || ""; card.dataset.productCategory = item.category || "";
    const photo = document.createElement("div"); photo.className = "product-photo";
    const link = document.createElement("a"); link.className = "product-card-image-link";
    link.href = item.url || (item.slug ? "/product/" + encodeURIComponent(item.slug) : "/collection");
    if (item.image) { const img = document.createElement("img"); img.src = item.image; img.alt = item.name || "Saved product"; img.loading = "lazy"; img.decoding = "async"; link.append(img); }
    else { const placeholder = document.createElement("div"); placeholder.className = "electronics-placeholder"; placeholder.textContent = "Photo coming soon"; link.append(placeholder); }
    const remove = document.createElement("button"); remove.type = "button"; remove.className = "product-favourite wishlist-toggle is-saved";
    remove.dataset.wishlistToggle = ""; remove.setAttribute("aria-pressed", "true"); remove.setAttribute("aria-label", "Remove " + item.name + " from wishlist"); remove.textContent = "♥";
    photo.append(link, remove);
    const info = document.createElement("div"); info.className = "luxury-product-info";
    const titleLink = document.createElement("a"); titleLink.className = "product-card-title-link"; titleLink.href = link.href;
    const title = document.createElement("h3"); title.textContent = item.name || "Product"; titleLink.append(title);
    const price = document.createElement("p"); price.className = "luxury-price"; price.textContent = money(item.price);
    const add = document.createElement("button"); add.type = "button"; add.className = "product-whatsapp-button add-to-cart-button"; add.dataset.addToCart = ""; add.textContent = "Add to Cart";
    info.append(titleLink, price, add); card.append(photo, info);
    return card;
  }
  function renderWishlistPage(items) {
    const grid = document.querySelector("[data-wishlist-grid]");
    if (!grid) return;
    const empty = document.querySelector("[data-wishlist-empty]");
    grid.replaceChildren();
    if (empty) empty.hidden = items.length !== 0;
    items.forEach(item => grid.append(createWishlistCard(item)));
    updateWishlist(items); renderProductButtons(readCart());
  }
  function renderWishlistDrawer() {
    const grid = document.querySelector("[data-wishlist-drawer-items]");
    if (!grid) return;
    const items = readWishlist(), empty = document.querySelector("[data-wishlist-drawer-empty]");
    grid.replaceChildren();
    items.forEach(item => grid.append(createWishlistCard(item)));
    if (empty) empty.hidden = items.length > 0;
    const count = document.querySelector("[data-wishlist-drawer-count]");
    if (count) count.textContent = "(" + items.length + ")";
    document.querySelectorAll("[data-wishlist-tab-count]").forEach(el => { el.textContent = items.length; });
    renderProductButtons(readCart());
  }
  function openWishlistDrawer() {
    const cartPanel = drawer();
    if (cartPanel && !cartPanel.hidden) { cartPanel.hidden = true; cartPanel.setAttribute("aria-hidden", "true"); }
    const cartOverlay = document.querySelector("[data-cart-overlay]"); if (cartOverlay) cartOverlay.hidden = true;
    document.body.classList.remove("cart-is-open");
    const panel = document.querySelector("[data-wishlist-drawer]");
    const overlay = document.querySelector("[data-wishlist-overlay]");
    if (!panel) return;
    renderWishlistDrawer();
    panel.hidden = false; panel.setAttribute("aria-hidden", "false");
    const trigger = document.querySelector("[data-wishlist-open]");
    if (trigger) trigger.setAttribute("aria-expanded", "true");
    if (overlay) overlay.hidden = false;
    document.body.classList.add("wishlist-is-open");
    const close = panel.querySelector("[data-wishlist-close]");
    if (close) close.focus();
  }
  function closeWishlistDrawer() {
    const panel = document.querySelector("[data-wishlist-drawer]");
    const overlay = document.querySelector("[data-wishlist-overlay]");
    if (!panel) return;
    panel.hidden = true; panel.setAttribute("aria-hidden", "true");
    if (overlay) overlay.hidden = true;
    document.body.classList.remove("wishlist-is-open");
    const trigger = document.querySelector("[data-wishlist-open]");
    if (trigger) { trigger.setAttribute("aria-expanded", "false"); trigger.focus(); }
  }
  function toggleWishlist(button) {
    const card = button.closest("[data-product-card]");
    if (!card) return;
    const item = productSnapshot(card), items = readWishlist();
    const exists = items.some(entry => String(entry.id) === item.id);
    const next = exists ? items.filter(entry => String(entry.id) !== item.id) : items.concat(item);
    const unique = Array.from(new Map(next.map(entry => [String(entry.id), entry])).values());
    localStorage.setItem(WISH_KEY, JSON.stringify(unique)); updateWishlist(unique); renderWishlistPage(unique); renderWishlistDrawer();
    button.classList.remove("wishlist-pop"); void button.offsetWidth; button.classList.add("wishlist-pop");
  }
  const saveCart = cart => {
    localStorage.setItem(KEY, JSON.stringify(cart));
    updateCount(cart);
    renderCart();
    renderProductButtons(cart);
  };
  function updateCount(cart) {
    const count = cart.length;
    document.querySelectorAll("[data-cart-count]").forEach(el => { el.textContent = count; });
    document.querySelectorAll("[data-cart-drawer-count]").forEach(el => { el.textContent = "(" + count + ")"; });
    document.querySelectorAll("[data-cart-tab-count]").forEach(el => { el.textContent = count; });
    document.querySelectorAll("[data-wishlist-tab-count]").forEach(el => { el.textContent = readWishlist().length; });
  }
  function renderProductButtons(cart) {
    const ids = new Set(cart.map(item => String(item.id)));
    document.querySelectorAll("[data-product-card]").forEach(card => {
      const button = card.querySelector("[data-add-to-cart]");
      if (!button) return;
      const added = ids.has(String(card.dataset.productId));
      button.textContent = added ? "Remove from cart" : "Add to cart";
      button.classList.toggle("is-added", added);
      button.setAttribute("aria-pressed", added ? "true" : "false");
    });
  }

  function normalizeFilterValue(value) {
    return String(value || "").trim().toLocaleLowerCase().replace(/\s+/g, " ");
  }
  function applyCollectionFilters(form) {
    const grid = document.querySelector("[data-collection-products]");
    if (!grid) return;
    const categorySelect = form.querySelector("[data-filter-category]");
    const storageSelect = form.querySelector("[data-filter-storage]");
    const colourSelect = form.querySelector("[data-filter-colour]");
    const selectedCategory = categorySelect && categorySelect.selectedOptions[0]
      ? normalizeFilterValue(categorySelect.selectedOptions[0].dataset.categoryName)
      : "";
    const selectedStorage = normalizeFilterValue(storageSelect && storageSelect.value);
    const selectedColour = normalizeFilterValue(colourSelect && colourSelect.value);
    const cards = Array.from(grid.querySelectorAll("[data-product-card]"));
    let visible = 0;
    cards.forEach(card => {
      const categoryMatch = !selectedCategory || normalizeFilterValue(card.dataset.categoryName) === selectedCategory;
      const storages = String(card.dataset.productStorages || "").split("|").map(normalizeFilterValue);
      const colours = String(card.dataset.productColours || "").split("|").map(normalizeFilterValue);
      const storageMatch = !selectedStorage || storages.includes(selectedStorage);
      const colourMatch = !selectedColour || colours.includes(selectedColour);
      const show = categoryMatch && storageMatch && colourMatch;
      card.hidden = !show;
      if (show) visible += 1;
    });
    const count = form.parentElement.querySelector("[data-filter-result-count]");
    if (count) count.textContent = visible + (visible === 1 ? " device" : " devices");
    const empty = grid.querySelector("[data-filter-empty]");
    if (empty) empty.hidden = visible !== 0;
  }
  function openCart() {
    const wishlistPanel = document.querySelector("[data-wishlist-drawer]");
    if (wishlistPanel && !wishlistPanel.hidden) { wishlistPanel.hidden = true; wishlistPanel.setAttribute("aria-hidden", "true"); }
    const wishlistOverlay = document.querySelector("[data-wishlist-overlay]"); if (wishlistOverlay) wishlistOverlay.hidden = true;
    document.body.classList.remove("wishlist-is-open");
    const panel = drawer();
    if (!panel) return;
    const trigger = document.querySelector("[data-cart-open]");
    const overlay = document.querySelector("[data-cart-overlay]");
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    if (overlay) overlay.hidden = false;
    document.body.classList.add("cart-is-open");
    if (trigger) trigger.setAttribute("aria-expanded", "true");
    renderCart();
    const close = panel.querySelector("[data-cart-close]");
    if (close) close.focus();
  }
  function closeCart() {
    const panel = drawer();
    if (!panel) return;
    panel.hidden = true;
    panel.setAttribute("aria-hidden", "true");
    const overlay = document.querySelector("[data-cart-overlay]");
    if (overlay) overlay.hidden = true;
    document.body.classList.remove("cart-is-open");
    const trigger = document.querySelector("[data-cart-open]");
    if (trigger) { trigger.setAttribute("aria-expanded", "false"); trigger.focus(); }
  }
  function toggleCart(button) {
    const card = button.closest("[data-product-card]");
    if (!card) return;
    const id = String(card.dataset.productId);
    const cart = readCart();
    if (cart.some(item => String(item.id) === id)) {
      saveCart(cart.filter(item => String(item.id) !== id));
      return;
    }
    const image = card.querySelector(".product-photo img, .product-detail-main-image img");
    cart.push({
      id,
      name: card.dataset.productName,
      price: Number(card.dataset.productPrice),
      description: card.dataset.productDescription || "",
      image: image ? image.src : "",
      quantity: 1
    });
    saveCart(cart);
  }
  function renderCart() {
    const root = document.getElementById("cart-items");
    if (!root) return;
    const cart = readCart();
    const empty = document.getElementById("cart-empty");
    const summary = document.getElementById("cart-summary");
    root.replaceChildren();
    if (!cart.length) {
      if (empty) empty.hidden = false;
      if (summary) summary.hidden = true;
      return;
    }
    if (empty) empty.hidden = true;
    if (summary) summary.hidden = false;
    cart.forEach(item => {
      const row = document.createElement("article");
      row.className = "cart-row";
      const image = document.createElement(item.image ? "img" : "div");
      if (item.image) { image.src = item.image; image.alt = item.name; image.loading = "lazy"; }
      else image.className = "cart-image-placeholder";
      const info = document.createElement("div");
      info.className = "cart-item-info";
      const name = document.createElement("h3");
      name.textContent = item.name;
      const price = document.createElement("p");
      price.className = "cart-item-price";
      price.textContent = money(item.price);
      const controls = document.createElement("div");
      controls.className = "cart-quantity";
      const decrease = document.createElement("button");
      decrease.type = "button"; decrease.textContent = "−"; decrease.setAttribute("aria-label", "Decrease " + item.name + " quantity");
      decrease.disabled = Number(item.quantity) <= 1;
      decrease.setAttribute("aria-disabled", decrease.disabled ? "true" : "false");
      decrease.addEventListener("click", () => changeQuantity(item.id, -1));
      const quantity = document.createElement("span");
      quantity.textContent = item.quantity;
      const increase = document.createElement("button");
      increase.type = "button"; increase.textContent = "+"; increase.setAttribute("aria-label", "Increase " + item.name + " quantity");
      increase.addEventListener("click", () => changeQuantity(item.id, 1));
      const remove = document.createElement("button");
      remove.type = "button"; remove.className = "cart-remove"; remove.textContent = "Remove";
      remove.addEventListener("click", () => removeItem(item.id));
      controls.append(decrease, quantity, increase, remove);
      info.append(name, price, controls);
      const total = document.createElement("strong");
      total.className = "cart-line-total";
      total.textContent = money(item.price * item.quantity);
      row.append(image, info, total);
      root.appendChild(row);
    });
    const subtotal = document.getElementById("cart-subtotal");
    if (subtotal) subtotal.textContent = money(cart.reduce((sum, item) => sum + item.price * item.quantity, 0));
  }
  function changeQuantity(id, delta) {
    const cart = readCart();
    const item = cart.find(entry => String(entry.id) === String(id));
    if (!item) return;
    const currentQuantity = Math.max(1, Number(item.quantity) || 1);
    item.quantity = Math.max(1, currentQuantity + delta);
    saveCart(cart);
  }
  function removeItem(id) { saveCart(readCart().filter(item => String(item.id) !== String(id))); }
  function clearWishlist() { localStorage.setItem(WISH_KEY, "[]"); updateWishlist([]); renderWishlistPage([]); renderWishlistDrawer(); }
  function moveWishlistToCart() {
    const saved = readWishlist(); if (!saved.length) return;
    const cart = readCart(); const byId = new Map(cart.map(item => [String(item.id), item]));
    saved.forEach(item => { const id = String(item.id); if (!byId.has(id)) byId.set(id, { id, name:item.name || "Product", price:Number(item.price)||0, description:item.description||"", image:item.image||"", quantity:1 }); });
    saveCart(Array.from(byId.values())); clearWishlist(); openCart();
  }
  function checkout() {
    const cart = readCart();
    const phone = (window.STORE_WHATSAPP || "").replace(/[^0-9]/g, "");
    if (!phone) { window.alert("This store has not added a WhatsApp number yet."); return; }
    if (!cart.length) return;
    const lines = cart.map(item => "- " + item.name + " × " + item.quantity + " — " + money(item.price * item.quantity));
    const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const message = "Hello " + (window.STORE_NAME || "") + ", I would like to order:\n" + lines.join("\n") + "\n\nSubtotal: " + money(total) + "\nPlease confirm availability.";
    window.open("https://wa.me/" + phone + "?text=" + encodeURIComponent(message), "_blank", "noopener");
  }
  document.addEventListener("DOMContentLoaded", () => {
    // Track visits after rendering so analytics never delays page navigation.
    const visitPayload = JSON.stringify({ path: window.location.pathname });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/track-visit", new Blob([visitPayload], { type: "application/json" }));
    } else {
      fetch("/track-visit", { method: "POST", headers: { "Content-Type": "application/json" },
        body: visitPayload, keepalive: true, credentials: "same-origin" }).catch(() => {});
    }

    const cart = readCart();
    const wishlist = readWishlist();
    updateWishlist(wishlist); renderWishlistPage(wishlist);
    updateCount(cart);
    renderCart();
    renderProductButtons(cart);
    refreshPageContent();
    document.addEventListener("click", event => {
      const galleryButton = event.target.closest("[data-gallery-image]");
      if (galleryButton) {
        const main = document.querySelector("[data-gallery-main]"), img = main && main.querySelector("img");
        if (img) { img.src = galleryButton.dataset.galleryImage; img.alt = galleryButton.dataset.galleryAlt || "Product photo"; }
        document.querySelectorAll("[data-gallery-image]").forEach(item => item.classList.toggle("is-active", item === galleryButton));
        return;
      }
      const wishButton = event.target.closest("[data-wishlist-toggle]");
      if (wishButton) { event.preventDefault(); toggleWishlist(wishButton); return; }
      const wishlistTrigger = event.target.closest("[data-wishlist-open]");
      if (wishlistTrigger) { event.preventDefault(); openWishlistDrawer(); return; }
      const button = event.target.closest("[data-add-to-cart]");
      if (button) { event.preventDefault(); toggleCart(button); return; }
      if (event.target.closest("[data-drawer-tab=\"wishlist\"]")) { event.preventDefault(); openWishlistDrawer(); return; }
      if (event.target.closest("[data-drawer-tab=\"cart\"]")) { event.preventDefault(); openCart(); return; }
      if (event.target.closest("[data-wishlist-clear]")) { clearWishlist(); return; }
      if (event.target.closest("[data-wishlist-move]")) { moveWishlistToCart(); return; }
      if (event.target.closest("[data-cart-clear]")) { saveCart([]); }
    });
    document.querySelectorAll("[data-cart-open]").forEach(button => button.addEventListener("click", openCart));
    document.querySelectorAll("[data-wishlist-close]").forEach(button => button.addEventListener("click", closeWishlistDrawer));
    const wishlistOverlay = document.querySelector("[data-wishlist-overlay]");
    if (wishlistOverlay) wishlistOverlay.addEventListener("click", closeWishlistDrawer);
    document.querySelectorAll("[data-cart-close]").forEach(button => button.addEventListener("click", closeCart));
    const overlay = document.querySelector("[data-cart-overlay]");
    if (overlay) overlay.addEventListener("click", closeCart);
    document.addEventListener("change", event => {
      const form = event.target.closest("[data-collection-filters]");
      if (!form) return;
      if (event.target.matches("[data-filter-category]")) {
        const option = event.target.selectedOptions[0];
        navigateTo(option && option.value && option.dataset.categoryUrl ? option.dataset.categoryUrl : "/collection");
        return;
      }
      applyCollectionFilters(form);
    });
    document.addEventListener("reset", event => {
      const form = event.target.closest("[data-collection-filters]");
      if (form) window.requestAnimationFrame(() => applyCollectionFilters(form));
    });
    document.addEventListener("submit", event => {
      if (event.target.matches("[data-collection-filters]")) event.preventDefault();
    });
    document.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      if (drawer() && !drawer().hidden) closeCart();
      const wishlistPanel = document.querySelector("[data-wishlist-drawer]");
      if (wishlistPanel && !wishlistPanel.hidden) closeWishlistDrawer();
    });
    const checkoutButton = document.getElementById("whatsapp-checkout");
    if (checkoutButton) checkoutButton.addEventListener("click", checkout);
    window.addEventListener("storage", event => {
      if (event.key === KEY) { const latest = readCart(); updateCount(latest); renderCart(); renderProductButtons(latest); }
      if (event.key === WISH_KEY) { const latest = readWishlist(); updateWishlist(latest); renderWishlistPage(latest); renderWishlistDrawer(); }
    });

  });

  const pageCache = new Map();
  const pendingPages = new Map();
  let activeNavigation = 0;
  function refreshPageContent() {
    const cart = readCart(), wishlist = readWishlist();
    updateWishlist(wishlist); renderWishlistPage(wishlist);
    updateCount(cart); renderCart(); renderProductButtons(cart);
    const form = document.querySelector("[data-collection-filters]");
    if (form) applyCollectionFilters(form);
  }
  async function fetchPage(url) {
    const key = new URL(url, location.href).href;
    if (pageCache.has(key)) return pageCache.get(key);
    if (pendingPages.has(key)) return pendingPages.get(key);
    const request = fetch(key, { credentials: "same-origin", headers: { "X-Requested-With": "fetch" } })
      .then(response => { if (!response.ok) throw new Error("Navigation request failed"); return response.text(); })
      .then(html => { pageCache.set(key, html); if (pageCache.storage > 8) pageCache.delete(pageCache.keys().next().value); return html; })
      .finally(() => pendingPages.delete(key));
    pendingPages.set(key, request);
    return request;
  }
  async function navigateTo(url, addHistory = true) {
    const target = new URL(url, location.href);
    if (target.origin !== location.origin) { location.assign(target.href); return; }
    if (target.href === location.href && addHistory) return;
    const token = ++activeNavigation;
    document.documentElement.classList.add("page-is-loading");
    try {
      const html = await fetchPage(target.href);
      if (token !== activeNavigation) return;
      const parsed = new DOMParser().parseFromString(html, "text/html");
      const nextMain = parsed.querySelector("main"), currentMain = document.querySelector("main");
      if (!nextMain || !currentMain) { location.assign(target.href); return; }
      currentMain.replaceWith(nextMain);
      document.title = parsed.title || document.title;
      const nextDescription = parsed.querySelector('meta[name="description"]');
      const description = document.querySelector('meta[name="description"]');
      if (nextDescription && description) description.content = nextDescription.content;
      if (addHistory) history.pushState({}, "", target.href);
      refreshPageContent();
      window.scrollTo(0, 0);
    } catch (_) { location.assign(target.href); }
    finally { if (token === activeNavigation) document.documentElement.classList.remove("page-is-loading"); }
  }
  document.addEventListener("click", event => {
    const link = event.target.closest("a[href]");
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if ((link.target && link.target !== "_self") || link.hasAttribute("download")) return;
    const target = new URL(link.href, location.href);
    if (target.origin !== location.origin || target.pathname.startsWith("/media/") || (target.hash && target.pathname === location.pathname) || !/^https?:$/.test(target.protocol)) return;
    event.preventDefault(); navigateTo(target.href);
  });
  const warmPage = link => {
    if (!link) return;
    const target = new URL(link.href, location.href);
    if (target.origin === location.origin && !target.pathname.startsWith("/media/") && target.href !== location.href) fetchPage(target.href).catch(() => {});
  };
  document.addEventListener("pointerover", event => warmPage(event.target.closest("a[href]")), { passive: true });
  document.addEventListener("touchstart", event => warmPage(event.target.closest("a[href]")), { passive: true });
  window.addEventListener("popstate", () => navigateTo(location.href, false));
})();