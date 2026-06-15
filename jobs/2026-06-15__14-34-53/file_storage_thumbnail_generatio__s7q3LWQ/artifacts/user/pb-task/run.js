import fs from 'fs';
import PocketBase from 'pocketbase';

const pb = new PocketBase('http://127.0.0.1:8090');

async function main() {
    try {
        await pb.admins.authWithPassword('admin@example.com', 'adminpassword');
        
        const fileContent = fs.readFileSync('input.jpg');
        const blob = new Blob([fileContent], { type: 'image/jpeg' });
        
        const formData = new FormData();
        formData.append('image', blob, 'input.jpg');
        
        const record = await pb.collection('gallery').create(formData);
        
        const thumbUrl = pb.files.getURL(record, record.image, { thumb: '100x100' });
        
        // Sometimes thumbnail generation takes a moment or needs a token if restricted,
        // but for public/admin it should work. Wait, getUrl returns the URL. To download,
        // we might need to fetch it.
        const response = await fetch(thumbUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch thumbnail: ${response.statusText}`);
        }
        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        
        fs.writeFileSync('thumbnail.jpg', buffer);
        fs.writeFileSync('output.log', `Record ID: ${record.id}`);
        
        console.log('Success');
    } catch (err) {
        console.error(err);
    }
}

main();
