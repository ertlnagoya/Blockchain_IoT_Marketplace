import type { RequestHandler } from '@sveltejs/kit';
import { Client } from 'pg';

// Function to fetch content from IPFS by CID
async function fetchIPFSContent(cid: string): Promise<any> {
    try {
        const response = await fetch(`http://host.docker.internal:5001/api/v0/cat?arg=${cid}`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error(`IPFS API error: ${response.status}`);
        }
        
        const text = await response.text();
        
        // Try to parse as JSON
        try {
            return JSON.parse(text);
        } catch {
            // If not JSON, return as plain text
            return { content: text, type: 'text' };
        }
    } catch (error) {
        console.error('Error fetching IPFS content:', error);
        return { error: 'Failed to fetch IPFS content', cid };
    }
}

export const POST: RequestHandler = async ({ request }) => {
    const { query } = await request.json();

    // Connect to PostgreSQL and execute the query
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
        
        // Always fetch data from IPFS
        if (result.length > 0) {
            const enrichedResult = await Promise.all(
                result.map(async (row: any) => {
                    // Find columns that may contain a CID
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
        
        // Return an empty array when no data
        await client.end();
        return new Response(JSON.stringify([]), {
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