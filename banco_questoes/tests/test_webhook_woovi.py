import base64
import hashlib
import hmac

from django.test import TestCase, override_settings
from django.urls import reverse


def sign(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("utf-8")


@override_settings(OPENPIX_WEBHOOK_SECRET="test_secret")
class WooviWebhookTests(TestCase):
    def test_post_valid_signature_returns_200(self):
        url = reverse("openpix_webhook")
        body = b'{"hello":"world"}'
        sig = sign("test_secret", body)

        resp = self.client.post(
            url,
            data=body,
            content_type="application/json",
            **{"HTTP_X_WEBHOOK_SIGNATURE": sig},
        )
        self.assertEqual(resp.status_code, 200)

    def test_post_invalid_signature_returns_401(self):
        url = reverse("openpix_webhook")
        body = b'{"hello":"world"}'

        resp = self.client.post(
            url,
            data=body,
            content_type="application/json",
            **{"HTTP_X_WEBHOOK_SIGNATURE": "invalid"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_get_returns_405(self):
        url = reverse("openpix_webhook")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)
