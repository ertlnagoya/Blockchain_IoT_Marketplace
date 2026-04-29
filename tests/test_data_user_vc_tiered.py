"""DataUserVC + tiered allowed_views projection (Stage T / case alpha).

Verifies:
  - trust_score module mirrors DataUserVerifier.sol scoring
  - DataUserVC issuance + presentation works for the 5 attributes
  - /platform/data projects rows according to ViewerToken.allowed_views
  - /marketplace/claim accepts data_user_attrs and bakes allowed_views
    into the resulting PurchaseViewerVC
  - existing ViewerVC flow without allowed_views falls back to Tier 1
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk
from publisher.app.ssi.keys import private_key_to_jwk, public_jwk_from_private_jwk
from publisher.app.ssi.sdjwt import _b64u, _es256_sign, _json_bytes
from publisher.app.ssi.trust_score import (
    evaluate,
    evaluate_from_claims,
)


# ---- trust_score pure-function tests ----

def test_trust_full_for_government_research_iso27001():
    """Mirror of Solidity scoring: gov(35)+research(15)+legal(15)+iso(15)+clean(10) = 90 -> full"""
    e = evaluate(
        entity_type="GovernmentOrganization",
        purpose="research",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
    )
    assert e.trust_score == 90
    assert e.access_level == "full"
    assert e.allowed_views == ["event", "image", "video"]


def test_trust_access_for_enterprise():
    """enterprise(20)+research(15)+legal(15)+iso(15)+clean(10) = 75; not gov so capped at 'access'"""
    e = evaluate(
        entity_type="Enterprise",
        purpose="research",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
    )
    assert e.trust_score == 75
    assert e.access_level == "access"
    assert e.allowed_views == ["event", "image"]


def test_trust_denied_for_low_score():
    """unknown(5)+unknown(5)+nolegal+nopolicy+misuse = 5+5-10 = 0 -> denied"""
    e = evaluate(
        entity_type="Random",
        purpose="other",
        legal_compliance=False,
        data_handling_policy="",
        misuse_record=True,
    )
    assert e.trust_score == 0
    assert e.access_level == "denied"
    assert e.allowed_views == []


def test_trust_full_requires_high_score_AND_gov_or_police():
    """gov score 90 -> full; same score with enterprise -> only access"""
    gov = evaluate(
        entity_type="Police",
        purpose="crime search",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
    )
    assert gov.access_level == "full"

    ent_high = evaluate(
        entity_type="Enterprise",
        purpose="crime search",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
    )
    assert ent_high.trust_score >= 80
    # Not gov/police, so still "access"
    assert ent_high.access_level == "access"


def test_evaluate_from_claims():
    e = evaluate_from_claims({
        "entityType": "GovernmentOrganization",
        "purpose": "research",
        "legalCompliance": True,
        "dataHandlingPolicy": "ISO27001",
        "misuseRecord": False,
    })
    assert e.access_level == "full"


# ---- API integration tests ----

@pytest.fixture
def client(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SSI_ISSUER_KEY_PATH", str(tmp_path / "issuer_key.jwk.json"))
    monkeypatch.setenv("SSI_PRESENTATION_DEFS_DIR", str(repo_root / "examples" / "ssi_wallet"))
    monkeypatch.setenv("SSI_ISSUER_BASE_URL", "http://testserver")
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("CONSENT_STORE_PATH", str(tmp_path / "consents.json"))
    monkeypatch.setenv("PLATFORM_API_URL", "http://testserver/platform/ingest")
    monkeypatch.setenv("MQTT_BROKER_HOST", "localhost")
    monkeypatch.setenv("MQTT_TOPICS", "")
    monkeypatch.setenv("SSI_PEX_SIDECAR_URL", "http://127.0.0.1:1")
    # Stage T (case B): keep the media gateway store inside tmp_path so
    # the test never writes to /data/media on the host.
    monkeypatch.setenv("MEDIA_STORE_PATH", str(tmp_path / "media"))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "")

    import importlib
    import publisher.app.main as pm
    importlib.reload(pm)

    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient
        with TestClient(pm.app) as tc:
            yield tc, pm


def test_issuer_metadata_lists_data_user_vc(client):
    tc, _ = client
    cfgs = tc.get("/.well-known/openid-credential-issuer").json()["credential_configurations_supported"]
    assert "DataUserVC" in cfgs
    assert cfgs["DataUserVC"]["vct"].endswith("/DataUserVC/v1")


def test_data_user_vc_offer_requires_attributes(client):
    tc, _ = client
    r = tc.get(
        "/issuer/offer",
        params={"type": "DataUserVC"},
        headers={"accept": "application/json"},
    )
    assert r.status_code == 400


def test_marketplace_claim_with_data_user_attrs_promotes_views(client):
    tc, _ = client
    body = {
        "merchandise_address": "0x" + "ab" * 20,
        "buyer_eth_addr": "0x" + "cd" * 20,
        "tx_hash": "0x" + "ef" * 32,
        "dataset_id": "home/event/possible_littering",
        "data_user_attrs": {
            "entityType": "GovernmentOrganization",
            "purpose": "research",
            "legalCompliance": True,
            "dataHandlingPolicy": "ISO27001",
            "misuseRecord": False,
        },
    }
    r = tc.post("/marketplace/claim", json=body)
    assert r.status_code == 200, r.text
    # The response shape doesn't (yet) surface allowed_views, so verify
    # via internal state via the GET /marketplace/claim/{id}
    claim_id = r.json()["claim_id"]
    # The claim record itself isn't exposed verbatim, but its
    # pre_authorized_code now points to an Offer; we simulate the rest of
    # the flow in test_purchase_viewer_vc_inherits_allowed_views.
    assert claim_id


def test_marketplace_claim_without_data_user_attrs_defaults_event_only(client):
    tc, pm = client
    body = {
        "merchandise_address": "0x" + "11" * 20,
        "buyer_eth_addr": "0x" + "22" * 20,
        "tx_hash": "0x" + "33" * 32,
        "dataset_id": "home/env/temperature",
    }
    tc.post("/marketplace/claim", json=body)
    # Inspect the stored claim
    claim_id = tc.post("/marketplace/claim", json=body).json()["claim_id"]
    claim = pm.ssi_state.get_marketplace_claim(claim_id)
    assert claim.allowed_views == ["event"]
    assert claim.trust_score is None


def _holder():
    pk = ec.generate_private_key(ec.SECP256R1())
    jwk = private_key_to_jwk(pk)
    pub = public_jwk_from_private_jwk(jwk)
    return jwk, pub, did_jwk_from_public_jwk(pub)


def _proof(priv, pub, nonce, aud):
    h = _b64u(_json_bytes({"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": pub}))
    p = _b64u(_json_bytes({"nonce": nonce, "aud": aud, "iat": int(time.time())}))
    sig = _es256_sign(priv, (h + "." + p).encode("ascii"))
    return h + "." + p + "." + _b64u(sig)


def _purchase_viewer_token(tc, *, allowed_views_in_claim: list[str], tx_seed: str = "66"):
    """End-to-end: claim with given views → receive PurchaseViewerVC →
    present → returned ViewerToken should carry allowed_views."""
    # Use trust_score-derived allowed_views via data_user_attrs.
    # Map views back to representative attributes.
    if allowed_views_in_claim == ["event", "image", "video"]:
        attrs = {
            "entityType": "GovernmentOrganization",
            "purpose": "research",
            "legalCompliance": True,
            "dataHandlingPolicy": "ISO27001",
            "misuseRecord": False,
        }
    elif allowed_views_in_claim == ["event", "image"]:
        attrs = {
            "entityType": "Enterprise",
            "purpose": "research",
            "legalCompliance": True,
            "dataHandlingPolicy": "ISO27001",
            "misuseRecord": False,
        }
    else:
        attrs = None

    body: dict = {
        "merchandise_address": "0x" + "44" * 20,
        "buyer_eth_addr": "0x" + "55" * 20,
        "tx_hash": "0x" + tx_seed * 32,
        "dataset_id": "home/env/temperature",
    }
    if attrs:
        body["data_user_attrs"] = attrs

    claim_resp = tc.post("/marketplace/claim", json=body).json()
    deeplink = claim_resp["deeplink"]
    pre_auth = json.loads(__import__("urllib.parse").parse.unquote(
        deeplink.split("=", 1)[1]
    ))["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]

    priv, pub, _ = _holder()
    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    proof = _proof(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    req = tc.get(
        "/verifier/request",
        params={"dataset_id": "home/env/temperature", "vc_kind": "PurchaseViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-purchase-viewer-temperature",
        "definition_id": "purchase-viewer-temperature",
        "descriptor_map": [{"id": "purchase_viewer_vc_temperature", "format": "vc+sd-jwt", "path": "$"}],
    }
    presented = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    return presented


def test_purchase_viewer_vc_inherits_allowed_views(client):
    """Tier 3 attrs in claim → Tier 3 allowed_views in PurchaseViewerVC + ViewerToken."""
    tc, _ = client
    presented = _purchase_viewer_token(tc, allowed_views_in_claim=["event", "image", "video"])
    assert presented["status"] == "allowed", presented
    assert presented["allowed_views"] == ["event", "image", "video"]


def test_platform_data_projects_image_video_for_tier_3(client):
    tc, _ = client
    # Seed a row with image_cid + video_cid so projection has something to filter
    pm = __import__("publisher.app.main", fromlist=["app"])
    pm.app.state.ingested.append({
        "dataset_id": "home/env/temperature",
        "event_type": "tick",
        "data": {"value": 1},
        "image_cid": "QmTier2Image",
        "video_cid": "QmTier3Video",
        "video_duration_sec": 5,
    })

    presented = _purchase_viewer_token(tc, allowed_views_in_claim=["event", "image", "video"])
    token = presented["viewer_token"]
    r = tc.get(
        "/platform/data",
        params={"dataset_id": "home/env/temperature"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed_views"] == ["event", "image", "video"]
    row = body["rows"][0]
    assert row["image_cid"] == "QmTier2Image"
    assert row["video_cid"] == "QmTier3Video"
    assert row["video_duration_sec"] == 5


def test_platform_data_hides_video_for_tier_2(client):
    tc, _ = client
    pm = __import__("publisher.app.main", fromlist=["app"])
    pm.app.state.ingested.append({
        "dataset_id": "home/env/temperature",
        "event_type": "tick",
        "data": {"value": 2},
        "image_cid": "QmImage",
        "video_cid": "QmVideo",
    })

    presented = _purchase_viewer_token(tc, allowed_views_in_claim=["event", "image"])
    token = presented["viewer_token"]
    r = tc.get(
        "/platform/data",
        params={"dataset_id": "home/env/temperature"},
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["allowed_views"] == ["event", "image"]
    row = body["rows"][0]
    assert row["image_cid"] == "QmImage"
    assert "video_cid" not in row


def test_platform_data_hides_image_and_video_for_tier_1(client):
    """A vanilla ViewerVC (no allowed_views claim) should default to
    Tier 1 = event only. Image/video CIDs in the row must be filtered."""
    tc, _ = client
    pm = __import__("publisher.app.main", fromlist=["app"])
    pm.app.state.ingested.append({
        "dataset_id": "home/env/temperature",
        "event_type": "tick",
        "data": {"value": 3},
        "image_cid": "QmShouldBeHidden",
        "video_cid": "QmShouldBeHiddenToo",
    })

    # Issue + present a regular ViewerVC (no allowed_views claim)
    priv, pub, _ = _holder()
    offer = tc.get(
        "/issuer/offer",
        params={"type": "ViewerVC", "dataset_id": "home/env/temperature", "purpose": "read"},
        headers={"accept": "application/json"},
    ).json()
    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": offer["pre_authorized_code"],
        },
    ).json()
    proof = _proof(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/ViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"dataset_id": "home/env/temperature", "vc_kind": "ViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-viewer-temperature",
        "definition_id": "viewer-temperature",
        "descriptor_map": [{"id": "viewer_vc_temperature", "format": "vc+sd-jwt", "path": "$"}],
    }
    presented = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    viewer_token = presented["viewer_token"]
    assert presented["allowed_views"] == ["event"]

    r = tc.get(
        "/platform/data",
        params={"dataset_id": "home/env/temperature"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    body = r.json()
    assert body["allowed_views"] == ["event"]
    row = body["rows"][0]
    assert "image_cid" not in row
    assert "video_cid" not in row
    assert row["data"]["value"] == 3


# ---- Stage T case alpha bug-fix regressions ----


def test_issuer_offer_with_claim_id_reuses_claim_pre_auth_code(client):
    """Regression for the iPhone e2e bug where /issuer/offer?type=PurchaseViewerVC&claim_id=...
    silently minted a fresh, claim-less Offer. The wallet would then hand
    back a PurchaseViewerVC with no merchandise_address / buyer_eth_addr /
    tx_hash / allowed_views, breaking the marketplace bridge."""
    tc, _ = client
    body = {
        "merchandise_address": "0x" + "77" * 20,
        "buyer_eth_addr": "0x" + "88" * 20,
        "tx_hash": "0x" + "99" * 32,
        "dataset_id": "home/env/temperature",
        "data_user_attrs": {
            "entityType": "GovernmentOrganization",
            "purpose": "research",
            "legalCompliance": True,
            "dataHandlingPolicy": "ISO27001",
            "misuseRecord": False,
        },
    }
    claim_resp = tc.post("/marketplace/claim", json=body).json()
    claim_id = claim_resp["claim_id"]
    deeplink_code = json.loads(__import__("urllib.parse").parse.unquote(
        claim_resp["deeplink"].split("=", 1)[1]
    ))["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"][
        "pre-authorized_code"
    ]

    offer = tc.get(
        "/issuer/offer",
        params={
            "type": "PurchaseViewerVC",
            "dataset_id": "home/env/temperature",
            "purpose": "read",
            "claim_id": claim_id,
        },
        headers={"accept": "application/json"},
    ).json()
    assert offer["pre_authorized_code"] == deeplink_code, (
        "the offer URL must reuse the claim's pre_authorized_code; "
        f"got {offer['pre_authorized_code']!r} != claim {deeplink_code!r}"
    )


def test_issuer_offer_unknown_claim_id_404(client):
    tc, _ = client
    r = tc.get(
        "/issuer/offer",
        params={
            "type": "PurchaseViewerVC",
            "dataset_id": "home/env/temperature",
            "purpose": "read",
            "claim_id": "nope-no-such-claim",
        },
        headers={"accept": "application/json"},
    )
    assert r.status_code == 404
    assert "unknown claim_id" in r.json()["detail"]


def test_pipeline_hoists_media_cids_to_top_level():
    """Stage T (case alpha): /platform/data's allowed_views projection
    only filters top-level keys. The pipeline must hoist image_cid /
    video_cid / video_duration_sec out of the inbound payload so the
    projection bites at Tier 2 / Tier 3.

    Tested at the MessageProcessor level so the test does not depend on
    a reachable platform/ingest endpoint.
    """
    from datetime import datetime, timezone, timedelta
    from publisher.app.pipeline import MessageProcessor
    from policy.engine import PolicyEngine
    from policy.store import ConsentStore
    from audit.repository import SQLiteAuditRepository
    from policy.models import ConsentVC
    import tempfile
    import os

    captured: list[dict] = []

    class _FakePlatformClient:
        def send(self, envelope: dict) -> None:
            captured.append(envelope)

    with tempfile.TemporaryDirectory() as td:
        consent_store = ConsentStore(os.path.join(td, "consents.json"))
        now = datetime.now(timezone.utc)
        consent_store.upsert(
            ConsentVC(
                vc_id="c-tier-test",
                subject_did="did:example:park",
                dataset_id="home/event/possible_littering",
                allowed_purposes=["community_cleaning"],
                retention_days=14,
                reshare_allowed=False,
                valid_from=now - timedelta(days=1),
                valid_to=now + timedelta(days=30),
                signature="x",
            )
        )
        audit_repo = SQLiteAuditRepository(os.path.join(td, "audit.db"))
        proc = MessageProcessor(
            publisher_id="test",
            default_purpose="community_cleaning",
            consent_store=consent_store,
            policy_engine=PolicyEngine(),
            audit_repo=audit_repo,
            platform_client=_FakePlatformClient(),
        )
        result = proc.process_message(
            "homeassistant/event/possible_littering",
            {
                "event_type": "possible_littering",
                "ts": "2026-04-29T09:00:00Z",
                "source": "edge_inference",
                "image_cid": "QmTopLevelImage",
                "data": {
                    "video_cid": "QmNestedVideo",
                    "video_duration_sec": 7,
                },
            },
            "community_cleaning",
        )
        assert result["status"] == "allowed", result
        assert captured, "platform_client.send was not called"
        env = captured[-1]
        assert env.get("image_cid") == "QmTopLevelImage", env
        assert env.get("video_cid") == "QmNestedVideo", env
        assert env.get("video_duration_sec") == 7, env


def test_marketplace_claim_picks_tier_aware_config_id(client):
    """Stage T (case alpha): the deeplink emitted by /marketplace/claim
    must reference the tier-specific credential_configuration_id so the
    wallet renders three distinct cards (Full / Image / Event-only)
    rather than three identical "PurchaseViewerVC" entries."""
    tc, _ = client

    cases = [
        (
            {
                "entityType": "GovernmentOrganization",
                "purpose": "research",
                "legalCompliance": True,
                "dataHandlingPolicy": "ISO27001",
                "misuseRecord": False,
            },
            "PurchaseViewerVC.full",
        ),
        (
            {
                "entityType": "Enterprise",
                "purpose": "research",
                "legalCompliance": True,
                "dataHandlingPolicy": "ISO27001",
                "misuseRecord": False,
            },
            "PurchaseViewerVC.access",
        ),
        (None, "PurchaseViewerVC.event"),
    ]
    for i, (attrs, expected_cfg_id) in enumerate(cases):
        body: dict = {
            "merchandise_address": f"0x{i:040x}",
            "buyer_eth_addr": f"0x{(i+100):040x}",
            "tx_hash": f"0x{(i+200):064x}",
            "dataset_id": "home/env/temperature",
        }
        if attrs:
            body["data_user_attrs"] = attrs
        resp = tc.post("/marketplace/claim", json=body).json()
        co = json.loads(__import__("urllib.parse").parse.unquote(
            resp["deeplink"].split("=", 1)[1]
        ))
        assert co["credential_configuration_ids"] == [expected_cfg_id], (
            f"case {i}: expected deeplink config_id {expected_cfg_id!r}, "
            f"got {co['credential_configuration_ids']!r}"
        )


def test_issuer_metadata_lists_three_purchase_viewer_tiers(client):
    tc, _ = client
    md = tc.get("/.well-known/openid-credential-issuer").json()
    cfgs = md["credential_configurations_supported"]
    for cfg_id in (
        "PurchaseViewerVC",
        "PurchaseViewerVC.full",
        "PurchaseViewerVC.access",
        "PurchaseViewerVC.event",
    ):
        assert cfg_id in cfgs, cfgs.keys()
        assert cfgs[cfg_id]["vct"] == "https://iw3ip.example/credentials/PurchaseViewerVC/v1"
    # The three tiered entries must have distinct display names so the
    # wallet renders distinct cards.
    names = {
        cfg_id: cfgs[cfg_id]["display"][0]["name"]
        for cfg_id in (
            "PurchaseViewerVC.full",
            "PurchaseViewerVC.access",
            "PurchaseViewerVC.event",
        )
    }
    assert len(set(names.values())) == 3, names


def test_purchase_viewer_vc_includes_subject_id(client):
    """Regression for "No Available Credential" in iw3ip-wallet: the
    verifier DCQL requires `subject_id`, so the issuer must bake the
    holder DID into the credential plain claims."""
    tc, _ = client
    body = {
        "merchandise_address": "0x" + "aa" * 20,
        "buyer_eth_addr": "0x" + "bb" * 20,
        "tx_hash": "0x" + "cc" * 32,
        "dataset_id": "home/env/temperature",
    }
    claim_resp = tc.post("/marketplace/claim", json=body).json()
    pre_auth = json.loads(__import__("urllib.parse").parse.unquote(
        claim_resp["deeplink"].split("=", 1)[1]
    ))["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"][
        "pre-authorized_code"
    ]

    priv, pub, holder_did = _holder()
    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    proof = _proof(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    # The SD-JWT VC's body claim set is recoverable by parsing the
    # <issuer-jwt>~<disclosure>~... compact form.
    sdjwt = cred["credential"]
    parts = sdjwt.split("~")
    issuer_jwt_payload = parts[0].split(".")[1]
    import base64
    pad = "=" * (-len(issuer_jwt_payload) % 4)
    body_claims = json.loads(
        base64.urlsafe_b64decode(issuer_jwt_payload + pad)
    )
    # Disclosures (one per ~ segment after the issuer JWT, except the
    # trailing kb-jwt slot which may be empty in this fixture).
    disclosed: dict = {}
    for d in parts[1:-1] if parts[-1] == "" else parts[1:]:
        if not d:
            continue
        pad = "=" * (-len(d) % 4)
        try:
            arr = json.loads(base64.urlsafe_b64decode(d + pad))
            if isinstance(arr, list) and len(arr) >= 3:
                disclosed[arr[1]] = arr[2]
        except Exception:
            continue

    # subject_id must appear either as a top-level claim or as a
    # disclosure, and must equal holder_did.
    sid = body_claims.get("subject_id") or disclosed.get("subject_id")
    assert sid == holder_did, (
        f"PurchaseViewerVC must carry subject_id == holder_did "
        f"({holder_did!r}); got top={body_claims.get('subject_id')!r}, "
        f"disclosed={disclosed.get('subject_id')!r}"
    )


# ---- Stage T case B: media gateway + URL-based tier projection ----


def _tiny_jpeg() -> bytes:
    # 1×1 white-pixel JPEG (smallest legal JPEG; 125 bytes).
    return bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605"
        "08070707090908090a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a"
        "0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0affc0000b08"
        "00010001010100ffc4001500010100000000000000000000000000000007ff"
        "c4001f10000103030301010100000000000000010002030405060708ffd900"
    )


def _multipart_body(filename: str, content_type: str, blob: bytes) -> tuple[bytes, str]:
    boundary = "----iw3ip-test-boundary"
    crlf = b"\r\n"
    parts = [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
        f"Content-Type: {content_type}".encode(),
        b"",
        blob,
        f"--{boundary}--".encode(),
        b"",
    ]
    body = crlf.join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def test_media_upload_then_serve(client):
    tc, _ = client
    blob = _tiny_jpeg()
    body, ct = _multipart_body("frame.jpg", "image/jpeg", blob)
    r = tc.post("/media/upload", content=body, headers={"Content-Type": ct})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["sha256"] == hashlib.sha256(blob).hexdigest()
    assert j["content_type"] == "image/jpeg"
    assert j["byte_size"] == len(blob)
    assert j["url"].endswith(f"/media/{j['sha256']}.jpg")

    # The published URL should resolve. TestClient sees the full origin.
    relative = "/media/" + j["sha256"] + ".jpg"
    r2 = tc.get(relative)
    assert r2.status_code == 200
    assert r2.content == blob
    assert r2.headers["content-type"].startswith("image/jpeg")


def test_media_upload_dedupes_on_sha256(client):
    tc, _ = client
    blob = _tiny_jpeg()
    body, ct = _multipart_body("a.jpg", "image/jpeg", blob)
    r1 = tc.post("/media/upload", content=body, headers={"Content-Type": ct}).json()
    body2, _ = _multipart_body("b-different-name.jpg", "image/jpeg", blob)
    r2 = tc.post("/media/upload", content=body2, headers={"Content-Type": ct}).json()
    assert r1["sha256"] == r2["sha256"]
    assert r1["url"] == r2["url"]


def test_media_upload_rejects_unknown_extension(client):
    tc, _ = client
    body, ct = _multipart_body("payload.exe", "application/octet-stream", b"\x00" * 32)
    r = tc.post("/media/upload", content=body, headers={"Content-Type": ct})
    assert r.status_code == 415


def test_media_get_rejects_path_traversal(client):
    tc, _ = client
    # urls with embedded slashes never match the path; this is a belt-and-braces check
    r = tc.get("/media/..%2Fauth")
    assert r.status_code in (400, 404)


def test_platform_data_projects_image_url_video_url_per_tier(client):
    """The Tier 2 / 3 buyer should see image_url; only Tier 3 should
    additionally see video_url. Tier 1 sees neither."""
    tc, pm = client
    # Seed a row that uses URL-based media (case B), not CID-based.
    pm.app.state.ingested.append({
        "dataset_id": "home/env/temperature",
        "event_type": "tick",
        "data": {"value": 9},
        "image_url": "http://testserver/media/aaaaaaa.jpg",
        "video_url": "http://testserver/media/bbbbbbb.mp4",
        "video_duration_sec": 4,
    })

    # Tier 3 — full
    presented = _purchase_viewer_token(
        tc, allowed_views_in_claim=["event", "image", "video"], tx_seed="71"
    )
    body = tc.get(
        "/platform/data",
        params={"dataset_id": "home/env/temperature"},
        headers={"Authorization": f"Bearer {presented['viewer_token']}"},
    ).json()
    row = body["rows"][0]
    assert row.get("image_url", "").endswith("/aaaaaaa.jpg")
    assert row.get("video_url", "").endswith("/bbbbbbb.mp4")
    assert row.get("video_duration_sec") == 4

    # Tier 2 — image only (different tx_seed → fresh claim/offer)
    presented2 = _purchase_viewer_token(
        tc, allowed_views_in_claim=["event", "image"], tx_seed="72"
    )
    body2 = tc.get(
        "/platform/data",
        params={"dataset_id": "home/env/temperature"},
        headers={"Authorization": f"Bearer {presented2['viewer_token']}"},
    ).json()
    row2 = body2["rows"][0]
    assert row2.get("image_url", "").endswith("/aaaaaaa.jpg")
    assert "video_url" not in row2
    assert "video_duration_sec" not in row2


def test_pipeline_hoists_image_url_video_url_to_top_level():
    """/simulate/publish should hoist image_url / video_url out of the
    payload exactly the same way it hoists image_cid / video_cid."""
    from datetime import datetime, timezone, timedelta
    from publisher.app.pipeline import MessageProcessor
    from policy.engine import PolicyEngine
    from policy.store import ConsentStore
    from policy.models import ConsentVC
    from audit.repository import SQLiteAuditRepository
    import tempfile
    import os

    captured: list[dict] = []

    class _Sink:
        def send(self, env: dict) -> None:
            captured.append(env)

    with tempfile.TemporaryDirectory() as td:
        cs = ConsentStore(os.path.join(td, "c.json"))
        now = datetime.now(timezone.utc)
        cs.upsert(
            ConsentVC(
                vc_id="c-stage-t-b",
                subject_did="did:example:park",
                dataset_id="home/event/possible_littering",
                allowed_purposes=["community_cleaning"],
                retention_days=14,
                reshare_allowed=False,
                valid_from=now - timedelta(days=1),
                valid_to=now + timedelta(days=30),
                signature="x",
            )
        )
        proc = MessageProcessor(
            publisher_id="t",
            default_purpose="community_cleaning",
            consent_store=cs,
            policy_engine=PolicyEngine(),
            audit_repo=SQLiteAuditRepository(os.path.join(td, "a.db")),
            platform_client=_Sink(),
        )
        result = proc.process_message(
            "homeassistant/event/possible_littering",
            {
                "event_type": "possible_littering",
                "ts": "2026-04-29T09:00:00Z",
                "source": "edge_inference",
                "image_url": "http://publisher:8080/media/aaa.jpg",
                "data": {
                    "video_url": "http://publisher:8080/media/bbb.mp4",
                    "video_duration_sec": 4,
                },
            },
            "community_cleaning",
        )
        assert result["status"] == "allowed", result
        assert captured
        env = captured[-1]
        assert env.get("image_url") == "http://publisher:8080/media/aaa.jpg"
        assert env.get("video_url") == "http://publisher:8080/media/bbb.mp4"
        assert env.get("video_duration_sec") == 4
