const API_BASE_URL = "https://o-market-8eu1.onrender.com";
const TOKEN_STORAGE_KEY = "omarket_staff_token";

let staffToken = sessionStorage.getItem(TOKEN_STORAGE_KEY) || "";
let uploadedProductImageData = null;
let uploadedBannerImageData = null;
let categoriesCache = [];

const els = {
  alertBox: document.getElementById("admin-alert"),
  gatePanel: document.getElementById("gate-panel"),
  workspacePanel: document.getElementById("workspace-panel"),
  unlockForm: document.getElementById("unlock-form"),
  tokenInput: document.getElementById("admin-token-input"),
  lockBtn: document.getElementById("admin-lock-btn"),
  createProductForm: document.getElementById("create-product-form"),
  prodCategory: document.getElementById("prod-category"),
  prodUnitLabel: document.getElementById("prod-unit-label"),
  prodUnitStep: document.getElementById("prod-unit-step"),
  prodDescription: document.getElementById("prod-description"),
  prodImageFile: document.getElementById("prod-image-file"),
  prodImagePreview: document.getElementById("prod-image-preview"),
  createCategoryForm: document.getElementById("create-category-form"),
  catName: document.getElementById("cat-name"),
  categoriesList: document.getElementById("admin-categories-list"),
  createBannerForm: document.getElementById("create-banner-form"),
  bannerImageFile: document.getElementById("banner-image-file"),
  bannerImagePreview: document.getElementById("banner-image-preview"),
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

function compressImageToBase64(file, maxWidth = 720, quality = 0.78) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const scale = img.width > maxWidth ? maxWidth / img.width : 1;
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.onerror = reject;
      img.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

els.prodImageFile.addEventListener("change", async (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) {
    uploadedProductImageData = null;
    els.prodImagePreview.classList.add("hidden");
    return;
  }
  try {
    uploadedProductImageData = await compressImageToBase64(file);
    els.prodImagePreview.src = uploadedProductImageData;
    els.prodImagePreview.classList.remove("hidden");
  } catch {
    notify("Impossible de lire l'image sélectionnée.", "error");
  }
});

els.bannerImageFile.addEventListener("change", async (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) {
    uploadedBannerImageData = null;
    els.bannerImagePreview.classList.add("hidden");
    return;
  }
  try {
    uploadedBannerImageData = await compressImageToBase64(file, 960, 0.8);
    els.bannerImagePreview.src = uploadedBannerImageData;
    els.bannerImagePreview.classList.remove("hidden");
  } catch {
    notify("Impossible de lire l'image de bannière.", "error");
  }
});

function renderCategoriesSelectAndList() {
  if (els.prodCategory) {
    const currentVal = els.prodCategory.value;
    els.prodCategory.innerHTML = `<option value="">— Sans catégorie —</option>`;
    categoriesCache.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      els.prodCategory.appendChild(opt);
    });
    if (currentVal) {
      els.prodCategory.value = currentVal;
    }
  }

  if (els.categoriesList) {
    els.categoriesList.innerHTML = "";
    if (!categoriesCache.length) {
      els.categoriesList.innerHTML = `<p class="empty-state">Aucune catégorie enregistrée.</p>`;
      return;
    }
    categoriesCache.forEach((c) => {
      const row = document.createElement("div");
      row.className = "cart-row";
      row.innerHTML = `
        <div>
          <strong>#${c.id} — ${c.name}</strong>
          ${c.slug ? `<div class="hint">/${c.slug}</div>` : ""}
        </div>
      `;
      els.categoriesList.appendChild(row);
    });
  }
}

async function loadCategoriesForSelect() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/categories`);
    if (!res.ok) return;
    const cats = await res.json();
    categoriesCache = Array.isArray(cats) ? cats : [];
    renderCategoriesSelectAndList();
  } catch {
    // Garde le cache actuel en cas d'erreur réseau
  }
}

els.createCategoryForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const cleanName = els.catName.value.trim();
  if (!cleanName) return;

  const res = await fetch(`${API_BASE_URL}/api/categories`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ name: cleanName })
  });

  if (res.ok) {
    const created = await res.json();
    e.target.reset();
    notify(`Catégorie « ${created.name} » créée.`);
    await loadCategoriesForSelect();
    if (els.prodCategory && created.id != null) {
      els.prodCategory.value = String(created.id);
    }
    loadCatalog();
  } else {
    const err = await res.json().catch(() => ({}));
    notify(err.detail || "Erreur lors de la création de la catégorie.", "error");
  }
});

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
  await Promise.all([loadCategoriesForSelect(), loadCatalog(), loadOrders(), loadUsers()]);
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
    category_id: els.prodCategory.value ? Number(els.prodCategory.value) : null,
    name: document.getElementById("prod-name").value.trim(),
    description: els.prodDescription.value.trim() || null,
    price: Number(document.getElementById("prod-price").value),
    unit_label: els.prodUnitLabel.value,
    unit_step: Number(els.prodUnitStep.value || 1),
    stock: Number(document.getElementById("prod-stock").value),
    image_url: uploadedProductImageData,
    is_sponsored: document.getElementById("prod-sponsored").checked
  };

  const res = await fetch(`${API_BASE_URL}/api/products`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    e.target.reset();
    uploadedProductImageData = null;
    els.prodImagePreview.classList.add("hidden");
    notify("Produit et image enregistrés en base.");
    loadCatalog();
  } else {
    notify("Erreur lors de l'ajout du produit.", "error");
  }
});

els.createBannerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!uploadedBannerImageData) {
    notify("Veuillez sélectionner une image de bannière.", "error");
    return;
  }
  const payload = {
    title: document.getElementById("banner-title").value.trim() || null,
    image_url: uploadedBannerImageData,
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
    uploadedBannerImageData = null;
    els.bannerImagePreview.classList.add("hidden");
    notify("Bannière enregistrée en base.");
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

  const catMap = new Map(categoriesCache.map((c) => [String(c.id), c.name]));

  products.forEach((p) => {
    const unitText = p.unit_label || "unité";
    const catLabel =
      p.category_id != null && catMap.has(String(p.category_id))
        ? catMap.get(String(p.category_id))
        : "Sans catégorie";
    const row = document.createElement("div");
    row.className = "order-card";
    row.innerHTML = `
      <div class="order-top">
        <div style="display:flex; gap:10px; align-items:center;">
          ${p.image_url ? `<img src="${p.image_url}" alt="${p.name}" style="width:48px; height:48px; border-radius:8px; object-fit:cover;" />` : ""}
          <div>
            <strong>#${p.id} — ${p.name}</strong>
            <div class="hint">Rayon : ${catLabel} • Unité : ${unitText} (pas ${p.unit_step ?? 1})${p.description ? ` — ${p.description}` : ""}</div>
          </div>
        </div>
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
      .map((i) => `Produit #${i.product_id ?? "?"} ×${i.quantity} ${i.unit_label || ""} (${i.unit_price} FCFA)`)
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
      <div class="hint">Adresse : ${o.delivery_address} (${o.delivery_zone || "standard"}) — Repère : ${o.landmark || "-"}</div>
      <div class="hint">Détail : Articles ${Number(o.items_subtotal || 0).toLocaleString("fr-FR")} FCFA + Livraison ${Number(o.delivery_fee || 0).toLocaleString("fr-FR")} FCFA + Frais ${Number(o.service_fee || 100).toLocaleString("fr-FR")} FCFA</div>
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