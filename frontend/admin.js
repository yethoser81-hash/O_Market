const API_BASE_URL = "https://o-market-8eu1.onrender.com";
const TOKEN_STORAGE_KEY = "omarket_staff_token";

let staffToken = sessionStorage.getItem(TOKEN_STORAGE_KEY) || "";

const els = {
  alertBox: document.getElementById("admin-alert"),
  gatePanel: document.getElementById("gate-panel"),
  workspacePanel: document.getElementById("workspace-panel"),
  unlockForm: document.getElementById("unlock-form"),
  tokenInput: document.getElementById("admin-token-input"),
  lockBtn: document.getElementById("admin-lock-btn"),
  createProductForm: document.getElementById("create-product-form"),
  createBannerForm: document.getElementById("create-banner-form"),
  reloadCatalogBtn: document.getElementById("reload-catalog-btn"),
  reloadOrdersBtn: document.getElementById("reload-orders-btn"),
  reloadUsersBtn: document.getElementById("reload-users-btn"),
  productsList: document.getElementById("admin-products-list"),
  ordersList: document.getElementById("admin-orders-list"),
  usersList: document.getElementById("admin-users-list")
};

function notify(message, type = "success") {
  els.alertBox.textContent = message;
  els.alertBox.className = `alert alert-${type}`;
  els.alertBox.classList.remove("hidden");
  clearTimeout(notify._t);
  notify._t = setTimeout(() => els.alertBox.classList.add("hidden"), 4500);
}

function authHeaders(extra = {}) {
  return {
    "Content-Type": "application/json",
    "X-Admin-Token": staffToken,
    ...extra
  };
}

function setLockedState(unlocked) {
  if (unlocked) {
    els.gatePanel.classList.add("hidden");
    els.workspacePanel.classList.remove("hidden");
    els.lockBtn.classList.remove("hidden");
  } else {
    els.gatePanel.classList.remove("hidden");
    els.workspacePanel.classList.add("hidden");
    els.lockBtn.classList.add("hidden");
  }
}

async function verifyAndLoad() {
  if (!staffToken) {
    setLockedState(false);
    return;
  }
  const res = await fetch(`${API_BASE_URL}/api/orders`, {
    headers: { "X-Admin-Token": staffToken }
  });
  if (!res.ok) {
    staffToken = "";
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    setLockedState(false);
    notify("Clé d'accès invalide ou expirée.", "error");
    return;
  }
  setLockedState(true);
  await Promise.all([loadCatalog(), loadOrders(), loadUsers()]);
}

els.unlockForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  staffToken = els.tokenInput.value.trim();
  sessionStorage.setItem(TOKEN_STORAGE_KEY, staffToken);
  els.tokenInput.value = "";
  await verifyAndLoad();
});

els.lockBtn.addEventListener("click", () => {
  staffToken = "";
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  setLockedState(false);
  notify("Session verrouillée.");
});

els.createProductForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("prod-name").value.trim(),
    price: Number(document.getElementById("prod-price").value),
    stock: Number(document.getElementById("prod-stock").value),
    image_url: document.getElementById("prod-image").value.trim() || null,
    is_sponsored: document.getElementById("prod-sponsored").checked
  };
  const res = await fetch(`${API_BASE_URL}/api/products`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    e.target.reset();
    notify("Produit ajouté au catalogue.");
    loadCatalog();
  } else {
    notify("Erreur lors de l'ajout du produit.", "error");
  }
});

els.createBannerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    title: document.getElementById("banner-title").value.trim() || null,
    image_url: document.getElementById("banner-image").value.trim(),
    target_url: document.getElementById("banner-target").value.trim() || null,
    is_active: true
  };
  const res = await fetch(`${API_BASE_URL}/api/banners`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    e.target.reset();
    notify("Bannière enregistrée.");
  } else {
    notify("Erreur lors de l'ajout de la bannière.", "error");
  }
});

async function loadCatalog() {
  const res = await fetch(`${API_BASE_URL}/api/products`);
  const products = res.ok ? await res.json() : [];
  els.productsList.innerHTML = "";

  if (!products.length) {
    els.productsList.innerHTML = `<p class="empty-state">Aucun produit en base.</p>`;
    return;
  }

  products.forEach((p) => {
    const row = document.createElement("div");
    row.className = "order-card";
    row.innerHTML = `
      <div class="order-top">
        <strong>#${p.id} — ${p.name}</strong>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <input type="number" id="p-price-${p.id}" value="${p.price}" style="width:110px;" />
          <input type="number" id="p-stock-${p.id}" value="${p.stock}" style="width:85px;" />
          <label style="flex-direction:row; gap:4px; font-size:0.82rem;">
            <input type="checkbox" id="p-spon-${p.id}" ${p.is_sponsored ? "checked" : ""} style="width:auto;" />
            Promo
          </label>
          <button class="btn btn-primary" type="button" data-save="${p.id}">Enregistrer</button>
          <button class="btn btn-secondary" type="button" data-del="${p.id}">Supprimer</button>
        </div>
      </div>
    `;
    row.querySelector(`[data-save="${p.id}"]`).addEventListener("click", () => updateProduct(p.id));
    row.querySelector(`[data-del="${p.id}"]`).addEventListener("click", () => deleteProduct(p.id));
    els.productsList.appendChild(row);
  });
}

