# Product Price Monitoring System

A real-time scalable system designed to monitor product prices from multiple secondary market e-commerce platforms (Grailed, Fashionphile, 1stdibs). Built iteratively using FastAPI, Async SQLite (via SQLAlchemy), and a Vanilla JS frontend.

---

## 1. How to run it
**Prerequisites:** Python 3.9+ 

1. **Clone the repository and cd into it:**
   ```bash
   git clone <your-repo-url>
   cd "entrupy assignment"
   ```

2. **Set up and activate the virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows:
   .\venv\Scripts\Activate.ps1
   
   # On Unix/macOS:
   source venv/bin/activate
   ```

3. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the API & Frontend Server:**
   ```bash
   uvicorn src.main:app --reload
   ```

5. **Interact:**
   - **Frontend UI**: Open your browser and navigate to `http://localhost:8000/static/index.html`
   - **Swagger/OpenAPI docs**: Navigate to `http://localhost:8000/docs`

6. **Run Automated Tests:**
   ```bash
   pytest tests\
   ```

---

## 2. API Documentation
*All requests require the `x-api-key: test_key` header for authentication.*

### `POST /api/refresh`
Manually triggers a background data fetch that simulates async scraping logic, reading through your datasets utilizing `tenacity` retries.
**Example Request:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/refresh' \
  -H 'accept: application/json' \
  -H 'x-api-key: test_key'
```
**Example Response:**
```json
{
  "message": "Data refresh triggered in the background."
}
```

### `GET /api/products` (optional parameters: `?source=grailed`)
Returns a browsable array of tracked products. Can be filtered by source marketplace.
**Example Request:**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/products?source=grailed' \
  -H 'accept: application/json' \
  -H 'x-api-key: test_key'
```
**Example Response:**
```json
[
  {
    "source": "grailed",
    "external_id": "3dcbbe62-a0c8-4238-8f42-acdb7f0af660",
    "url": "https://www.grailed.com/listings/83672676",
    "brand": "Amiri",
    "model": "Amiri Washed Filigree T-Shirt",
    "currency": "USD",
    "id": 1,
    "price_history": [
      {
        "price": 425.0,
        "scraped_at": "2026-04-02T19:50:35.792Z"
      }
    ]
  }
]
```

### `GET /api/products/{id}`
Fetches individual product details and returns its `price_history`.
**Example Request:**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/products/1' \
  -H 'accept: application/json' \
  -H 'x-api-key: test_key'
```
**Example Response:** *(Same structure as a single product array entry shown above)*

### `GET /api/analytics`
Fetches aggregate statistics indicating how many products exist and averages per brand. Used largely by the dashboard layer.
**Example Request:**
```bash
curl -X 'GET' \
  'http://localhost:8000/api/analytics' \
  -H 'accept: application/json' \
  -H 'x-api-key: test_key'
```
**Example Response:**
```json
{
  "total_products": 90,
  "totals_by_source": {
    "1stdibs": 30,
    "fashionphile": 30,
    "grailed": 30
  },
  "avg_price_by_brand": {
    "Amiri": 450.5,
    "Chanel": 2600.0,
    "Tiffany": 1400.0
  }
}
```

---

## 3. Design Decisions

**How does your price history scale? What happens at millions of rows?**
The `price_history` table retains references via `product_id`. At millions of rows, querying `SELECT * FROM price_history WHERE product_id = X ORDER BY scraped_at DESC LIMIT 1` natively without indices is extremely slow (requiring a full table scan).
*Solution:* B-Tree indices were enforced on `price_history.product_id` and `price_history.scraped_at` during the SQLAlchemy Schema declaration. At hundreds of millions of rows, scaling requires timeseries-friendly partitioning by date (e.g., using PostgreSQL + TimescaleDB extension) and archiving stale delta records out of the hot queries.

**Implementation of Notifications / Why that approach over alternatives?**
*Approach:* A background worker pool was constructed utilizing `asyncio.Queue` acting as an Event Log. When `process_product()` detects a diff between the old and incoming price, it publishes to the queue. An async worker processes this queue and fires HTTP `POST` requests directly to interested consumer webhooks. Delivery failures are managed via exponential backoffs using the `tenacity` library so events are not silently lost during temporary recipient downtime.
*Alternatives:* We could have used Server-Sent Events (SSE) or WebSockets.
*Reasoning:* Webhooks easily surpass SSE/WebSockets for server-to-server notifications where clients might disconnect transiently. Because the server (us) actively pushes data with retries, the consumer doesn't need to implement complex state-resumption protocols, making integrations seamless for generic alerting services.

**How would you extend this system to 100+ data sources?**
Currently, `PARSERS` uses a functional dictionary mapping. For 100+ sources, placing logic inside basic conditional loops will result in an unmaintainable monolith.
*Solution:* 
1. Build a rigid Abstract Base Class (ABC) Interface `PluginFetcher` dictating `async def fetch()` and `def parse()`. 
2. Transition the 100+ sources into isolated plugins inside a `fetchers/plugins/` directory. 
3. The root service dynamically loads every interface implemented in the plugin directory upon boot, inherently scaling up the available sources without needing to alter core business logic strings.

---

## 4. Known Limitations & Improvements
- **Local DB Limitations:** Currently utilizing SQLite, which will throttle down under massive concurrent write loads during data refreshes. If given more time, scaling this up heavily requires migration to a fully managed PostgreSQL instance to support extensive MVCC concurrency during the async fetch job loops.
- **Bot Evasions:** The fetcher simulates async fetching via `aiofiles` mapping to local mock responses. Live data collection from 100+ endpoints necessitates sophisticated crawler fleets routing via rotating residential proxies paired with Headless browsers (like stealth puppeteer) to reliably bypass Cloudflare / PerimeterX protections without being blocked.
- **Authentication Scope:** API usage per key is tracked individually by hitting the SQLite database for every request header middleware verification. To improve latency, the authentication and rate-limiting limits should be aggressively cached over `Redis`.
