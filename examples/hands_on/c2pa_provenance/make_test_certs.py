"""Generate a private test CA and an ES256 gateway signing certificate for C2PA.

Stage P (C2PA provenance) P0 helper. The C2PA SDK refuses certificates
that are self-signed, signed with SHA-1, or lack an extended key usage,
so this script builds a CA -> leaf chain that satisfies those rules.

Usage:
    uv run --no-project --with c2pa-python --with pillow --with cryptography \
        python examples/hands_on/c2pa_provenance/make_test_certs.py

Writes ``certs/`` next to this file:
    ca.pem       test CA certificate (register it as a trust anchor)
    gw.key       gateway private key (PKCS#8 PEM, test use only)
    chain.pem    gateway certificate + CA certificate (passed to the signer)

The keys are for local experiments only. Never use them in production.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


HERE = Path(__file__).resolve().parent


def _name(cn: str) -> x509.Name:
    return x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IW3IP"),
    ])


def build(out_dir: Path, gateway_cn: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)

    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = _name("IW3IP Test CA")
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())  # SHA-1 is rejected by the SDK
    )

    gw_key = ec.generate_private_key(ec.SECP256R1())
    gw_cert = (
        x509.CertificateBuilder()
        .subject_name(_name(gateway_cn))
        .issuer_name(ca_name)
        .public_key(gw_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=180))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False, crl_sign=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        # C2PA requires an EKU on the signing certificate
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(gw_key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )

    pem = serialization.Encoding.PEM
    (out_dir / "ca.pem").write_bytes(ca_cert.public_bytes(pem))
    (out_dir / "chain.pem").write_bytes(gw_cert.public_bytes(pem) + ca_cert.public_bytes(pem))
    (out_dir / "gw.key").write_bytes(
        gw_key.private_bytes(pem, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    print(f"wrote {out_dir}/ca.pem, chain.pem, gw.key (CN={gateway_cn})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "certs")
    # the CN stays in every Tier 2 derivative and cannot be redacted, so keep the camera ID out of it
    parser.add_argument("--gateway-cn", default="iw3ip-gateway")
    args = parser.parse_args()
    build(args.out, args.gateway_cn)


if __name__ == "__main__":
    main()
