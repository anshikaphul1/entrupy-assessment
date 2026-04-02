const API_KEY = "test_key";
const headers = { "x-api-key": API_KEY };

async function fetchDashboard() {
    try {
        const res = await fetch("/api/analytics", { headers });
        const data = await res.json();
        
        document.getElementById("stat-total").textContent = data.total_products;
        
        const sourcesDiv = document.getElementById("stat-sources");
        sourcesDiv.innerHTML = "";
        for (const [source, count] of Object.entries(data.totals_by_source)) {
            sourcesDiv.innerHTML += `<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem">
                <span style="text-transform: capitalize;">${source}</span>
                <span style="color: var(--text-main); font-weight: 500;">${count}</span>
            </div>`;
        }

        const avgDiv = document.getElementById("stat-avg");
        avgDiv.innerHTML = "";
        for (const [brand, avg] of Object.entries(data.avg_price_by_brand)) {
             avgDiv.innerHTML += `<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem">
                <span>${brand}</span>
                <span style="color: var(--text-main); font-weight: 500;">$${parseFloat(avg).toFixed(2)}</span>
            </div>`;
        }

    } catch (e) {
        console.error("Failed to fetch dashboard stats", e);
    }
}

async function fetchProducts(source_filter = "") {
    const listDiv = document.getElementById("product-list");
    listDiv.innerHTML = `<p style="color: var(--text-muted);">Loading products...</p>`;
    try {
        let url = "/api/products";
        if (source_filter) {
            url += `?source=${source_filter}`;
        }
        const res = await fetch(url, { headers });
        const products = await res.json();

        listDiv.innerHTML = "";
        if (products.length === 0) {
            listDiv.innerHTML = `<p style="color: var(--text-muted);">No products found.</p>`;
            return;
        }

        products.forEach(p => {
            const card = document.createElement("div");
            card.className = "product-card";
            card.onclick = () => showProductDetails(p.id);
            
            // Just display the latest price we have
            const price = p.price_history.length > 0 ? p.price_history[0].price : 0;

            card.innerHTML = `
                <div class="product-brand">${p.brand || 'Unknown'}</div>
                <div class="product-model" title="${p.model}">${p.model || 'Unknown Model'}</div>
                <div class="product-price">$${parseFloat(price).toFixed(2)} ${p.currency}</div>
                <div class="product-source">${p.source}</div>
            `;
            listDiv.appendChild(card);
        });

    } catch (e) {
        console.error("Failed to fetch products", e);
    }
}

async function showProductDetails(id) {
    const modal = document.getElementById("detail-modal");
    const modalBody = document.getElementById("modal-body");
    
    modal.style.display = "flex";
    modalBody.innerHTML = "<p>Loading...</p>";

    try {
        const res = await fetch(`/api/products/${id}`, { headers });
        const p = await res.json();
        
        let historyHtml = p.price_history.map(h => `
            <tr>
                <td>$${parseFloat(h.price).toFixed(2)}</td>
                <td>${new Date(h.scraped_at).toLocaleString()}</td>
            </tr>
        `).join("");

        modalBody.innerHTML = `
            <div style="margin-bottom: 2rem;">
                <h2 style="margin: 0 0 0.5rem 0;">${p.brand || 'Unknown Brand'} - ${p.model || 'Unknown'}</h2>
                <a href="${p.url}" target="_blank" style="color: var(--primary-color); text-decoration: none;">View Original Listing &nearr;</a>
            </div>
            
            <div style="background: var(--bg-color); padding: 1rem; border-radius: 0.5rem; margin-bottom: 2rem;">
                <h3 style="margin: 0 0 1rem 0; font-size: 1rem; color: var(--text-muted);">Price History</h3>
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Price (${p.currency})</th>
                            <th>Recorded At</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${historyHtml}
                    </tbody>
                </table>
            </div>
        `;
    } catch (e) {
        modalBody.innerHTML = "<p>Error loading product details.</p>";
    }
}

document.getElementById("close-modal").onclick = () => {
    document.getElementById("detail-modal").style.display = "none";
};

document.getElementById("refresh-btn").onclick = async () => {
    const btn = document.getElementById("refresh-btn");
    btn.disabled = true;
    btn.textContent = "Triggering...";

    try {
        const res = await fetch("/api/refresh", { method: 'POST', headers });
        if (res.ok) {
            btn.textContent = "Refresh Triggered!";
            setTimeout(() => {
                btn.disabled = false;
                btn.textContent = "Trigger Data Refresh";
                // Optionally reload data after a small delay to let fetch finish
                setTimeout(() => {
                    fetchDashboard();
                    fetchProducts(document.getElementById("source-filter").value);
                }, 1000);
            }, 2000);
        }
    } catch (e) {
        btn.disabled = false;
        btn.textContent = "Trigger Data Refresh";
        alert("Failed to trigger refresh.");
    }
};

document.getElementById("source-filter").onchange = (e) => {
    fetchProducts(e.target.value);
};

// Initial Load
fetchDashboard();
fetchProducts();
