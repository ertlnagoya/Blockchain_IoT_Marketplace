"""Stage P (C2PA provenance) — verify uploads and sign Tier 2 derivatives.

P1 (docs/design/c2pa-provenance-spec §7.1): ``/media/upload`` reads the
C2PA manifest of an image with the CAI SDK (c2pa-python) and returns
``{present, manifest_label, validation_state, signer, trusted}``. A
manifest whose hashes or signature do not match is ``Invalid`` and the
upload is refused (``400 c2pa_invalid``); a file without a manifest is
accepted as before (``present: false``).

P2 (spec §5.3): when the publisher blurs a signed image for Tier 2 it
signs the blurred bytes with its own certificate, references the
capture as a ``parentOf`` ingredient, and redacts the capture's
thumbnail, camera and sensor assertions so Tier 2 recipients learn only
that the image was made from a signed original.

Redaction cannot remove the capture manifest's title or the signer
certificate (C2PA Security Considerations §4.3.5.1 / §4.3.5.2), so the
gateway must keep the camera ID out of both (spec §5.2 / §6.1).

c2pa-python is imported lazily so the publisher still boots, and every
other test still runs, on machines without the SDK; ``C2PA_ENABLED``
turns the feature on.
"""
from __future__ import annotations

import io
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Images the SDK can sign and read in this MVP. Video (fragmented MP4) is P3.
SUPPORTED_TYPES = {"image/jpeg", "image/png"}

# Leading bytes of the supported formats. The type is taken from the
# bytes, not the filename, so renaming a tampered JPEG to .webp does not
# skip the check.
_MAGIC = ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"))


def sniff_type(body: bytes) -> str | None:
    """Return the image type of ``body`` from its leading bytes, or None."""
    for magic, content_type in _MAGIC:
        if body.startswith(magic):
            return content_type
    return None

# Capture assertions that must not reach Tier 2 recipients (spec §5.3).
REDACT_LABELS = (
    "c2pa.thumbnail.claim",
    "jp.ertl.iw3ip.capture",
    "jp.ertl.iw3ip.sensor",
)


class ProvenanceError(Exception):
    """Any C2PA failure the caller should turn into a warning or 4xx."""


class ProvenanceDependencyMissing(ProvenanceError):
    """C2PA_ENABLED is set but c2pa-python is not installed."""


@dataclass
class VerifyResult:
    present: bool
    manifest_label: str | None = None
    validation_state: str | None = None
    signer: str | None = None
    trusted: bool = False
    failure_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["failure_codes"] = list(self.failure_codes)
        return d


def _import_c2pa():
    try:
        import c2pa  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ProvenanceDependencyMissing(
            "C2PA_ENABLED requires c2pa-python. Install it in the publisher "
            "image (`pip install c2pa-python`) or unset C2PA_ENABLED."
        ) from exc
    return c2pa


