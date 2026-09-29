"""Offline checks for the upstream response and request formats."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

import app


class ApiContractTests(unittest.TestCase):
    def test_generation_accepts_documented_201_zip_response(self):
        response = httpx.Response(201, content=b"zip payload")
        client = MagicMock()
        client.post.return_value = response
        with patch.object(app.httpx, "Client") as client_type:
            client_type.return_value.__enter__.return_value = client
            result = app._call_novelai("test-token", {"input": "test"})

        self.assertEqual(result, b"zip payload")
        self.assertEqual(client.post.call_args.kwargs["headers"]["Accept"], "application/zip")

    def test_upscale_sends_only_documented_fields(self):
        response = httpx.Response(200, content=b"\x89PNG\r\n\x1a\nexample")
        client = MagicMock()
        client.post.return_value = response
        with patch.object(app.httpx, "Client") as client_type:
            client_type.return_value.__enter__.return_value = client
            result = app._call_upscale("test-token", "base64-image", "nai-diffusion-5-full")

        self.assertEqual(result, response.content)
        self.assertEqual(
            client.post.call_args.kwargs["json"],
            {"image": "base64-image", "model": "nai-diffusion-5-full"},
        )

    def test_old_upscale_scale_is_rejected(self):
        with self.assertRaises(ValidationError):
            app.UpscaleRequest(filename="example.png", scale=4)

    def test_upscale_output_cannot_escape_output_directory(self):
        with patch.object(app, "_require_key", return_value="test-token"), patch.object(
            app, "_resolve_local_image", return_value=Path("example.png")
        ), patch.object(app, "_call_upscale") as upstream:
            with self.assertRaises(HTTPException) as raised:
                app.upscale(app.UpscaleRequest(filename="example.png", output_name="../elsewhere.png"))

        self.assertEqual(raised.exception.status_code, 400)
        upstream.assert_not_called()

    def test_generation_does_not_retry_429(self):
        client = MagicMock()
        client.post.return_value = httpx.Response(429, text="rate limited")
        with patch.object(app.httpx, "Client") as client_type:
            client_type.return_value.__enter__.return_value = client
            with self.assertRaises(HTTPException) as raised:
                app._call_novelai("test-token", {"input": "test"})

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(client.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
