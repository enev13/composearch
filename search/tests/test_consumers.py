from unittest.mock import patch

from django.test import TestCase

from search.consumers import SearchStreamConsumer
from search.tests.fixtures.products import sample_product


async def mock_stream_search(query):
    yield sample_product


class TestSearchStreamConsumer(TestCase):
    async def _run_consumer(self, query_string):
        consumer = SearchStreamConsumer()
        consumer.scope = {"query_string": query_string}
        collected = []

        async def fake_send(message):
            collected.append(message)

        consumer.send = fake_send
        await consumer.handle(b"")
        return collected

    @patch("search.consumers.stream_search", side_effect=mock_stream_search)
    async def test_consumer_streams_product_then_done(self, mock_stream):
        messages = await self._run_consumer(b"query=test")

        starts = [m for m in messages if m["type"] == "http.response.start"]
        self.assertEqual(len(starts), 1)
        start = starts[0]
        self.assertEqual(start["status"], 200)
        self.assertIn(
            (b"content-type", b"text/event-stream"),
            [(k.lower(), v.lower()) for k, v in start["headers"]],
        )

        body = b"".join(
            m["body"] for m in messages if m["type"] == "http.response.body"
        ).decode("utf-8")

        self.assertIn("event: product", body)
        self.assertIn("event: done", body)
        self.assertLess(body.index("event: product"), body.index("event: done"))
        self.assertIn(sample_product.name, body)

    async def test_consumer_empty_query_sends_error(self):
        messages = await self._run_consumer(b"")

        body = b"".join(
            m["body"] for m in messages if m["type"] == "http.response.body"
        ).decode("utf-8")

        self.assertIn("event: error", body)
        self.assertNotIn("event: product", body)
        self.assertNotIn("event: done", body)
