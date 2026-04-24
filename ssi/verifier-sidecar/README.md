# iw3ip-verifier-sidecar

Node.js sidecar that runs SD-JWT VC signature verification and
`@sphereon/pex` Presentation Exchange v2 evaluation on behalf of the
Python publisher.

The publisher posts to `POST /verify` with the VP token and submission
received from the wallet, plus the presentation definition and issuer
public JWK; the sidecar returns `{verified, reason, claims, holder_did}`.

Run standalone:

```bash
npm install
PORT=7000 npm start
```

In Compose, it is started via the `ssi-wallet` profile.
