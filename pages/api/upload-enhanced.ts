import { NextApiRequest, NextApiResponse } from 'next';
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';

// Backend API URL - can be configured via environment variable
const PY_BACKEND_URL = process.env.PY_BACKEND_URL || 'http://localhost:8000';

interface UploadResponse {
  success: boolean;
  message: string;
  data?: any;
  errors?: string[];
}

interface PythonBackendResponse {
  success: boolean;
  message: string;
  data?: {
    filename: string;
    supplier_name?: string;
    invoice_number?: string;
    invoice_date?: string;
    net_amount?: number;
    vat_amount?: number;
    total_amount?: number;
    ocr_confidence?: number;
    line_items?: any[];
    processing_time?: number;
  };
  error?: string;
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
        console.error(`Error processing ${file.originalFilename}:`, error);
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
): Promise<any> {
  const fileName = file.originalFilename || 'unknown';
  
  try {
    // Create FormData to send to Python backend
    const FormData = require('form-data');
    const formData = new FormData();
    
    // Add the file
    formData.append('file', fs.createReadStream(file.filepath), fileName);
    
    // Add metadata
    formData.append('userRole', userRole);
    formData.append('documentType', documentType);

    console.log(`🔄 Sending ${fileName} to Python backend at ${PY_BACKEND_URL}/api/upload/enhanced`);

    // Send to Python FastAPI backend - FIXED: Added /api prefix and using enhanced endpoint
    const response = await fetch(`${PY_BACKEND_URL}/api/upload/enhanced`, {
      method: 'POST',
      body: formData as any,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ Backend error for ${fileName}:`, errorText);
      throw new Error(`Backend error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const result: PythonBackendResponse = await response.json();
    
    console.log(`✅ Backend response for ${fileName}:`, result);

    return {
      filename: fileName,
      success: result.success,
      data: result.data,
      error: result.error || null,
      processing_time: result.data?.processing_time,
      ocr_confidence: result.data?.ocr_confidence,
      supplier_name: result.data?.supplier_name,
      invoice_number: result.data?.invoice_number,
      invoice_date: result.data?.invoice_date,
      net_amount: result.data?.net_amount,
      vat_amount: result.data?.vat_amount,
      total_amount: result.data?.total_amount,
      line_items: result.data?.line_items
    };

  } catch (error) {
    console.error(`❌ Error processing ${fileName}:`, error);
    throw error;
  }
} 