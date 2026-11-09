"""Stage P (C2PA provenance) P1 + P2 in the publisher.

Verifies:
  - /media/upload reads the C2PA manifest: unsigned files pass through,
    signed files are Trusted against the test CA, tampered files are
    refused with 400 c2pa_invalid, and an audit record is written
  - the publisher signs the Tier 2 blur with a manifest that references
    the capture and redacts its thumbnail, camera and sensor assertions
  - the pipeline attaches `provenance` to the row and mints a token
  - /platform/data shows the signer only to Tier 2+

Needs c2pa-python and Pillow; skipped without them. Run with
``uv run --with c2pa-python --with pillow python -m pytest tests/test_c2pa_provenance.py``
(``python -m``: a bare ``pytest`` resolves to the project venv and does
not see the ``--with`` packages). The chain client
(ProvenanceToken.mint) is tested in test_provenance_token_client.py.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import time
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
P0_DIR = REPO_ROOT / "examples" / "hands_on" / "c2pa_provenance"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- C2PA (c2pa-python) ----

c2pa = pytest.importorskip("c2pa")
PIL_Image = pytest.importorskip("PIL.Image")
from PIL import ImageFilter  # noqa: E402


@pytest.fixture(scope="module")
def certs(tmp_path_factory):
    out = tmp_path_factory.mktemp("certs")
    _load("make_test_certs", P0_DIR / "make_test_certs.py").build(out, "iw3ip-gateway")
    return out


@pytest.fixture(scope="module")
def p0():
    return _load("p0_sign_verify", P0_DIR / "p0_sign_verify.py")


def _jpeg(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture(scope="module")
def capture(certs, p0) -> bytes:
    """A capture signed by the gateway, like p0_sign_verify.py makes."""
    img = PIL_Image.new("RGB", (64, 48), (90, 120, 160))
    definition = {
        "claim_generator_info": [{"name": "iw3ip-gateway", "version": "0.1.0"}],
        "title": "capture.jpg",
        "assertions": [
            {"label": "c2pa.actions", "data": {"actions": [
                {"action": "c2pa.created", "digitalSourceType": p0.DIGITAL_CAPTURE}]}},
            {"label": "jp.ertl.iw3ip.capture", "data": {
                "camera_id": "cam01", "captured_at": "2026-11-09T10:00:00Z"}},
            {"label": "jp.ertl.iw3ip.sensor", "data": {"readings": [
                {"topic": "home/env/temperature", "value": 22.4, "unit": "Cel"}]}},
        ],
    }
    out = io.BytesIO()
    with c2pa.Builder(definition) as b:
        b.sign(p0.make_signer(certs), "image/jpeg", io.BytesIO(_jpeg(img)), out)
    return out.getvalue()


@pytest.fixture
def client(monkeypatch, tmp_path, certs):
    monkeypatch.setenv("SSI_ISSUER_KEY_PATH", str(tmp_path / "issuer_key.jwk.json"))
    monkeypatch.setenv("SSI_PRESENTATION_DEFS_DIR", str(REPO_ROOT / "examples" / "ssi_wallet"))
    monkeypatch.setenv("SSI_ISSUER_BASE_URL", "http://testserver")
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("CONSENT_STORE_PATH", str(tmp_path / "consents.json"))
    monkeypatch.setenv("PLATFORM_API_URL", "http://testserver/platform/ingest")
    monkeypatch.setenv("MQTT_BROKER_HOST", "localhost")
    monkeypatch.setenv("MQTT_TOPICS", "")
    monkeypatch.setenv("SSI_PEX_SIDECAR_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("MEDIA_STORE_PATH", str(tmp_path / "media"))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "")
    monkeypatch.setenv("C2PA_ENABLED", "true")
    monkeypatch.setenv("C2PA_TRUST_ANCHORS_PATH", str(certs / "ca.pem"))
    monkeypatch.setenv("C2PA_SIGNER_CHAIN_PATH", str(certs / "publisher_chain.pem"))
    monkeypatch.setenv("C2PA_SIGNER_KEY_PATH", str(certs / "publisher.key"))

    import importlib
    import publisher.app.main as pm
    importlib.reload(pm)

    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient
        with TestClient(pm.app) as tc:
            yield tc, pm


def _upload(tc, blob: bytes, name: str = "frame.jpg"):
    return tc.post("/media/upload", files={"file": (name, blob, "image/jpeg")})


def test_unsigned_upload_passes_through(client):
    tc, _ = client
    r = _upload(tc, _jpeg(PIL_Image.new("RGB", (8, 8))))
    assert r.status_code == 200, r.text
    assert r.json()["c2pa"]["present"] is False


def test_signed_upload_is_trusted_and_audited(client, capture, tmp_path):
    tc, pm = client
    r = _upload(tc, capture)
    assert r.status_code == 200, r.text
    c = r.json()["c2pa"]
    assert c["present"] is True
    assert c["validation_state"] == "Trusted"
    assert c["trusted"] is True
    assert c["signer"] == "iw3ip-gateway"
    assert c["manifest_label"].startswith("urn:c2pa:")
    sha = r.json()["sha256"]
    assert (tmp_path / "media" / ".c2pa" / f"{sha}.json").is_file()
    # the sidecar (it holds the signer name) is not served under any spelling
    for name in (f".c2pa/{sha}.json", f"{sha}.json", f"{sha}.C2PA.json", ".c2pa"):
        assert tc.get(f"/media/{name}").status_code in (400, 404), name
    logs = [l for l in pm.audit_repo.list_recent(20) if l["raw_topic"] == "provenance/verified"]
    assert logs and logs[0]["reason"].startswith("c2pa:Trusted:urn:c2pa:")


def test_tampered_upload_is_refused(client, capture):
    tc, _ = client
    tampered = bytearray(capture)
    tampered[-10] ^= 0xFF
    r = _upload(tc, bytes(tampered))
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "c2pa_invalid"
    assert detail["c2pa"]["validation_state"] == "Invalid"
    sha = hashlib.sha256(bytes(tampered)).hexdigest()
    assert tc.get(f"/media/{sha}.jpg").status_code == 404


@pytest.mark.parametrize("name", ["x.webp", "x.gif", "x.png"])
def test_tampered_upload_is_refused_whatever_the_filename(client, capture, name):
    """The type comes from the bytes, so renaming does not skip the check."""
    tc, _ = client
    tampered = bytearray(capture)
    tampered[-10] ^= 0xFF
    r = tc.post("/media/upload", files={"file": (name, bytes(tampered), "application/octet-stream")})
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["error"] == "c2pa_invalid"


def test_unreadable_manifest_is_refused_not_treated_as_unsigned(client, capture):
    """Damage inside the manifest makes the SDK raise instead of returning
    Invalid; that must not turn the file into an 'unsigned' upload."""
    tc, _ = client
    i = capture.find(b"c2pa")
    damaged = bytearray(capture)
    damaged[i + 200] ^= 0xFF
    r = _upload(tc, bytes(damaged))
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["c2pa"]["failure_codes"] == ["c2pa.unreadable"]


def test_signed_upload_without_trust_anchor_is_valid_untrusted(capture):
    from publisher.app.c2pa_provenance import C2paProvenance

    res = C2paProvenance().verify(capture, "image/jpeg")
    assert res.validation_state == "Valid"
    assert res.trusted is False
    assert "signingCredential.untrusted" in res.failure_codes


def test_tier2_derivative_redacts_capture_and_stays_trusted(client, capture):
    _, pm = client
    prov = pm.c2pa_provenance
    blurred = _jpeg(PIL_Image.open(io.BytesIO(capture)).convert("RGB").filter(ImageFilter.GaussianBlur(4)))
    signed = prov.sign_tier2(source=capture, derived=blurred, content_type="image/jpeg")
    res = prov.verify(signed, "image/jpeg")
    assert res.validation_state == "Trusted"
    assert res.signer == "iw3ip-publisher"
    with c2pa.Reader("image/jpeg", io.BytesIO(signed), context=prov._context) as r:
        store = json.loads(r.json())
    cap_label = prov.verify(capture, "image/jpeg").manifest_label
    remaining = [a["label"] for a in store["manifests"][cap_label]["assertions"]]
    assert "jp.ertl.iw3ip.capture" not in remaining
    assert "jp.ertl.iw3ip.sensor" not in remaining
    assert "thumbnail" not in store["manifests"][cap_label]
    ingredients = store["manifests"][store["active_manifest"]]["ingredients"]
    assert all("thumbnail" not in i for i in ingredients)
    assert b"cam01" not in signed


def test_redactor_signs_the_blur_before_upload(client, capture, monkeypatch):
    """ImageRedactor (opencv backend) with the face detector and the HTTP
    round trips replaced: the uploaded bytes must carry the Tier 2 manifest."""
    tc, pm = client
    from publisher.app import image_redactor as ir

    monkeypatch.setattr(ir, "_opencv_blur_faces", lambda b, ext: _jpeg(
        PIL_Image.open(io.BytesIO(b)).convert("RGB").filter(ImageFilter.GaussianBlur(4))))

    class _Resp:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return _Resp(capture)

    uploaded = {}

    def fake_upload(*, upload_endpoint, body, filename, content_type):
        uploaded["body"] = body
        return _upload(tc, body, filename).json()

    monkeypatch.setattr(ir.httpx, "Client", _Client)
    monkeypatch.setattr(ir, "_post_to_media_upload", fake_upload)
    redactor = ir.ImageRedactor(backend="opencv", provenance=pm.c2pa_provenance)
    out = redactor.blur_pii(image_url="http://p/media/x.jpg", content_type="image/jpeg")
    assert out["image_redacted_c2pa"]["validation_state"] == "Trusted"
    assert out["image_redacted_c2pa"]["signer"] == "iw3ip-publisher"
    assert b"cam01" not in uploaded["body"]


def test_pipeline_attaches_provenance_and_mints(client, capture):
    tc, pm = client
    up = _upload(tc, capture).json()
    tc.post("/consents", json=json.loads((REPO_ROOT / "examples" / "consent_possible_littering.json").read_text()))
    minted = {}

    def fake_mint(**kw):
        minted.update(kw)
        return {"token_id": 3, "tx_hash": "0x" + "12" * 32, "contract": "0x" + "cc" * 20}

    pm.processor.provenance_token = type("T", (), {"mint": staticmethod(fake_mint)})()
    # PLATFORM_API_URL points at the TestClient host, which real HTTP cannot reach
    pm.processor.platform_client = type("P", (), {"send": staticmethod(pm.app.state.ingested.append)})()
    payload = json.loads((REPO_ROOT / "examples" / "payload_possible_littering.json").read_text())
    payload["image_url"] = up["url"]
    r = tc.post("/simulate/publish", json={
        "topic": "homeassistant/event/possible_littering", "payload": payload,
        "purpose": "community_cleaning",
    })
    assert r.json()["status"] == "allowed", r.text
    row = pm.app.state.ingested[-1]
    prov = row["provenance"]
    assert prov["manifest_label"] == up["c2pa"]["manifest_label"]
    assert prov["validation_state"] == "Trusted"
    assert prov["token_id"] == 3
    assert minted["asset_sha256"] == up["sha256"]
    topics = [l["raw_topic"] for l in pm.audit_repo.list_recent(50)]
    assert "provenance/anchored" in topics


# ---- /platform/data projection of `provenance` ----

def _viewer_token(tc, attrs: dict | None) -> tuple[str, list[str]]:
    """Claim -> PurchaseViewerVC -> presentation, as the tier tests do."""
    from cryptography.hazmat.primitives.asymmetric import ec

    from publisher.app.ssi.keys import private_key_to_jwk, public_jwk_from_private_jwk
    from publisher.app.ssi.sdjwt import _b64u, _es256_sign, _json_bytes

    body = {
        "merchandise_address": "0x" + "44" * 20,
        "buyer_eth_addr": "0x" + "55" * 20,
        "tx_hash": "0x" + hashlib.sha256(json.dumps(attrs).encode()).hexdigest(),
        "dataset_id": "home/env/temperature",
    }
    if attrs:
        body["data_user_attrs"] = attrs
    deeplink = tc.post("/marketplace/claim", json=body).json()["deeplink"]
    offer = json.loads(urllib.parse.unquote(deeplink.split("=", 1)[1]))
    pre_auth = offer["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]
    jwk = private_key_to_jwk(ec.generate_private_key(ec.SECP256R1()))
    pub = public_jwk_from_private_jwk(jwk)
    tok = tc.post("/issuer/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
        "pre-authorized_code": pre_auth,
    }).json()
    h = _b64u(_json_bytes({"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": pub}))
    p = _b64u(_json_bytes({"nonce": tok["c_nonce"], "aud": "http://testserver", "iat": int(time.time())}))
    proof = h + "." + p + "." + _b64u(_es256_sign(jwk, (h + "." + p).encode("ascii")))
    cred = tc.post("/issuer/credential", headers={"Authorization": f"Bearer {tok['access_token']}"}, json={
        "format": "vc+sd-jwt",
        "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
        "proof": {"proof_type": "jwt", "jwt": proof},
    }).json()
    req = tc.get("/verifier/request", params={
        "dataset_id": "home/env/temperature", "vc_kind": "PurchaseViewerVC",
    }, headers={"accept": "application/json"}).json()
    sub = {
        "id": "sub", "definition_id": "purchase-viewer-temperature",
        "descriptor_map": [{"id": "purchase_viewer_vc_temperature", "format": "vc+sd-jwt", "path": "$"}],
    }
    presented = tc.post("/verifier/response", data={
        "vp_token": cred["credential"], "presentation_submission": json.dumps(sub),
        "state": req["state"],
    }).json()
    return presented["viewer_token"], presented["allowed_views"]


_TIER3 = {"entityType": "GovernmentOrganization", "purpose": "research",
          "legalCompliance": True, "dataHandlingPolicy": "ISO27001", "misuseRecord": False}
_TIER2 = dict(_TIER3, entityType="Enterprise")


@pytest.mark.parametrize("attrs,signer_visible", [(_TIER3, True), (_TIER2, True), (None, False)])
def test_platform_data_projects_provenance(client, attrs, signer_visible):
    tc, pm = client
    pm.app.state.ingested.append({
        "dataset_id": "home/env/temperature",
        "data": {"value": 1},
        "provenance": {
            "manifest_label": "urn:c2pa:cap", "validation_state": "Trusted",
            "signer": "iw3ip-gateway", "redacted_manifest_label": "urn:c2pa:t2",
            "token_id": 1, "derived_sha256": "ab" * 32,
        },
    })
    token, views = _viewer_token(tc, attrs)
    rows = tc.get("/platform/data", params={"dataset_id": "home/env/temperature"},
                  headers={"Authorization": f"Bearer {token}"}).json()["rows"]
    prov = rows[-1]["provenance"]
    assert prov["manifest_label"] == "urn:c2pa:cap"
    assert prov["token_id"] == 1
    assert ("signer" in prov) is signer_visible
    # legacy tiers have neither image_redacted nor description_summary
    assert "redacted_manifest_label" not in prov
    assert "derived_sha256" not in prov
