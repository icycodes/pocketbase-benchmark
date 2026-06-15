const PocketBase = require('pocketbase/cjs');
const fs = require('fs');
const path = require('path');

const PB_URL = 'http://127.0.0.1:8090';
const ADMIN_EMAIL = 'admin@example.com';
const ADMIN_PASSWORD = 'adminpassword';
const COLLECTION_NAME = 'gallery';
const INPUT_FILE = path.join(__dirname, 'input.jpg');
const THUMBNAIL_FILE = path.join(__dirname, 'thumbnail.jpg');
const LOG_FILE = path.join(__dirname, 'output.log');

async function main() {
  const pb = new PocketBase(PB_URL);

  // 1. Authenticate as admin
  await pb.collection('_superusers').authWithPassword(ADMIN_EMAIL, ADMIN_PASSWORD);
  console.log('Authenticated as admin.');

  // 2. Read the input image and create FormData for upload
  const fileBuffer = fs.readFileSync(INPUT_FILE);
  const blob = new Blob([fileBuffer], { type: 'image/jpeg' });

  const formData = new FormData();
  formData.append('image', blob, 'input.jpg');

  // 3. Create a new record in the gallery collection
  const record = await pb.collection(COLLECTION_NAME).create(formData);
  console.log('Record created:', record.id);

  // 4. Get the thumbnail URL using pb.files.getURL()
  const thumbUrl = pb.files.getURL(record, record.image, { thumb: '100x100' });
  console.log('Thumbnail URL:', thumbUrl);

  // 5. Download the thumbnail
  const response = await fetch(thumbUrl);
  if (!response.ok) {
    throw new Error(`Failed to download thumbnail: ${response.status} ${response.statusText}`);
  }
  const thumbBuffer = Buffer.from(await response.arrayBuffer());
  fs.writeFileSync(THUMBNAIL_FILE, thumbBuffer);
  console.log('Thumbnail saved to', THUMBNAIL_FILE);

  // 6. Write the record ID to output.log
  fs.writeFileSync(LOG_FILE, `Record ID: ${record.id}\n`);
  console.log('Record ID written to', LOG_FILE);
}

main().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
