"""In-memory state for OID4VCI offers and OID4VP requests.

Hands-on scale only; not suitable for multi-worker deployments. State is lost
on restart — re-issue the VC from the wallet flow. For the target scenario
(one publisher container, one wallet), this is adequate.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field


@dataclass
class Offer:
    pre_authorized_code: str
    credential_config_id: str
    dataset_id: str
    purpose: str
    allowed_purposes: list[str]
    created_at: float
    consumed: bool = False


@dataclass
class AccessToken:
    token: str
    pre_authorized_code: str
    c_nonce: str
    created_at: float


@dataclass
class VerificationRequest:
    request_id: str
    state: str
    nonce: str
    presentation_definition_id: str
    dataset_id: str
    purpose: str
    created_at: float
    result: dict | None = None


class SSIStateStore:
    def __init__(self, offer_ttl: int = 600, response_ttl: int = 600) -> None:
        self._lock = threading.Lock()
        self._offers: dict[str, Offer] = {}
        self._tokens: dict[str, AccessToken] = {}
        self._requests: dict[str, VerificationRequest] = {}
        self._offer_ttl = offer_ttl
        self._response_ttl = response_ttl

    # ---- OID4VCI ----

    def create_offer(
        self,
        credential_config_id: str,
        dataset_id: str,
        purpose: str,
        allowed_purposes: list[str],
    ) -> Offer:
        code = secrets.token_urlsafe(24)
        offer = Offer(
            pre_authorized_code=code,
            credential_config_id=credential_config_id,
            dataset_id=dataset_id,
            purpose=purpose,
            allowed_purposes=allowed_purposes,
            created_at=time.time(),
        )
        with self._lock:
            self._offers[code] = offer
        return offer

    def consume_offer(self, code: str) -> Offer | None:
        with self._lock:
            offer = self._offers.get(code)
            if not offer or offer.consumed:
                return None
            if time.time() - offer.created_at > self._offer_ttl:
                return None
            offer.consumed = True
            return offer

    def issue_token(self, offer: Offer) -> AccessToken:
        token = AccessToken(
            token=secrets.token_urlsafe(32),
            pre_authorized_code=offer.pre_authorized_code,
            c_nonce=secrets.token_urlsafe(16),
            created_at=time.time(),
        )
        with self._lock:
            self._tokens[token.token] = token
        return token

    def get_token(self, token: str) -> AccessToken | None:
        with self._lock:
            t = self._tokens.get(token)
            if not t:
                return None
            if time.time() - t.created_at > self._offer_ttl:
                return None
            return t

    def get_offer_for_token(self, token: AccessToken) -> Offer | None:
        with self._lock:
            return self._offers.get(token.pre_authorized_code)

    # ---- OID4VP ----

    def create_verification_request(
        self,
        presentation_definition_id: str,
        dataset_id: str,
        purpose: str,
    ) -> VerificationRequest:
        req = VerificationRequest(
            request_id=secrets.token_urlsafe(16),
            state=secrets.token_urlsafe(16),
            nonce=secrets.token_urlsafe(16),
            presentation_definition_id=presentation_definition_id,
            dataset_id=dataset_id,
            purpose=purpose,
            created_at=time.time(),
        )
        with self._lock:
            self._requests[req.state] = req
        return req

    def find_verification_request(self, state: str) -> VerificationRequest | None:
        with self._lock:
            req = self._requests.get(state)
            if not req:
                return None
            if time.time() - req.created_at > self._response_ttl:
                return None
            return req

    def record_verification_result(self, state: str, result: dict) -> None:
        with self._lock:
            req = self._requests.get(state)
            if req:
                req.result = result
