import Ajv from 'ajv';
import addFormats from 'ajv-formats';

// 本地复制的 schema
import purchaseRequestSchema from '$lib/schemas/purchase/v1/purchase_request.schema.json' assert { type: 'json' };
import providerResponseSchema from '$lib/schemas/response/v1/provider_response.schema.json' assert { type: 'json' };
import zkClaimSchema from '$lib/schemas/ssi/v1/zk_access_level_claim.schema.json' assert { type: 'json' };

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

// 先注册被 $ref 的 claim schema
ajv.addSchema(zkClaimSchema as any, zkClaimSchema.$id);

export const validatePurchaseRequest = ajv.compile(purchaseRequestSchema as any);
export const validateProviderResponse = ajv.compile(providerResponseSchema as any);

export {
  purchaseRequestSchema,
  providerResponseSchema
};