async function updateProduct(id) {
  const payload = {
    price: Number(document.getElementById(`p-price-${id}`).value),
    stock: Number(document.getElementById(`p-stock-${id}`).value),
    is_sponsored: document.getElementById(`p-spon-${id}`).checked
  };
  const res = await fetch(`${API_BASE_URL}/api/products/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    notify(`Produit #${id} mis à jour.`);
    loadCatalog();
  } else {
    notify("Mise à jour refusée.", "error");
  }
}

async function deleteProduct(id) {
  const res = await fetch(`${API_BASE_URL}/api/products/${id}`, {
    method: "DELETE",
    headers: { "X-Admin-Token": staffToken }
  });
  if (res.ok) {
    notify(`Produit #${id} supprimé.`);
    loadCatalog();
  } else {
    notify("Suppression refusée.", "error");
  }
}

async function loadOrders() {
  const res = await fetch(`${API_BASE_URL}/api/orders`, {
    headers: { "X-Admin-Token": staffToken }
  });
  const orders = res.ok ? await res.json() : [];
  els.ordersList.innerHTML = "";

  if (!orders.length) {
    els.ordersList.innerHTML = `<p class="empty-state">Aucune commande enregistrée.</p>`;
    return;
  }

  orders.forEach((o) => {
    const itemsSummary = (o.items || [])
      .map((i) => `Produit #${i.product_id ?? "?"} ×${i.quantity} (${i.unit_price} FCFA)`)
      .join(" | ");

    const card = document.createElement("div");
    card.className = "order-card";
    card.innerHTML = `
      <div class="order-top">
        <strong>Commande #${o.id} — ${Number(o.total_amount).toLocaleString("fr-FR")} FCFA</strong>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <select id="o-pay-${o.id}">
            <option value="unpaid" ${o.payment_status === "unpaid" ? "selected" : ""}>unpaid</option>
            <option value="paid" ${o.payment_status === "paid" ? "selected" : ""}>paid</option>
          </select>
          <select id="o-st-${o.id}">
            <option value="pending_payment" ${o.status === "pending_payment" ? "selected" : ""}>pending_payment</option>
            <option value="paid" ${o.status === "paid" ? "selected" : ""}>paid</option>
            <option value="processing" ${o.status === "processing" ? "selected" : ""}>processing</option>
            <option value="out_for_delivery" ${o.status === "out_for_delivery" ? "selected" : ""}>out_for_delivery</option>
            <option value="delivered" ${o.status === "delivered" ? "selected" : ""}>delivered</option>
          </select>
          <button class="btn btn-primary" type="button" data-order-save="${o.id}">Mettre à jour</button>
        </div>
      </div>
      <div class="hint">Adresse : ${o.delivery_address} — Repère : ${o.landmark || "-"}</div>
      <div class="hint">Articles : ${itemsSummary || "-"}</div>
    `;
    card.querySelector(`[data-order-save="${o.id}"]`).addEventListener("click", () => updateOrder(o.id));
    els.ordersList.appendChild(card);
  });
}

async function updateOrder(id) {
  const payload = {
    payment_status: document.getElementById(`o-pay-${id}`).value,
    status: document.getElementById(`o-st-${id}`).value
  };
  const res = await fetch(`${API_BASE_URL}/api/orders/${id}/status`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    notify(`Commande #${id} mise à jour.`);
    loadOrders();
  } else {
    notify("Mise à jour de commande refusée.", "error");
  }
}

async function loadUsers() {
  if (!els.usersList) return;
  const res = await fetch(`${API_BASE_URL}/api/users`, {
    headers: { "X-Admin-Token": staffToken }
  });
  const users = res.ok ? await res.json() : [];
  els.usersList.innerHTML = "";

  if (!users.length) {
    els.usersList.innerHTML = `<p class="empty-state">Aucun utilisateur inscrit.</p>`;
    return;
  }

  users.forEach((u) => {
    const row = document.createElement("div");
    row.className = "order-card";
    row.innerHTML = `
      <div class="order-top">
        <span><strong>#${u.id} — ${u.full_name || "Sans nom"}</strong> (${u.phone})</span>
        <div style="display:flex; gap:8px; align-items:center;">
          <select id="u-role-${u.id}">
            <option value="client" ${u.role === "client" ? "selected" : ""}>client</option>
            <option value="driver" ${u.role === "driver" ? "selected" : ""}>driver (livreur moto)</option>
            <option value="admin" ${u.role === "admin" ? "selected" : ""}>admin</option>
          </select>
          <button class="btn btn-primary" type="button" data-role-save="${u.id}">Appliquer</button>
        </div>
      </div>
    `;
    row.querySelector(`[data-role-save="${u.id}"]`).addEventListener("click", () => updateUserRole(u.id));
    els.usersList.appendChild(row);
  });
}

async function updateUserRole(userId) {
  const role = document.getElementById(`u-role-${userId}`).value;
  const res = await fetch(`${API_BASE_URL}/api/users/${userId}/role`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ role })
  });
  if (res.ok) {
    notify(`Rôle de l'utilisateur #${userId} passé à "${role}".`);
    loadUsers();
  } else {
    notify("Modification du rôle refusée.", "error");
  }
}

els.reloadCatalogBtn.addEventListener("click", loadCatalog);
els.reloadOrdersBtn.addEventListener("click", loadOrders);
if (els.reloadUsersBtn) {
  els.reloadUsersBtn.addEventListener("click", loadUsers);
}

verifyAndLoad();