import { decodeJwt } from 'jose';

export type ProviderCredential = {
	'@context'?: unknown;
	id?: string;
	type?: string[] | string;
	issuer?: string;
	issuanceDate?: string;
	credentialSubject?: Record<string, any> & { id?: string };
	proof?: Record<string, any>;
};

export type ProviderProfileSummary = {
	providerDID: string;
	issuerDID?: string;
	level: number;
	vcID?: string;
	legalCompliance?: boolean;
	misuseRecord?: boolean;
	purpose?: string;
	entityType?: string;
	source?: 'json-ld' | 'jwt';
	issuedAt?: string;
};

export class ProviderVcError extends Error {
	constructor(message: string) {
		super(message);
		this.name = 'ProviderVcError';
	}
}

const jwtPattern = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;

function isJwt(input: string) {
	return jwtPattern.test(input);
}

export function parseProviderCredential(rawInput: string | object): { credential: ProviderCredential; source: 'json-ld' | 'jwt' } {
	if (typeof rawInput === 'object') {
		return { credential: rawInput as ProviderCredential, source: 'json-ld' };
	}

	const trimmed = rawInput.trim();
	if (!trimmed) {
		throw new ProviderVcError('请输入 Provider VC 或粘贴 JWT');
	}

	if (isJwt(trimmed)) {
		const payload = decodeJwt(trimmed) as Record<string, any>;
		const credential = (payload.vc ?? {}) as ProviderCredential;
		if (!credential.credentialSubject) {
			throw new ProviderVcError('JWT 中缺少 credentialSubject 字段');
		}
		return { credential, source: 'jwt' };
	}

	try {
		const parsed = JSON.parse(trimmed);
		return { credential: parsed as ProviderCredential, source: 'json-ld' };
	} catch (error) {
		throw new ProviderVcError('无法解析 JSON 格式的 VC');
	}
}

export function deriveProviderLevel(credential: ProviderCredential): number {
	const subject = credential.credentialSubject ?? {};
	if (subject.legalCompliance === true && subject.misuseRecord === false) {
		return 2;
	}
	if (subject.legalCompliance === true) {
		return 1;
	}
	return 0;
}

export function summarizeProvider(
	credential: ProviderCredential,
	levelOverride?: number,
	source: 'json-ld' | 'jwt' = 'json-ld'
): ProviderProfileSummary {
	const subject = credential.credentialSubject ?? {};
	const providerDID = subject.id || credential.id || credential.issuer;
	if (!providerDID) {
		throw new ProviderVcError('VC 中缺少 provider DID (credentialSubject.id)');
	}

	const level = Number.isInteger(levelOverride) ? Number(levelOverride) : deriveProviderLevel(credential);

	return {
		providerDID,
		issuerDID: credential.issuer,
		level,
		vcID: credential.id,
		legalCompliance: subject.legalCompliance,
		misuseRecord: subject.misuseRecord,
		purpose: subject.purpose,
		entityType: subject.entityType,
		source,
		issuedAt: credential.issuanceDate
	};
}

export function buildProviderProfilePayload(summary: ProviderProfileSummary) {
	return {
		providerDID: summary.providerDID,
		issuerDID: summary.issuerDID,
		level: summary.level,
		vcID: summary.vcID,
		attributes: {
			purpose: summary.purpose,
			entityType: summary.entityType,
			legalCompliance: summary.legalCompliance,
			misuseRecord: summary.misuseRecord
		}
	};
}
