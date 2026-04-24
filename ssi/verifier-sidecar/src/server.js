import express from "express";
import { PEX } from "@sphereon/pex";
import { importJWK, jwtVerify } from "jose";

const PORT = Number(process.env.PORT || 7000);
const app = express();
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "iw3ip-verifier-sidecar" });
});

function b64uDecode(s) {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  return Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/") + pad, "base64");
}

async function verifySdJwtVc(compact, issuerPublicJwk) {
  const parts = compact.split("~");
  const jwt = parts[0];
  const rest = parts.slice(1);
  const kb = rest.length > 0 && rest[rest.length - 1] !== "" ? rest[rest.length - 1] : null;
  const disclosures = rest.slice(0, rest.length - 1).filter((d) => d !== "");

  const key = await importJWK(issuerPublicJwk, "ES256");
  const { payload, protectedHeader } = await jwtVerify(jwt, key, { algorithms: ["ES256"] });
  const payloadObj = typeof payload === "object" ? payload : JSON.parse(Buffer.from(payload).toString("utf-8"));

  const sdSet = new Set(payloadObj._sd || []);
  const disclosed = {};
  for (const d of disclosures) {
    const digest = Buffer.from(
      await crypto.subtle.digest("SHA-256", Buffer.from(d, "ascii"))
    );
    const digestB64u = digest.toString("base64").replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
    if (!sdSet.has(digestB64u)) {
      throw new Error("disclosure not referenced by _sd");
    }
    const arr = JSON.parse(b64uDecode(d).toString("utf-8"));
    disclosed[arr[1]] = arr[2];
  }
  const merged = { ...payloadObj };
  delete merged._sd;
  delete merged._sd_alg;
  Object.assign(merged, disclosed);
  return { claims: merged, header: protectedHeader, kb };
}

app.post("/verify", async (req, res) => {
  try {
    const {
      presentation_definition,
      vp_token,
      presentation_submission,
      issuer_public_jwk,
      expected_nonce,
      expected_aud,
    } = req.body || {};

    if (!presentation_definition || !vp_token || !presentation_submission) {
      return res.status(400).json({ verified: false, reason: "missing_fields" });
    }

    const { claims } = await verifySdJwtVc(vp_token, issuer_public_jwk);

    const pex = new PEX();
    const selectResult = pex.evaluateCredentials(presentation_definition, [
      { ...claims, vct: claims.vct },
    ]);
    if (selectResult.errors && selectResult.errors.length > 0) {
      return res.json({
        verified: false,
        reason: "pex_evaluate_error:" + selectResult.errors.map((e) => e.message || e.tag).join(","),
        claims,
        holder_did: null,
      });
    }

    let holderDid = null;
    const cnfJwk = claims.cnf && claims.cnf.jwk;
    if (cnfJwk) {
      const canonical = JSON.stringify(cnfJwk, Object.keys(cnfJwk).sort());
      holderDid = "did:jwk:" + Buffer.from(canonical, "utf-8").toString("base64")
        .replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
    }

    return res.json({ verified: true, reason: "ok", claims, holder_did: holderDid });
  } catch (err) {
    return res.status(200).json({
      verified: false,
      reason: "verify_error:" + (err && err.message ? err.message : String(err)),
      claims: {},
      holder_did: null,
    });
  }
});

app.listen(PORT, () => {
  console.log(`[iw3ip-verifier-sidecar] listening on :${PORT}`);
});
