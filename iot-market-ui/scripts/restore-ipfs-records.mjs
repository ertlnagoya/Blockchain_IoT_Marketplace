import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from 'pg';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const processedDir = path.resolve(__dirname, '../../mediator-owner/processed_data');
const ipfsBase = process.env.IPFS_API_BASE ?? 'http://localhost:5001';
const ipfsAddEndpoint = `${ipfsBase.replace(/\/$/, '')}/api/v0/add`;
const pgHost = process.env.PGHOST ?? 'localhost';

async function collectJsonFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const entryPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectJsonFiles(entryPath)));
    } else if (entry.isFile() && entry.name.endsWith('.json')) {
      files.push(entryPath);
    }
  }
  return files;
}

async function uploadJsonToIpfs(filePath, contents) {
  const formData = new FormData();
  formData.append('file', new Blob([contents], { type: 'application/json' }), path.basename(filePath));

  const response = await fetch(ipfsAddEndpoint, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw new Error(`IPFS add failed for ${filePath}: ${response.status} ${response.statusText}`);
  }

  const payloadText = await response.text();
  try {
    const payload = JSON.parse(payloadText);
    if (!payload.Hash) {
      throw new Error('Hash missing in IPFS response');
    }
    return payload.Hash;
  } catch (err) {
    throw new Error(`Failed to parse IPFS response for ${filePath}: ${(err && err.message) || err}\n${payloadText}`);
  }
}

function extractRecordData(data, filePath) {
  const start = data.start_timestamp ?? data.startTime;
  const end = data.end_timestamp ?? data.endTime;
  const location = data.location ?? data.geo ?? {};
  const latitude = location.latitude ?? location.lat;
  const longitude = location.longitude ?? location.lng ?? location.lon;
  const existPerson = data.exist_person ?? data.exist_people ?? data.existPerson ?? data.existPeople ?? false;

  if (!start || !end || latitude === undefined || longitude === undefined) {
    throw new Error(`Missing required fields in ${filePath}`);
  }

  return {
    start,
    end,
    latitude: Number(latitude),
    longitude: Number(longitude),
    existPerson: Boolean(existPerson)
  };
}

async function main() {
  const jsonFiles = (await collectJsonFiles(processedDir)).filter((filePath) => !filePath.includes('/metadata/'));
  if (jsonFiles.length === 0) {
    console.log('No JSON files found to restore.');
    return;
  }

  jsonFiles.sort();

  const client = new Client({
    host: pgHost,
    port: 5432,
    database: 'mydb',
    user: 'dev',
    password: 'devpassword'
  });

  await client.connect();
  console.log(`Connected to PostgreSQL. Truncating ipfs_records...`);
  await client.query('TRUNCATE ipfs_records;');

  let processed = 0;
  let inserted = 0;
  for (const filePath of jsonFiles) {
    try {
      const contents = await readFile(filePath, 'utf8');
      const data = JSON.parse(contents);
      const record = extractRecordData(data, filePath);
      const cid = await uploadJsonToIpfs(filePath, contents);

      await client.query(
        `INSERT INTO ipfs_records (cid, start_timestamp, end_timestamp, location, exist_people)
         VALUES ($1, $2, $3, ST_SetSRID(ST_MakePoint($4, $5), 4326), $6);`,
        [cid, record.start, record.end, record.longitude, record.latitude, record.existPerson]
      );

      inserted += 1;
      processed += 1;
      if (processed % 10 === 0 || processed === jsonFiles.length) {
        console.log(`[${processed}/${jsonFiles.length}] Inserted ${path.basename(filePath)} => ${cid}`);
      }
    } catch (error) {
      processed += 1;
      console.error(`Failed to process ${filePath}:`, error.message);
    }
  }

  await client.end();
  console.log(`Restoration complete: ${inserted} rows inserted.`);
}

main().catch((error) => {
  console.error('Restore script failed:', error);
  process.exit(1);
});
