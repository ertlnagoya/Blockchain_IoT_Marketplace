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
    # Stage 3: distinguishes ConsentVC (write authz) from ViewerVC (read authz)
    vc_kind: str = "ConsentVC"


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
    vc_kind: str = "ConsentVC"


@dataclass
class PolicyToken:
    jti: str
    token: str
    dataset_id: str
    purpose: str
    holder_did: str | None
    issued_at: float
    expires_at: float
    consumed_at: float | None = None


@dataclass
class ViewerToken:
    """Read-side counterpart to PolicyToken.

    Re-usable within TTL (viewing is continuous), unlike PolicyToken which
    is single-use. Each successful /platform/data read bumps `read_count`.
    """
    jti: str
    token: str
    dataset_id: str
    holder_did: str | None
    issued_at: float
    expires_at: float
    read_count: int = 0


class SSIStateStore:
    def __init__(
        self,
        offer_ttl: int = 600,
        response_ttl: int = 600,
        policy_token_ttl: int = 300,
        viewer_token_ttl: int = 60,
    ) -> None:
        self._lock = threading.Lock()
        self._offers: dict[str, Offer] = {}
        self._tokens: dict[str, AccessToken] = {}
        self._requests: dict[str, VerificationRequest] = {}
        self._policy_tokens: dict[str, PolicyToken] = {}
        self._viewer_tokens: dict[str, ViewerToken] = {}
        self._offer_ttl = offer_ttl
        self._response_ttl = response_ttl
        self._policy_token_ttl = policy_token_ttl
        self._viewer_token_ttl = viewer_token_ttl

    @property
    def policy_token_ttl(self) -> int:
        return self._policy_token_ttl

    @property
    def viewer_token_ttl(self) -> int:
        return self._viewer_token_ttl

    # ---- OID4VCI ----

    def create_offer(
        self,
        credential_config_id: str,
        dataset_id: str,
        purpose: str,
        allowed_purposes: list[str],
        vc_kind: str = "ConsentVC",
    ) -> Offer:
        code = secrets.token_urlsafe(24)
        offer = Offer(
            pre_authorized_code=code,
            credential_config_id=credential_config_id,
            dataset_id=dataset_id,
            purpose=purpose,
            allowed_purposes=allowed_purposes,
            created_at=time.time(),
            vc_kind=vc_kind,
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
        vc_kind: str = "ConsentVC",
    ) -> VerificationRequest:
        req = VerificationRequest(
            request_id=secrets.token_urlsafe(16),
            state=secrets.token_urlsafe(16),
            nonce=secrets.token_urlsafe(16),
            presentation_definition_id=presentation_definition_id,
            dataset_id=dataset_id,
            purpose=purpose,
            created_at=time.time(),
            vc_kind=vc_kind,
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

    # ---- PolicyToken ----
    # TODO: in-memory only; will not survive across publisher replicas.
    # Move to a shared cache (Redis) or signed JWT before scaling out.

    def create_policy_token(
        self,
        *,
        dataset_id: str,
        purpose: str,
        holder_did: str | None,
    ) -> PolicyToken:
        now = time.time()
        pt = PolicyToken(
            jti=secrets.token_hex(8),
            token=secrets.token_urlsafe(32),
            dataset_id=dataset_id,
            purpose=purpose,
            holder_did=holder_did,
            issued_at=now,
            expires_at=now + self._policy_token_ttl,
        )
        with self._lock:
            self._policy_tokens[pt.token] = pt
        return pt

    def consume_policy_token(
        self,
        token: str,
        *,
        dataset_id: str,
    ) -> tuple[PolicyToken | None, str]:
        """Return (token, reason). On success reason="ok"; otherwise a short code.

        Reasons: unknown, expired, already_consumed, dataset_mismatch.
        """
        with self._lock:
            pt = self._policy_tokens.get(token)
            if not pt:
                return None, "unknown"
            if time.time() > pt.expires_at:
                return None, "expired"
            if pt.consumed_at is not None:
                return None, "already_consumed"
            if pt.dataset_id != dataset_id:
                return None, "dataset_mismatch"
            pt.consumed_at = time.time()
            return pt, "ok"

    def get_policy_token(self, token: str) -> PolicyToken | None:
        with self._lock:
            return self._policy_tokens.get(token)

    # ---- ViewerToken (Stage 3) ----

    def create_viewer_token(
        self,
        *,
        dataset_id: str,
        holder_did: str | None,
    ) -> ViewerToken:
        now = time.time()
        vt = ViewerToken(
            jti=secrets.token_hex(8),
            token=secrets.token_urlsafe(32),
            dataset_id=dataset_id,
            holder_did=holder_did,
            issued_at=now,
            expires_at=now + self._viewer_token_ttl,
        )
        with self._lock:
            self._viewer_tokens[vt.token] = vt
        return vt

    def use_viewer_token(
        self,
        token: str,
        *,
        dataset_id: str,
    ) -> tuple[ViewerToken | None, str]:
        """Return (token, reason). Reason: ok, unknown, expired, dataset_mismatch.

        Multi-use within TTL: increments read_count instead of marking consumed.
        """
        with self._lock:
            vt = self._viewer_tokens.get(token)
            if not vt:
                return None, "unknown"
            if time.time() > vt.expires_at:
                return None, "expired"
            if vt.dataset_id != dataset_id:
                return None, "dataset_mismatch"
            vt.read_count += 1
            return vt, "ok"

    def get_viewer_token(self, token: str) -> ViewerToken | None:
        with self._lock:
            return self._viewer_tokens.get(token)
