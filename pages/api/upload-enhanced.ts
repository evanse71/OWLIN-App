import { NextApiRequest, NextApiResponse } from 'next';
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';

// Import the new modules (these would need to be available in the Node.js environment)
// For now, we'll create a bridge to the Python backend

interface UploadResponse {
  success: boolean;
  message: string;
  data?: any;
  errors?: string[];
}

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<UploadResponse>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      success: false, 
      message: 'Method not allowed' 
    });
  }

  try {
    const form = formidable({
      uploadDir: path.join(process.cwd(), 'uploads'),
      keepExtensions: true,
      maxFileSize: 50 * 1024 * 1024, // 50MB
    });

    const [fields, files] = await new Promise<[formidable.Fields, formidable.Files]>((resolve, reject) => {
      form.parse(req, (err, fields, files) => {
        if (err) reject(err);
        else resolve([fields, files]);
      });
    });

    const uploadedFiles = Array.isArray(files.file) ? files.file : [files.file];
    const userRole = fields.userRole?.[0] || 'viewer';
    const documentType = fields.documentType?.[0] || 'invoice';

    const results = [];

    for (const file of uploadedFiles) {
      if (!file) continue;

      try {
        // Call the Python backend for processing
        const result = await processFileWithPythonBackend(file, userRole, documentType);
        results.push(result);
      } catch (error) {
        results.push({
          filename: file.originalFilename || 'unknown',
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    const successCount = results.filter(r => r.success).length;
    const totalCount = results.length;

    return res.status(200).json({
      success: successCount > 0,
      message: `Processed ${successCount}/${totalCount} files successfully`,
      data: {
        results,
        summary: {
          total: totalCount,
          successful: successCount,
          failed: totalCount - successCount
        }
      }
    });

  } catch (error) {
    console.error('Upload error:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
      errors: [error instanceof Error ? error.message : 'Unknown error']
    });
  }
}

async function processFileWithPythonBackend(
  file: formidable.File, 
  userRole: string, 
  documentType: string
) {
  // This function would call the Python backend
  // For now, we'll simulate the processing
  
  const filePath = file.filepath;
  const fileName = file.originalFilename || 'unknown';
  
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Simulate success/failure based on file type
  const isSuccess = file.mimetype?.includes('pdf') || file.mimetype?.includes('image');
  
  return {
    filename: fileName,
    success: isSuccess,
    data: isSuccess ? {
      filePath,
      fileSize: file.size,
      mimeType: file.mimetype,
      documentType,
      userRole,
      processedAt: new Date().toISOString()
    } : null,
    error: isSuccess ? null : 'Unsupported file type'
  };
} 