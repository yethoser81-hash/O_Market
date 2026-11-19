const API_BASE_URL = "https://o-market-8eu1.onrender.com";

const state = {
  user: JSON.parse(localStorage.getItem("omarket_user") || "null"),
  products: [],
  cart: JSON.parse(localStorage.getItem("omarket_cart") || "[]")
};

const els = {
  apiStatus: document.getElementById("api-status"),
  openAuthBtn: document.getElementById("open-auth-btn"),
  closeAuthBtn: document.getElementById("close-auth-btn"),
  authModal: document.getElementById("auth-modal"),
  authForm: document.getElementById("auth-form"),
  authPhone: document.getElementById("auth-phone"),
  authName: document.getElementById("auth-name"),
  userChip: document.getElementById("user-chip"),
  userLabel: document.getElementById("user-label"),
  logoutBtn: document.getElementById("logout-btn"),
  globalAlert: document.getElementById("global-alert"),
  productsList: document.getElementById("products-list"),
  refreshProductsBtn: document.getElementById("refresh-products-btn"),
  cartItems: document.getElementById("cart-items"),
  cartTotal: document.getElementById("cart-total"),
  orderForm: document.getElementById("order-form"),
  deliveryAddress: document.getElementById("delivery-address"),
  deliveryLandmark: document.getElementById("delivery-landmark"),
  smartListForm: document.getElementById("smart-list-form"),
  smartListInput: document.getElementById("smart-list-input"),
  smartListResult: document.getElementById("smart-list-result")
};

function formatFcfa(amount) {
  return `${Number(amount || 0).toLocaleString("fr-FR")} FCFA`;
}

function showAlert(message, type = "success") {
  els.globalAlert.textContent = message;
  els.globalAlert.className = `alert alert-${type}`;
  els.globalAlert.classList.remove("hidden");
  clearTimeout(showAlert._timer);
  showAlert._timer = setTimeout(() => {
    els.globalAlert.classList.add("hidden");
  }, 5000);
}

function saveCart() {
  localStorage.setItem("omarket_cart", JSON.stringify(state.cart));
  renderCart();
}

function renderAuth() {
  if (state.user) {
    els.openAuthBtn.classList.add("hidden");
    els.userChip.classList.remove("hidden");
    els.userLabel.textContent = state.user.full_name
      ? `${state.user.full_name} (${state.user.phone})`
      : state.user.phone;
  } else {
    els.openAuthBtn.classList.remove("hidden");
    els.userChip.classList.add("hidden");
    els.userLabel.textContent = "";
  }
}

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    els.apiStatus.textContent = "API Connectée";
    els.apiStatus.className = "status-pill status-online";
  } catch {
    els.apiStatus.textContent = "API Hors ligne";
    els.apiStatus.className = "status-pill status-offline";
  }
}

