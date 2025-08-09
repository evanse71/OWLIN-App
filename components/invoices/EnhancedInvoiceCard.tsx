import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  ChevronDownIcon, 
  ChevronUpIcon, 
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  FileTextIcon,
  BuildingIcon,
  CalendarIcon,
  CreditCardIcon
} from 'lucide-react';

interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  confidence: number;
}

interface ParsedInvoice {
  invoice_number: string;
  date: string;
  supplier: string;
  net_total: number;
  vat_total: number;
  gross_total: number;
  currency: string;
  vat_rate?: number;
  confidence: number;
  line_items: LineItem[];
}

interface EnhancedInvoiceCardProps {
  documentId: string;
  filename: string;
  overallConfidence: number;
  manualReviewRequired: boolean;
  documentType: string;
  processingTime: number;
  parsedInvoice?: ParsedInvoice;
  userRole?: string;
  onEdit?: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}

const EnhancedInvoiceCard: React.FC<EnhancedInvoiceCardProps> = ({
  documentId,
  filename,
  overallConfidence,
  manualReviewRequired,
  documentType,
  processingTime,
  parsedInvoice,
  userRole = 'viewer',
  onEdit,
  onApprove,
  onReject
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircleIcon className="w-4 h-4" />;
    if (confidence >= 0.6) return <ClockIcon className="w-4 h-4" />;
    return <AlertTriangleIcon className="w-4 h-4" />;
  };

  const formatCurrency = (amount: number, currency: string = 'GBP') => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const canEdit = userRole === 'finance' || userRole === 'admin';
  const canApprove = userRole === 'finance' || userRole === 'admin';

  return (
    <Card className="w-full hover:shadow-lg transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <FileTextIcon className="w-5 h-5 text-gray-500" />
              <CardTitle className="text-lg font-semibold truncate">
                {filename}
              </CardTitle>
            </div>
            
            {/* Confidence and Review Status */}
            <div className="flex items-center gap-3 mb-3">
              <Badge 
                variant="outline" 
                className={`flex items-center gap-1 ${getConfidenceColor(overallConfidence)}`}
              >
                {getConfidenceIcon(overallConfidence)}
                {Math.round(overallConfidence * 100)}% Confidence
              </Badge>
              
              {manualReviewRequired && (
                <Badge variant="destructive" className="flex items-center gap-1">
                  <AlertTriangleIcon className="w-4 h-4" />
                  Manual Review Required
                </Badge>
              )}
              
              <Badge variant="secondary">
                {documentType}
              </Badge>
            </div>

            {/* Parsed Invoice Summary */}
            {parsedInvoice && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="flex items-center gap-1">
                  <BuildingIcon className="w-4 h-4 text-gray-500" />
                  <span className="truncate">{parsedInvoice.supplier}</span>
                </div>
                
                <div className="flex items-center gap-1">
                  <CalendarIcon className="w-4 h-4 text-gray-500" />
                  <span>{parsedInvoice.date}</span>
                </div>
                
                <div className="flex items-center gap-1">
                  <FileTextIcon className="w-4 h-4 text-gray-500" />
                  <span>{parsedInvoice.invoice_number}</span>
                </div>
                
                <div className="flex items-center gap-1">
                  <CreditCardIcon className="w-4 h-4 text-gray-500" />
                  <span className="font-semibold">
                    {formatCurrency(parsedInvoice.gross_total, parsedInvoice.currency)}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2 ml-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronUpIcon className="w-4 h-4" />
              ) : (
                <ChevronDownIcon className="w-4 h-4" />
              )}
            </Button>
            
            {canEdit && onEdit && (
              <Button variant="outline" size="sm" onClick={onEdit}>
                Edit
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Processing Information */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>Processing Time: {processingTime.toFixed(2)}s</span>
            <span>Document ID: {documentId.slice(0, 8)}...</span>
          </div>
          
          {/* Confidence Progress Bar */}
          <div className="mt-2">
            <div className="flex items-center justify-between text-sm mb-1">
              <span>OCR Confidence</span>
              <span>{Math.round(overallConfidence * 100)}%</span>
            </div>
            <Progress value={overallConfidence * 100} className="h-2" />
          </div>
        </div>

        {/* Expanded Content */}
        {isExpanded && (
          <div className="space-y-4">
            {/* Parsed Invoice Details */}
            {parsedInvoice && (
              <div className="space-y-3">
                <h4 className="font-semibold text-gray-900">Invoice Details</h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
                  <div>
                    <h5 className="font-medium text-gray-700 mb-2">Basic Information</h5>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>Supplier:</span>
                        <span className="font-medium">{parsedInvoice.supplier}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Invoice Number:</span>
                        <span className="font-medium">{parsedInvoice.invoice_number}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Date:</span>
                        <span className="font-medium">{parsedInvoice.date}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Currency:</span>
                        <span className="font-medium">{parsedInvoice.currency}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h5 className="font-medium text-gray-700 mb-2">Financial Summary</h5>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>Net Total:</span>
                        <span className="font-medium">
                          {formatCurrency(parsedInvoice.net_total, parsedInvoice.currency)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>VAT Total:</span>
                        <span className="font-medium">
                          {formatCurrency(parsedInvoice.vat_total, parsedInvoice.currency)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Gross Total:</span>
                        <span className="font-semibold text-blue-600">
                          {formatCurrency(parsedInvoice.gross_total, parsedInvoice.currency)}
                        </span>
                      </div>
                      {parsedInvoice.vat_rate && (
                        <div className="flex justify-between">
                          <span>VAT Rate:</span>
                          <span className="font-medium">{parsedInvoice.vat_rate}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Line Items */}
                {parsedInvoice.line_items.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-gray-900 mb-3">Line Items ({parsedInvoice.line_items.length})</h5>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {parsedInvoice.line_items.map((item, index) => (
                        <div key={index} className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-sm">{item.description}</span>
                            <Badge 
                              variant="outline" 
                              className={`text-xs ${getConfidenceColor(item.confidence)}`}
                            >
                              {Math.round(item.confidence * 100)}%
                            </Badge>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
                            <div>
                              <span className="font-medium">Qty:</span> {item.quantity}
                            </div>
                            <div>
                              <span className="font-medium">Unit Price:</span> {formatCurrency(item.unit_price, parsedInvoice.currency)}
                            </div>
                            <div>
                              <span className="font-medium">Total:</span> {formatCurrency(item.total_price, parsedInvoice.currency)}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-4 border-t">
              {canApprove && onApprove && (
                <Button 
                  variant="default" 
                  size="sm" 
                  onClick={onApprove}
                  disabled={manualReviewRequired}
                >
                  <CheckCircleIcon className="w-4 h-4 mr-1" />
                  Approve
                </Button>
              )}
              
              {canApprove && onReject && (
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={onReject}
                >
                  <AlertTriangleIcon className="w-4 h-4 mr-1" />
                  Reject
                </Button>
              )}
              
              {manualReviewRequired && (
                <div className="flex items-center gap-2 text-sm text-amber-600">
                  <AlertTriangleIcon className="w-4 h-4" />
                  <span>This document requires manual review due to low confidence</span>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default EnhancedInvoiceCard; 