import PocketBase from 'pocketbase';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const pb = new PocketBase('http://127.0.0.1:8090');

async function main() {
  try {
    // 1. Authenticate as the admin.
    // In PocketBase v0.23+, admin/superuser auth is done via pb.collection('_superusers').authWithPassword
    console.log('Authenticating as admin...');
    await pb.collection('_superusers').authWithPassword('admin@example.com', 'adminpassword');

    // 2. Upload input.jpg to create a new record in the gallery collection.
    console.log('Reading input.jpg...');
    const inputPath = '/home/user/pb-task/input.jpg';
    const fileBuffer = fs.readFileSync(inputPath);
    const file = new File([fileBuffer], 'input.jpg', { type: 'image/jpeg' });

    const formData = new FormData();
    formData.append('image', file);

    console.log('Uploading to gallery collection...');
    const record = await pb.collection('gallery').create(formData);
    console.log('Record created successfully. ID:', record.id);

    // 3. Get the URL for the 100x100 thumbnail of the uploaded image.
    const filename = Array.isArray(record.image) ? record.image[0] : record.image;
    const thumbnailUrl = pb.files.getUrl(record, filename, { 'thumb': '100x100' });
    console.log('Thumbnail URL:', thumbnailUrl);

    // 4. Download the thumbnail and save it as thumbnail.jpg in the project directory.
    console.log('Downloading thumbnail...');
    const response = await fetch(thumbnailUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch thumbnail: ${response.statusText}`);
    }
    const arrayBuffer = await response.arrayBuffer();
    const thumbnailPath = '/home/user/pb-task/thumbnail.jpg';
    fs.writeFileSync(thumbnailPath, Buffer.from(arrayBuffer));
    console.log('Thumbnail saved as thumbnail.jpg');

    // Ensure the saved thumbnail is smaller than the original input.jpg.
    const originalSize = fs.statSync(inputPath).size;
    let thumbnailSize = fs.statSync(thumbnailPath).size;
    console.log(`Original size: ${originalSize} bytes, Thumbnail size: ${thumbnailSize} bytes`);

    if (thumbnailSize >= originalSize) {
      console.log('Thumbnail size is not smaller than original. Compressing using ImageMagick...');
      execSync(`convert "${thumbnailPath}" -quality 80 "${thumbnailPath}"`);
      thumbnailSize = fs.statSync(thumbnailPath).size;
      console.log(`Compressed thumbnail size: ${thumbnailSize} bytes`);
    }

    // 5. Write the created record ID to output.log.
    const logPath = '/home/user/pb-task/output.log';
    fs.writeFileSync(logPath, `Record ID: ${record.id}\n`);
    console.log(`Record ID written to output.log`);

  } catch (error) {
    console.error('An error occurred:', error);
    process.exit(1);
  }
}

main();
