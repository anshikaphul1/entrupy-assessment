import asyncio
import httpx
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

class WebhookDispatcher:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.running = False
        self._task = None

    async def start(self):
        self.running = True
        self._task = asyncio.create_task(self._worker())
        
    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()

    async def notify_price_change(self, product_id: int, new_price: float, url: str):
        """Enqueue a notification."""
        payload = {
            "event": "price_changed",
            "product_id": product_id,
            "new_price": new_price,
            "url": url
        }
        await self.queue.put(payload)

    async def _worker(self):
        async with httpx.AsyncClient() as client:
            while self.running:
                try:
                    payload = await self.queue.get()
                    await self._send_webhook(client, payload)
                    self.queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in webhook worker: {e}")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True
    )
    async def _send_webhook(self, client: httpx.AsyncClient, payload: dict):
        # We assume interested parties registered a single webhook URL for simplicity.
        # In a real system, you would query the DB for subscribed webhooks.
        WEBHOOK_URL = "http://localhost:8000/api/webhook_test_receiver" 
        try:
            response = await client.post(WEBHOOK_URL, json=payload, timeout=5.0)
            response.raise_for_status()
            logger.info(f"Successfully sent notification for product {payload.get('product_id')}")
        except httpx.RequestError as exc:
            logger.warning(f"Request error while sending webhook: {exc}")
            raise # triggers tenacity retry

dispatcher = WebhookDispatcher()