class C2paProvenance:
    """Verify manifests against a trust anchor and sign Tier 2 derivatives.

    Construct via ``C2paProvenance.from_settings(settings)``; it returns
    ``None`` when C2PA is disabled so callers can branch on ``is None``.
    Signing needs ``c2pa_signer_chain_path`` / ``c2pa_signer_key_path``;
    without them the publisher still verifies uploads but skips P2.
    """

    def __init__(
        self,
        *,
        trust_anchors_pem: str = "",
        signer_chain_pem: str = "",
        signer_key_pem: bytes = b"",
    ) -> None:
        self._c2pa = _import_c2pa()
        settings: dict = {"verify": {"verify_trust": True}}
        if trust_anchors_pem:
            settings["trust"] = {"user_anchors": trust_anchors_pem}
        self._context = self._c2pa.Context(self._c2pa.Settings.from_dict(settings))
        self._signer_chain_pem = signer_chain_pem
        self._signer_key_pem = signer_key_pem

    @classmethod
    def from_settings(cls, settings) -> "C2paProvenance | None":
        if not settings.c2pa_enabled:
            return None

        def _read(path: str) -> str:
            return Path(path).read_text() if path else ""

        return cls(
            trust_anchors_pem=_read(settings.c2pa_trust_anchors_path),
            signer_chain_pem=_read(settings.c2pa_signer_chain_path),
            signer_key_pem=(
                Path(settings.c2pa_signer_key_path).read_bytes()
                if settings.c2pa_signer_key_path
                else b""
            ),
        )

    @property
    def can_sign(self) -> bool:
        return bool(self._signer_chain_pem and self._signer_key_pem)

    # ---- P1: verification ----

    def verify(self, body: bytes, content_type: str | None = None) -> VerifyResult:
        """Read the manifest store of ``body``.

        The type is sniffed from the bytes; ``content_type`` (from the
        filename or upload header) is ignored for that reason. Returns
        ``present=False`` for other formats and for files without a
        manifest. ``validation_state`` is the SDK's ``Invalid`` /
        ``Valid`` / ``Trusted``; ``Valid`` with
        ``signingCredential.untrusted`` means the signer's CA is not a
        configured trust anchor. A manifest the SDK cannot parse at all
        is reported as ``Invalid`` (``c2pa.unreadable``), not as absent.
        """
        sniffed = sniff_type(body)
        if sniffed is None:
            return VerifyResult(present=False)
        try:
            reader = self._c2pa.Reader(
                sniffed, io.BytesIO(body), context=self._context
            )
        except Exception as exc:  # noqa: BLE001 - the SDK raises its own types
            if type(exc).__name__.endswith("ManifestNotFound"):
                return VerifyResult(present=False)
            # A manifest is embedded but broken (e.g. its JUMBF was cut):
            # refuse it like a hash mismatch instead of treating it as unsigned.
            logger.info("c2pa reader: unreadable manifest (%s)", exc)
            return VerifyResult(
                present=True,
                validation_state="Invalid",
                failure_codes=("c2pa.unreadable",),
            )
        with reader:
            state = reader.get_validation_state()
            store = json.loads(reader.json())
        label = store.get("active_manifest")
        manifest = (store.get("manifests") or {}).get(label or "", {})
        info = manifest.get("signature_info") or {}
        codes = tuple(
            s.get("code", "")
            for s in (store.get("validation_status") or [])
        )
        return VerifyResult(
            present=True,
            manifest_label=label,
            validation_state=state,
            signer=info.get("common_name"),
            trusted=state == "Trusted",
            failure_codes=codes,
        )

    # ---- P2: Tier 2 derivative ----

    def sign_tier2(
        self,
        *,
        source: bytes,
        derived: bytes,
        content_type: str,
        kind: str = "face_blur",
        title: str = "tier2.jpg",
    ) -> bytes:
        """Sign ``derived`` with a manifest that references ``source``.

        The capture's thumbnail and the ``jp.ertl.iw3ip.capture`` /
        ``jp.ertl.iw3ip.sensor`` assertions are redacted from the
        ingredient (spec §5.3); only labels actually present in the
        capture manifest are listed, because the SDK refuses to redact
        an assertion that does not exist.
        """
        if not self.can_sign:
            raise ProvenanceError("publisher signer is not configured")
        c2pa = self._c2pa
        with c2pa.Reader(content_type, io.BytesIO(source), context=self._context) as r:
            store = json.loads(r.json())
        cap_label = store.get("active_manifest")
        if not cap_label:
            raise ProvenanceError("source has no active manifest")
        cap_manifest = store["manifests"][cap_label]
        present = {a.get("label") for a in cap_manifest.get("assertions", [])}
        if cap_manifest.get("thumbnail"):
            present.add("c2pa.thumbnail.claim")
        redactions = [
            f"self#jumbf=/c2pa/{cap_label}/c2pa.assertions/{lab}"
            for lab in REDACT_LABELS
            if lab in present
        ]
        definition = {
            "claim_generator_info": [{"name": "iw3ip-publisher", "version": "0.1.0"}],
            "title": title,
            "assertions": [
                {"label": "c2pa.actions", "data": {"actions": [
                    # the SDK refuses a first action other than created / opened
                    {"action": "c2pa.opened", "parameters": {"ingredientIds": ["capture"]}},
                    {"action": "c2pa.edited", "parameters": {"description": kind}},
                    # the SDK does not add c2pa.redacted by itself
                    *(
                        {"action": "c2pa.redacted", "reason": "c2pa.PII.present",
                         "parameters": {"redacted": uri}}
                        for uri in redactions
                    ),
                ]}},
                {"label": "jp.ertl.iw3ip.derivation", "data": {"tier": 2, "kind": kind}},
            ],
            "redactions": redactions,
        }
        out = io.BytesIO()
        with c2pa.Builder(definition) as builder:
            builder.add_ingredient(
                {"title": "capture", "relationship": "parentOf", "label": "capture"},
                content_type,
                io.BytesIO(source),
            )
            builder.sign(self._signer(), content_type, io.BytesIO(derived), out)
        return out.getvalue()

    def _signer(self):
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

        key = serialization.load_pem_private_key(self._signer_key_pem, None)

        def sign(data: bytes) -> bytes:
            # COSE ES256 signatures are raw r||s (64 bytes)
            r, s = decode_dss_signature(key.sign(data, ec.ECDSA(hashes.SHA256())))
            return r.to_bytes(32, "big") + s.to_bytes(32, "big")

        return self._c2pa.Signer.from_callback(
            sign, self._c2pa.C2paSigningAlg.ES256, self._signer_chain_pem, None
        )


# ---- sidecar records ----
# /media/upload stores the verification result as .c2pa/<sha256>.json
# under the media store so the pipeline (which only sees image_url) can
# attach provenance to the event row without re-reading the image. The
# sub-directory is never served: GET /media/<name> rejects names that
# start with "." or contain "/", and the result holds the signer name,
# which only some tiers may see.


def sidecar_path(store: Path, sha256: str) -> Path:
    return store / ".c2pa" / f"{sha256}.json"


def write_sidecar(store: Path, sha256: str, result: VerifyResult) -> None:
    path = sidecar_path(store, sha256)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict()))


def read_sidecar_for_url(store: Path, url: str | None) -> dict | None:
    """Return the stored verification result for a ``/media/<sha>.<ext>``
    URL, or None when the URL is not publisher-hosted or was uploaded
    while C2PA was off."""
    if not url or "/media/" not in url:
        return None
    name = url.split("?", 1)[0].rsplit("/media/", 1)[1]
    sha = name.split(".", 1)[0]
    if len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
        return None
    path = sidecar_path(store, sha)
    if not path.is_file():
        return None
    return json.loads(path.read_text())
