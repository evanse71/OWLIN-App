import type { NextApiRequest, NextApiResponse } from 'next';
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';

const PY_BACKEND_URL = process.env.PY_BACKEND_URL || 'http://localhost:8002';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Parse the form data
    const form = formidable({
      uploadDir: './uploads',
      keepExtensions: true,
      maxFileSize: 50 * 1024 * 1024, // 50MB
    });

    const [fields, files] = await form.parse(req);
    const file = Array.isArray(files.file) ? files.file[0] : files.file;

    if (!file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // Create form data for Python backend
    const formData = new FormData();
    const fileBuffer = fs.readFileSync(file.filepath);
    const blob = new Blob([fileBuffer], { type: file.mimetype || 'application/octet-stream' });
    formData.append('file', blob, file.originalFilename || 'upload');

    // Forward to Python backend
    const response = await fetch(`${PY_BACKEND_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    // Clean up temporary file
    fs.unlinkSync(file.filepath);

    if (!response.ok) {
      return res.status(response.status).json(result);
    }

    return res.status(200).json(result);

  } catch (error) {
    console.error('Upload error:', error);
    return res.status(500).json({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
} 