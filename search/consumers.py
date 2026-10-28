import json
import time
from urllib.parse import parse_qs

from channels.generic.http import AsyncHttpConsumer

from search.search import stream_search


class SearchStreamConsumer(AsyncHttpConsumer):
    """
    Streams search results to the browser as Server-Sent Events.
    """

    async def handle(self, body):
        query_string = self.scope["query_string"].decode("utf-8")
        query_params = parse_qs(query_string)
        query = query_params.get("query", [""])[0]

        await self.send_headers(
            status=200,
            headers=[
                (b"Content-Type", b"text/event-stream"),
                (b"Cache-Control", b"no-cache"),
                (b"X-Accel-Buffering", b"no"),
            ],
        )

        if not query:
            await self.send_body(b"event: error\ndata: {}\n\n", more_body=False)
            return

        start_time = time.perf_counter()
        async for product in stream_search(query):
            data = json.dumps(product.to_dict())
            frame = f"event: product\ndata: {data}\n\n".encode("utf-8")
            await self.send_body(frame, more_body=True)

        elapsed = time.perf_counter() - start_time
        done_data = json.dumps({"seconds": round(elapsed, 2)})
        done_frame = f"event: done\ndata: {done_data}\n\n".encode("utf-8")
        await self.send_body(done_frame, more_body=False)
