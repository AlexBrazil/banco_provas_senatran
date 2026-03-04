from __future__ import annotations

import json

from django.conf import settings


def meta_pixel_context(request):
    pixel_id = (settings.META_PIXEL_ID or "").strip()
    pixel_enabled = bool(settings.META_PIXEL_ENABLED and pixel_id)
    pageview_event_id = getattr(request, "_meta_pageview_event_id", "") or ""
    pending_events = []
    if hasattr(request, "session"):
        raw_events = request.session.pop("meta_pending_events", [])
        if isinstance(raw_events, list):
            pending_events = raw_events
    return {
        "meta_pixel_enabled": pixel_enabled,
        "meta_pixel_id": pixel_id,
        "meta_pageview_event_id": pageview_event_id,
        "meta_pending_events_json": json.dumps(pending_events, ensure_ascii=True),
    }
