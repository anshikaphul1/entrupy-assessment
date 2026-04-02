# Product Price Monitoring System

A real-time scalable system designed to monitor product prices from multiple secondary market e-commerce platforms (Grailed, Fashionphile, 1stdibs). Built iteratively using FastAPI, Async SQLite (via SQLAlchemy) and Vanilla JS / HTML.

## Setup Instructions

**Prerequisites:** Python 3.9+ 

1. **Clone the repository and cd into it:**
   ```bash
   cd "entrupy assignment"
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\Activate.ps1
   # On Unix/Mac
   source venv/bin/activate
   ```

3. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Database Migrations and Dev Server:**
   ```bash
   uvicorn src.main:app --reload
   ```

5. **Interact:**
   - See the beautiful Frontend at: `http://localhost:8000/static/index.html`
   - See the OpenAPI swagger docs at: `http://localhost:8000/docs`

6. **Run Tests:** (At least 8 automated tests)
   ```bash
   pytest tests\
   ```

---

## API Documentation
*All requests require the `x-api-key: test_key` header for authentication.*

- `POST /api/refresh` 
  - **Description**: Triggers a background data fetch using `tenacity` retry logic to read local sample files imitating an async network fetch.
  - **Response Examples**: `{ "message": "Data refresh triggered in the background." }`
  
- `GET /api/products` & `GET /api/products?source={grailed|fashionphile|1stdibs}`
  - **Description**: Browsable & filterable array of tracked products. 
  
- `GET /api/products/{id}`
  - **Description**: Fetches individual product details and returns a nested array of its `price_history`.
  
- `GET /api/analytics`
  - **Description**: Fetches aggregate stats utilized by the frontend dashboard. 

---

## Design Decisions

1. **How does your price history scale? What happens at millions of rows?**
   - The `price_history` table retains references via `product_id`. At millions of rows, querying `SELECT * FROM price_history WHERE product_id = X ORDER BY scraped_at DESC LIMIT 1` natively without indices is extremely slow and leads to full table scans. 
   - *Solution Used:* B-Tree indices were created on `price_history.product_id` and `price_history.scraped_at`.
   - *Scale Up:* In real implementations, at hundreds of millions of rows, the schema would be partitioned by date (e.g. TimescaleDB for PostgreSQL) enabling faster aggregations and archival of old delta records.
   
2. **Implementation of Notifications**
   - *Approach:* We used a generic background task processing technique utilizing `asyncio.Queue` and a generic `Dispatcher` that fires HTTP POST requests via Webhooks. Webhook requests employ exponential backoff with `tenacity` to combat HTTP delivery failures.
   - *Alternative Considered:* Server-Sent Events (SSE) or WebSockets.
   - *Why Webhooks?* Webhooks excel over SSE/WebSockets for server-to-server notifications where clients (alert systems) may transiently bounce. Webhooks alongside job queues ensure reliable push semantics natively rather than the client needing to manage state.
   
3. **Extending to 100+ Data Sources?**
   - *Approach:* The `AsyncFetcher` class serves as a monolithic simulation. For 100+ sources, the `PARSERS` dictionary and simple conditional routes fail to scale cleanly.
   - *Refactor:* Replace structural dicts with a distinct Interface `class PluginFetcher(ABC): async def fetch() ... def parse()`. 100 sources translate to 100 modules adhering strictly to this ABC, leveraging dynamic module loading strategies, making it modular.

## Known Limitations & Further Improvements
- Uses SQLite: Cannot process multiple concurrent heavy writes. True scaling requires PostgreSQL.
- Hardcoded `sample_products` directories are expected to be present within `d:/entrupy assignment/sample_products`.
- Fetcher simply reads the local state. An actual crawler requires robust rotating proxies via stealth puppeteer to evade anti-bot filters (Cloudflare, PerimeterX).
