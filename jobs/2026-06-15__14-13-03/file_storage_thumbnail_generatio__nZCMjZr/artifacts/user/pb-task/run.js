const PocketBase = require('pocketbase/cjs');
const fs = require('fs');
const path = require('path');

async function main() {
  const pb = new PocketBase('http://127.0.0.1:8090');

  // 1. Authenticate as admin
  await pb.admins.authWithPassword('admin@example.com', 'adminpassword');
  console.log('Authenticated as admin.');

  // 2. Upload input.jpg to create a new record in the gallery collection
  const imagePath = path.join(__dirname, 'input.jpg');
  const imageData = fs.readFileSync(imagePath);
  const blob = new Blob([imageData], { type: 'image/jpeg' });

  const formData = new FormData();
  formData.append('image', blob, 'input.jpg');

  const record = await pb.collection('gallery').create(formData);
  console.log('Record created with ID:', record.id);

  // 3. Get the URL for the 100x100 thumbnail
  const thumbUrl = pb.files.getUrl(record, record.image, { thumb: '100x100' });
  console.log('Thumbnail URL:', thumbUrl);

  // 4. Download the thumbnail and save it as thumbnail.jpg
  const response = await fetch(thumbUrl, {
    headers: {
      Authorization: pb.authStore.token,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to download thumbnail: ${response.status} ${response.statusText}`);
  }

  const arrayBuffer = await response.arrayBuffer();
  const thumbnailPath = path.join(__dirname, 'thumbnail.jpg');
  fs.writeFileSync(thumbnailPath, Buffer.from(arrayBuffer));
  console.log('Thumbnail saved to thumbnail.jpg');

  // 5. Write the record ID to output.log
  const logPath = path.join(__dirname, 'output.log');
  fs.writeFileSync(logPath, `Record ID: ${record.id}\n`);
  console.log('Record ID written to output.log');
}

main().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
