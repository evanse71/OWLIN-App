import React, { useState } from 'react';

interface SignatureRegion {
  id: string;
  image_url: string;
  confidence: number;
  page: number;
  coordinates: { x: number; y: number; width: number; height: number };
}

interface SignatureStripProps {
  regions: SignatureRegion[];
}

export default function SignatureStrip({ regions }: SignatureStripProps) {
  const [selectedSignature, setSelectedSignature] = useState<SignatureRegion | null>(null);

  if (!regions || regions.length === 0) {
    return null;
  }

  const handleSignatureClick = (region: SignatureRegion) => {
    setSelectedSignature(region);
  };

  const handleModalClose = () => {
    setSelectedSignature(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleModalClose();
    }
  };

  return (
    <>
      <div className="space-y-2">
        <h4 className="text-[13px] text-[#5B6470] font-medium">Signatures & Stamps</h4>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {regions.map((region) => (
            <button
              key={region.id}
              onClick={() => handleSignatureClick(region)}
              className="flex-shrink-0 group"
              aria-label={`View signature on page ${region.page}`}
            >
              <div className="relative">
                <img
                  src={region.image_url}
                  alt={`Signature on page ${region.page}`}
                  className="w-16 h-16 md:w-20 md:h-20 rounded-md border border-[#E7EAF0] object-cover hover:shadow-md transition-shadow"
                />
                <div className="absolute bottom-1 right-1 bg-black/60 text-white text-xs px-1 rounded">
                  {region.page}
                </div>
                {region.confidence < 0.7 && (
                  <div className="absolute top-1 left-1 bg-amber-500 text-white text-xs px-1 rounded">
                    ⚠
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Modal */}
      {selectedSignature && (
        <div
          className="signature-modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
          onClick={handleModalClose}
          onKeyDown={handleKeyDown}
          tabIndex={-1}
        >
          <div
            className="signature-modal-panel bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[#2B2F36]">
                Signature on Page {selectedSignature.page}
              </h3>
              <button
                onClick={handleModalClose}
                className="text-[#5B6470] hover:text-[#2B2F36] transition-colors"
                aria-label="Close signature view"
              >
                ×
              </button>
            </div>
            
            <div className="flex items-center justify-center">
              <img
                src={selectedSignature.image_url}
                alt={`Signature on page ${selectedSignature.page}`}
                className="max-h-[60vh] max-w-full object-contain rounded border border-[#E7EAF0]"
              />
            </div>
            
            <div className="mt-4 text-sm text-[#5B6470] space-y-1">
              <div>Confidence: {(selectedSignature.confidence * 100).toFixed(1)}%</div>
              <div>Position: {selectedSignature.coordinates.x.toFixed(0)}, {selectedSignature.coordinates.y.toFixed(0)}</div>
              <div>Size: {selectedSignature.coordinates.width.toFixed(0)} × {selectedSignature.coordinates.height.toFixed(0)}</div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}; 