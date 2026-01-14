import { describe, it, expect } from 'vitest';
import {
	deriveProviderLevel,
	parseProviderCredential,
	summarizeProvider,
	buildProviderProfilePayload
} from '$lib/provider/verification';

const sampleCredential = {
	'@context': ['https://www.w3.org/2018/credentials/v1'],
	id: 'urn:uuid:test-provider',
	issuer: 'did:key:z6MkIssuer',
	credentialSubject: {
		id: 'did:key:z6MkProviderSubject',
		entityType: 'GovernmentOrganization',
		purpose: 'research',
		legalCompliance: true,
		misuseRecord: false
	}
};

describe('provider VC utilities', () => {
	it('derives level 2 when compliant and no misuse', () => {
		expect(deriveProviderLevel(sampleCredential)).toBe(2);
	});

	it('parses JWT formatted VC', () => {
		const header = Buffer.from(JSON.stringify({ alg: 'EdDSA', typ: 'JWT' })).toString('base64url');
		const payload = Buffer.from(JSON.stringify({ vc: sampleCredential })).toString('base64url');
		const signature = Buffer.from('sig').toString('base64url');
		const fakeJwt = `${header}.${payload}.${signature}`;
		const { credential, source } = parseProviderCredential(fakeJwt);
		expect(source).toBe('jwt');
		expect(credential.credentialSubject?.id).toBe('did:key:z6MkProviderSubject');
	});

	it('summarizes provider info and builds profile payload', () => {
		const { credential } = parseProviderCredential(JSON.stringify(sampleCredential));
		const summary = summarizeProvider(credential, undefined, 'json-ld');
		expect(summary.level).toBe(2);
		expect(summary.providerDID).toBe('did:key:z6MkProviderSubject');
		const profilePayload = buildProviderProfilePayload(summary);
		expect(profilePayload.providerDID).toBe(summary.providerDID);
		expect(profilePayload.attributes?.legalCompliance).toBe(true);
	});
});
