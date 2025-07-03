import type { RequestHandler } from '@sveltejs/kit';
import { Client } from 'pg';

// IPFSからCIDのコンテンツを取得する関数
async function fetchIPFSContent(cid: string): Promise<any> {
    try {
        const response = await fetch(`http://host.docker.internal:5001/api/v0/cat?arg=${cid}`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error(`IPFS API error: ${response.status}`);
        }
        
        const text = await response.text();
        
        // JSONとしてパースを試行
        try {
            return JSON.parse(text);
        } catch {
            // JSONでない場合はテキストとして返す
            return { content: text, type: 'text' };
        }
    } catch (error) {
        console.error('Error fetching IPFS content:', error);
        return { error: 'Failed to fetch IPFS content', cid };
    }
}

export const POST: RequestHandler = async ({ request }) => {
    const { query, fetchIPFS = false } = await request.json();

    // PostgreSQLに接続してクエリを実行
    const client = new Client({
        user: 'dev',
        host: 'host.docker.internal',
        database: 'mydb',
        password: 'devpassword',
        port: 5432,
    });

    try {
        await client.connect();
        const { rows: result } = await client.query(query);
        
        // fetchIPFSがtrueの場合、CIDカラムがあるかチェックしてIPFSからデータを取得
        if (fetchIPFS && result.length > 0) {
            const enrichedResult = await Promise.all(
                result.map(async (row: any) => {
                    // CIDを含む可能性のあるカラムを探す
                    const cidColumns = Object.keys(row).filter(key => 
                        key.toLowerCase().includes('cid') || 
                        key.toLowerCase().includes('hash')
                    );
                    
                    if (cidColumns.length > 0) {
                        const cid = row[cidColumns[0]];
                        if (cid && typeof cid === 'string') {
                            const ipfsData = await fetchIPFSContent(cid);
                            return {
                                ...row,
                                ipfs_data: ipfsData
                            };
                        }
                    }
                    
                    return row;
                })
            );
            
            await client.end();
            return new Response(JSON.stringify(enrichedResult), {
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        await client.end();
        return new Response(JSON.stringify(result), {
            headers: { 'Content-Type': 'application/json' }
        });
        
    } catch (error) {
        await client.end();
        console.error('Database or IPFS error:', error);
        return new Response(JSON.stringify({ error: 'Database or IPFS query failed' }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
};
