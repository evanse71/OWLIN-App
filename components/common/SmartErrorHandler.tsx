import React from 'react';

interface UploadError {
  type: 'low_confidence' | 'no_text_detected' | 'timeout' | 'validation' | 'unknown';
  message: string;
}

interface SmartErrorHandlerProps {
  error: UploadError;
  onRetry: () => void;
  onFix: (suggestion: string) => void;
}

const ExclamationTriangleIcon: React.FC = () => (
  <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
  </svg>
);

const SmartErrorHandler: React.FC<SmartErrorHandlerProps> = ({ error, onRetry, onFix }) => {
  const getErrorSuggestion = (error: UploadError) => {
    switch (error.type) {
      case 'low_confidence':
        return 'Try uploading a clearer image or PDF';
      case 'no_text_detected':
        return 'Check if the document is properly oriented';
      case 'timeout':
        return 'Try a smaller file or split large PDFs';
      case 'validation':
        return 'Please check file type and size requirements';
      default:
        return 'Please try again or contact support';
    }
  };

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-center">
        <ExclamationTriangleIcon />
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">
            Upload failed
          </h3>
          <p className="text-sm text-red-700 mt-1">
            {error.message}
          </p>
          <p className="text-sm text-red-600 mt-2">
            Suggestion: {getErrorSuggestion(error)}
          </p>
        </div>
      </div>
      <div className="mt-4 flex space-x-3">
        <button
          onClick={onRetry}
          className="bg-red-100 text-red-700 px-3 py-1 rounded text-sm hover:bg-red-200 transition-colors"
        >
          Retry
        </button>
        <button
          onClick={() => onFix(getErrorSuggestion(error))}
          className="bg-blue-100 text-blue-700 px-3 py-1 rounded text-sm hover:bg-blue-200 transition-colors"
        >
          Try Fix
        </button>
      </div>
    </div>
  );
};

export default SmartErrorHandler;
