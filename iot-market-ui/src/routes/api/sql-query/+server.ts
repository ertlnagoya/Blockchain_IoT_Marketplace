import type { RequestHandler } from '@sveltejs/kit';
import { Client } from 'pg';

export const POST: RequestHandler = async ({ request }) => {
    const { query } = await request.json();

    // PostgreSQLに接続してクエリを実行

    const client = new Client({
        user: 'dev',
        host: 'host.docker.internal',
        database: 'mydb',
        password: 'devpassword',
        port: 5432,
    });

    await client.connect();
    const { rows: result } = await client.query(query);
    await client.end();
    // const result = await db.query(query);

    return new Response(JSON.stringify(result), {
        headers: { 'Content-Type': 'application/json' }
    });
};