from __future__ import annotations

import html as _html


_QR_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; padding: 2rem; max-width: 720px; margin: 0 auto; }}
    #qr {{ margin: 1rem 0; }}
    pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; font-size: 0.85rem; }}
    a.deeplink {{ display: inline-block; margin-top: 0.5rem; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>{subtitle}</p>
  <div id="qr"></div>
  <p><a class="deeplink" href="{deeplink}">{deeplink_label}</a></p>
  <details open><summary>payload</summary><pre>{payload_json}</pre></details>
  <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
  <script>
    QRCode.toCanvas(document.getElementById('qr'), {deeplink_js}, {{ width: 320 }});
  </script>
</body>
</html>
"""


def render_qr_page(
    *,
    title: str,
    subtitle: str,
    deeplink: str,
    deeplink_label: str,
    payload_json: str,
) -> str:
    import json as _json

    return _QR_PAGE.format(
        title=_html.escape(title),
        subtitle=_html.escape(subtitle),
        deeplink=_html.escape(deeplink, quote=True),
        deeplink_label=_html.escape(deeplink_label),
        payload_json=_html.escape(payload_json),
        deeplink_js=_json.dumps(deeplink),
    )