async function loadProducts() {
  els.productsList.innerHTML = `<p class="empty-state">Chargement du catalogue...</p>`;
  try {
    const res = await fetch(`${API_BASE_URL}/api/products`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.products = Array.isArray(data) ? data : [];
    renderProducts();
  } catch (err) {
    els.productsList.innerHTML = `<p class="empty-state">Erreur : ${err.message}</p>`;
  }
}

function renderProducts() {
  if (!state.products.length) {
    els.productsList.innerHTML = `<p class="empty-state">Aucun produit disponible.</p>`;
    return;
  }

  els.productsList.innerHTML = "";
  state.products.forEach((p) => {
    const card = document.createElement("article");
    card.className = "product-card";

    const imgHtml = p.image_url
      ? `<img src="${p.image_url}" alt="${p.name}" loading="lazy" />`
      : "";
    const sponsorHtml = p.is_sponsored
      ? `<span class="badge-sponsored">Promotion</span>`
      : "";

    card.innerHTML = `
      <div>
        ${imgHtml}
        ${sponsorHtml}
        <h3 class="product-title">${p.name}</h3>
        <div class="product-price">${formatFcfa(p.price)}</div>
        <div class="hint">Stock : ${p.stock ?? 0}</div>
      </div>
      <button class="btn btn-primary full-width add-cart-btn" type="button">Ajouter au panier</button>
    `;

    card.querySelector(".add-cart-btn").addEventListener("click", () => {
      addToCart({
        product_id: p.id,
        product_name: p.name,
        unit_price: Number(p.price),
        quantity: 1
      });
    });

    els.productsList.appendChild(card);
  });
}

function addToCart(item) {
  const existing = state.cart.find((c) => c.product_id === item.product_id);
  if (existing) {
    existing.quantity += item.quantity;
  } else {
    state.cart.push({ ...item });
  }
  saveCart();
  showAlert(`${item.product_name} ajouté au panier.`);
}

function removeFromCart(index) {
  state.cart.splice(index, 1);
  saveCart();
}

function renderCart() {
  if (!state.cart.length) {
    els.cartItems.innerHTML = `<p class="empty-state">Aucun article dans le panier.</p>`;
    els.cartTotal.textContent = formatFcfa(0);
    return;
  }

  els.cartItems.innerHTML = "";
  let total = 0;

  state.cart.forEach((item, idx) => {
    const lineTotal = Number(item.unit_price) * Number(item.quantity);
    total += lineTotal;

    const row = document.createElement("div");
    row.className = "cart-row";
    row.innerHTML = `
      <div>
        <strong>${item.product_name}</strong><br />
        <span class="hint">${item.quantity} × ${formatFcfa(item.unit_price)} = ${formatFcfa(lineTotal)}</span>
      </div>
      <button class="btn-link" type="button">Retirer</button>
    `;
    row.querySelector("button").addEventListener("click", () => removeFromCart(idx));
    els.cartItems.appendChild(row);
  });

  els.cartTotal.textContent = formatFcfa(total);
}

els.openAuthBtn.addEventListener("click", () => els.authModal.classList.remove("hidden"));
els.closeAuthBtn.addEventListener("click", () => els.authModal.classList.add("hidden"));

els.authForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    phone: els.authPhone.value.trim(),
    full_name: els.authName.value.trim() || null
  };

  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/login-register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Échec de connexion");

    state.user = data.user || null;
    localStorage.setItem("omarket_user", JSON.stringify(state.user));
    renderAuth();
    els.authModal.classList.add("hidden");
    showAlert(data.message || "Connexion réussie.");
  } catch (err) {
    showAlert(err.message, "error");
  }
});

els.logoutBtn.addEventListener("click", () => {
  state.user = null;
  localStorage.removeItem("omarket_user");
  renderAuth();
  showAlert("Déconnecté.");
});

els.smartListForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const raw_text = els.smartListInput.value.trim();
  if (!raw_text) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/smart-list`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erreur d'analyse");

    const parsedItems = Array.isArray(data.parsed_items) ? data.parsed_items : [];
    els.smartListResult.innerHTML = "";
    els.smartListResult.classList.remove("hidden");

    const heading = document.createElement("p");
    heading.innerHTML = `<strong>${data.message}</strong> — Total estimé : <strong>${formatFcfa(data.total_estimated)}</strong>`;
    els.smartListResult.appendChild(heading);

    parsedItems.forEach((it) => {
      if (!it.product_id) return;
      const line = document.createElement("div");
      line.className = "cart-row";
      line.innerHTML = `
        <span>${it.quantity} × ${it.product_name} (${formatFcfa(it.unit_price)})</span>
        <button class="btn btn-secondary" type="button">Ajouter au panier</button>
      `;
      line.querySelector("button").addEventListener("click", () => {
        addToCart({
          product_id: it.product_id,
          product_name: it.product_name,
          unit_price: Number(it.unit_price || 0),
          quantity: Number(it.quantity || 1)
        });
      });
      els.smartListResult.appendChild(line);
    });
  } catch (err) {
    showAlert(err.message, "error");
  }
});

els.orderForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.cart.length) {
    showAlert("Votre panier est vide.", "error");
    return;
  }

  const payload = {
    user_id: state.user?.id || null,
    delivery_address: els.deliveryAddress.value.trim(),
    landmark: els.deliveryLandmark.value.trim(),
    items: state.cart.map((c) => ({
      product_id: c.product_id,
      product_name: c.product_name,
      quantity: c.quantity
    }))
  };

  try {
    const res = await fetch(`${API_BASE_URL}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erreur commande");

    state.cart = [];
    saveCart();
    els.orderForm.reset();
    showAlert(`Commande #${data.order_id} enregistrée (${formatFcfa(data.total_amount)}).`);
  } catch (err) {
    showAlert(err.message, "error");
  }
});

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

els.refreshProductsBtn.addEventListener("click", loadProducts);

renderAuth();
renderCart();
checkHealth();
loadProducts();