from __future__ import annotations

import httpx


class PEXSidecarClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def verify(
        self,
        *,
        presentation_definition: dict,
        vp_token: str,
        presentation_submission: dict,
        issuer_public_jwk: dict,
        expected_nonce: str,
        expected_aud: str,
    ) -> dict:
        """Ask the sidecar to run @sphereon/pex against the submission.

        Returns {"verified": bool, "reason": str, "claims": dict, "holder_did": str | None}.
        Network failures raise; caller decides fallback behavior.
        """
        payload = {
            "presentation_definition": presentation_definition,
            "vp_token": vp_token,
            "presentation_submission": presentation_submission,
            "issuer_public_jwk": issuer_public_jwk,
            "expected_nonce": expected_nonce,
            "expected_aud": expected_aud,
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(f"{self._base}/verify", json=payload)
            resp.raise_for_status()
            return resp.json()
