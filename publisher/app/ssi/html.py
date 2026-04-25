from __future__ import annotations

import base64
import html as _html
import io


_QR_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; padding: 2rem; max-width: 720px; margin: 0 auto; }}
    img.qr {{ margin: 1rem 0; image-rendering: pixelated; width: 320px; height: 320px; }}
    pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; font-size: 0.85rem; }}
    a.deeplink {{ display: inline-block; margin-top: 0.5rem; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>{subtitle}</p>
  <img class="qr" alt="QR code for {deeplink_label}" src="{qr_data_uri}" />
  <p><a class="deeplink" href="{deeplink}">{deeplink_label}</a></p>
  <details open><summary>payload</summary><pre>{payload_json}</pre></details>
</body>
</html>
"""


def _render_qr_data_uri(text: str) -> str:
    try:
        import qrcode  # type: ignore
    except ImportError:
        return ""
    img = qrcode.make(text, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def render_qr_page(
    *,
    title: str,
    subtitle: str,
    deeplink: str,
    deeplink_label: str,
    payload_json: str,
) -> str:
    qr_data_uri = _render_qr_data_uri(deeplink)

    return _QR_PAGE.format(
        title=_html.escape(title),
        subtitle=_html.escape(subtitle),
        deeplink=_html.escape(deeplink, quote=True),
        deeplink_label=_html.escape(deeplink_label),
        payload_json=_html.escape(payload_json),
        qr_data_uri=_html.escape(qr_data_uri, quote=True),
    )
