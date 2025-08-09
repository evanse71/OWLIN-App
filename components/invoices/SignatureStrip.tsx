import React, { useState } from 'react';
import { X, ZoomIn, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface SignatureRegion {
  page: number;
  bbox: { x: number; y: number; width: number; height: number };
  image_b64: string;
}

interface SignatureStripProps {
  signatureRegions: SignatureRegion[];
  className?: string;
}

const SignatureStrip: React.FC<SignatureStripProps> = ({
  signatureRegions,
  className
}) => {
  const [selectedSignature, setSelectedSignature] = useState<SignatureRegion | null>(null);
  const [rotation, setRotation] = useState(0);

  const handleSignatureClick = (signature: SignatureRegion) => {
    setSelectedSignature(signature);
    setRotation(0);
  };

  const handleCloseModal = () => {
    setSelectedSignature(null);
    setRotation(0);
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  if (signatureRegions.length === 0) {
    return null;
  }

  return (
    <>
      <div className={`flex flex-wrap gap-2 ${className}`}>
        {signatureRegions.map((signature, index) => (
          <div
            key={index}
            className="relative group cursor-pointer"
            onClick={() => handleSignatureClick(signature)}
          >
            <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
              <img
                src={`data:image/jpeg;base64,${signature.image_b64}`}
                alt={`Signature on page ${signature.page}`}
                className="w-20 h-16 object-contain bg-white"
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-200 flex items-center justify-center">
                <ZoomIn className="w-4 h-4 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <div className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs px-1 rounded-full">
              {signature.page}
            </div>
          </div>
        ))}
      </div>

      {/* Modal for enlarged signature */}
      {selectedSignature && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">
                Signature - Page {selectedSignature.page}
              </h3>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRotate}
                >
                  <RotateCw className="w-4 h-4 mr-1" />
                  Rotate
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCloseModal}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="p-4 flex items-center justify-center">
              <div
                className="relative overflow-hidden rounded-lg border border-gray-200 bg-gray-50"
                style={{
                  transform: `rotate(${rotation}deg)`,
                  transition: 'transform 0.3s ease'
                }}
              >
                <img
                  src={`data:image/jpeg;base64,${selectedSignature.image_b64}`}
                  alt={`Signature on page ${selectedSignature.page}`}
                  className="max-w-full max-h-[70vh] object-contain bg-white"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SignatureStrip; 