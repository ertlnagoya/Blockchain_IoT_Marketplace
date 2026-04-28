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


@dataclass
class MarketplaceClaim:
    """Bridge-recorded purchase context that maps an Ethereum tx to an
    OID4VCI offer (M2 / v2). M3 grafts the eth_addr <-> did:jwk binding
    on top by recording the holder_did once the wallet completes
    credential receipt.
    """
    claim_id: str
    pre_authorized_code: str
    merchandise_address: str
    buyer_eth_addr: str
    tx_hash: str
    dataset_id: str
    purchase_amount_wei: str
    created_at: float
    holder_did: str | None = None  # filled in M3 once wallet receives the VC


@dataclass
class ServiceToken:
    """M2M write counterpart to PolicyToken (Stage 4 prep).

    Long-lived (default 1 h) and multi-use, suited to a continuous
    MQTT publisher that holds a ServiceVC and writes many events under
    a single presentation. Each ingest under the token increments
    `write_count`.
    """
    jti: str
    token: str
    dataset_id: str
    holder_did: str | None
    issued_at: float
    expires_at: float
    write_count: int = 0


class SSIStateStore:
    def __init__(
        self,
        offer_ttl: int = 600,
        response_ttl: int = 600,
        policy_token_ttl: int = 300,
        viewer_token_ttl: int = 60,
        service_token_ttl: int = 3600,
    ) -> None:
        self._lock = threading.Lock()
        self._offers: dict[str, Offer] = {}
        self._tokens: dict[str, AccessToken] = {}
        self._requests: dict[str, VerificationRequest] = {}
        self._policy_tokens: dict[str, PolicyToken] = {}
        self._viewer_tokens: dict[str, ViewerToken] = {}
        self._service_tokens: dict[str, ServiceToken] = {}
        self._marketplace_claims: dict[str, MarketplaceClaim] = {}
        self._marketplace_claims_by_tx: dict[str, MarketplaceClaim] = {}
        # M4: merchandise_address -> dataset_id, populated from claims so
        # /platform/data?merchandise=<addr> can resolve a dataset without
        # asking the buyer to type it.
        self._merchandise_dataset: dict[str, str] = {}
        self._offer_ttl = offer_ttl
        self._response_ttl = response_ttl
        self._policy_token_ttl = policy_token_ttl
        self._viewer_token_ttl = viewer_token_ttl
        self._service_token_ttl = service_token_ttl

    @property
    def policy_token_ttl(self) -> int:
        return self._policy_token_ttl

    @property
    def viewer_token_ttl(self) -> int:
        return self._viewer_token_ttl

    @property
    def service_token_ttl(self) -> int:
        return self._service_token_ttl

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

    # ---- ServiceToken (Stage 4 prep) ----

    def create_service_token(
        self,
        *,
        dataset_id: str,
        holder_did: str | None,
    ) -> ServiceToken:
        now = time.time()
        st = ServiceToken(
            jti=secrets.token_hex(8),
            token=secrets.token_urlsafe(32),
            dataset_id=dataset_id,
            holder_did=holder_did,
            issued_at=now,
            expires_at=now + self._service_token_ttl,
        )
        with self._lock:
            self._service_tokens[st.token] = st
        return st

    def use_service_token(
        self,
        token: str,
        *,
        dataset_id: str,
    ) -> tuple[ServiceToken | None, str]:
        """Return (token, reason). Reason: ok, unknown, expired, dataset_mismatch.

        Multi-use within TTL — every ingest call increments write_count.
        """
        with self._lock:
            st = self._service_tokens.get(token)
            if not st:
                return None, "unknown"
            if time.time() > st.expires_at:
                return None, "expired"
            if st.dataset_id != dataset_id:
                return None, "dataset_mismatch"
            st.write_count += 1
            return st, "ok"

    def get_service_token(self, token: str) -> ServiceToken | None:
        with self._lock:
            return self._service_tokens.get(token)

    # ---- MarketplaceClaim (v2 / M2) ----
    # Each Purchase event from the bridge becomes one MarketplaceClaim.
    # Idempotent on tx_hash: replaying the same Purchase returns the
    # existing claim instead of double-issuing.

    def create_marketplace_claim(
        self,
        *,
        merchandise_address: str,
        buyer_eth_addr: str,
        tx_hash: str,
        dataset_id: str,
        purchase_amount_wei: str,
    ) -> tuple[MarketplaceClaim, bool]:
        """Return (claim, created). created=False means we returned the
        previously-recorded claim for this tx_hash (idempotent)."""
        with self._lock:
            existing = self._marketplace_claims_by_tx.get(tx_hash)
            if existing:
                return existing, False
            claim = MarketplaceClaim(
                claim_id=secrets.token_hex(8),
                pre_authorized_code=secrets.token_urlsafe(24),
                merchandise_address=merchandise_address,
                buyer_eth_addr=buyer_eth_addr,
                tx_hash=tx_hash,
                dataset_id=dataset_id,
                purchase_amount_wei=purchase_amount_wei,
                created_at=time.time(),
            )
            self._marketplace_claims[claim.claim_id] = claim
            self._marketplace_claims_by_tx[tx_hash] = claim
            # M4: opportunistically index merchandise -> dataset_id
            self._merchandise_dataset[merchandise_address.lower()] = dataset_id
        return claim, True

    def dataset_for_merchandise(self, merchandise_address: str) -> str | None:
        with self._lock:
            return self._merchandise_dataset.get(merchandise_address.lower())

    def get_marketplace_claim(self, claim_id: str) -> MarketplaceClaim | None:
        with self._lock:
            return self._marketplace_claims.get(claim_id)

    def find_marketplace_claim_by_code(
        self, pre_authorized_code: str
    ) -> MarketplaceClaim | None:
        with self._lock:
            for c in self._marketplace_claims.values():
                if c.pre_authorized_code == pre_authorized_code:
                    return c
            return None

    def attach_holder_to_claim(
        self, claim_id: str, holder_did: str
    ) -> MarketplaceClaim | None:
        """M3 hook: record eth_addr <-> did:jwk binding once a wallet
        finishes credential receipt for the claim."""
        with self._lock:
            c = self._marketplace_claims.get(claim_id)
            if c:
                c.holder_did = holder_did
            return c
