import React, { useState, useRef, useEffect } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  Save, 
  Eye, 
  Flag, 
  Scissors, 
  Download, 
  Loader2,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  MapPin,
  User
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import LineItemsTable from './LineItemsTable';
import SignatureStrip from './SignatureStrip';
import { cn } from '@/lib/utils';

export interface LineItem {
  id?: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  vat_rate: number;
  line_total: number;
  page: number;
  row_idx: number;
  confidence: number;
  flags: string[];
}

export interface Address {
  supplier_address?: string;
  delivery_address?: string;
}

export interface SignatureRegion {
  page: number;
  bbox: { x: number; y: number; width: number; height: number };
  image_b64: string;
}

export interface InvoiceCardProps {
  id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  currency?: string;
  doc_type: 'invoice' | 'delivery_note' | 'receipt' | 'utility';
  page_range?: string;
  field_confidence?: Record<string, number>;
  status: 'processing' | 'processed' | 'error' | 'needs_review' | 'reviewed';
  addresses?: Address;
  signature_regions?: SignatureRegion[];
  line_items?: LineItem[];
  verification_status?: 'unreviewed' | 'needs_review' | 'reviewed';
  confidence?: number;
  onSave?: (invoiceId: string, data: Partial<InvoiceCardProps>) => void;
  onMarkReviewed?: (invoiceId: string) => void;
  onFlagIssues?: (invoiceId: string) => void;
  onSplitMerge?: (invoiceId: string) => void;
  onOpenPDF?: (invoiceId: string) => void;
  className?: string;
}

const InvoiceCard: React.FC<InvoiceCardProps> = ({
  id,
  supplier_name,
  invoice_number,
  invoice_date,
  total_amount,
  currency = 'GBP',
  doc_type,
  page_range,
  field_confidence = {},
  status,
  addresses,
  signature_regions = [],
  line_items = [],
  verification_status = 'unreviewed',
  confidence = 1.0,
  onSave,
  onMarkReviewed,
  onFlagIssues,
  onSplitMerge,
  onOpenPDF,
  className
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(status === 'processing');
  const [editedLineItems, setEditedLineItems] = useState<LineItem[]>(line_items);
  const cardRef = useRef<HTMLDivElement>(null);

  // Auto-expand when processing completes
  useEffect(() => {
    if (status === 'processed' && isProcessing) {
      setIsProcessing(false);
      setIsExpanded(true);
    }
  }, [status, isProcessing]);

  const getStatusColor = () => {
    switch (status) {
      case 'processing': return 'bg-blue-100 text-blue-800';
      case 'processed': return 'bg-green-100 text-green-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'needs_review': return 'bg-yellow-100 text-yellow-800';
      case 'reviewed': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getDocTypeColor = () => {
    switch (doc_type) {
      case 'invoice': return 'bg-blue-100 text-blue-800';
      case 'delivery_note': return 'bg-green-100 text-green-800';
      case 'receipt': return 'bg-yellow-100 text-yellow-800';
      case 'utility': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'bg-green-100 text-green-800';
    if (conf >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-GB');
    } catch {
      return dateStr;
    }
  };

  const handleLineItemUpdate = (rowIndex: number, field: keyof LineItem, value: any) => {
    setEditedLineItems(prev => prev.map((item, idx) => 
      idx === rowIndex ? { ...item, [field]: value } : item
    ));
  };

  const handleSave = () => {
    if (onSave) {
      onSave(id, { line_items: editedLineItems });
    }
  };

  const calculateTotals = () => {
    const subtotal = editedLineItems.reduce((sum, item) => sum + item.line_total, 0);
    const vat = editedLineItems.reduce((sum, item) => sum + (item.line_total * item.vat_rate), 0);
    const total = subtotal + vat;
    return { subtotal, vat, total };
  };

  const totals = calculateTotals();
  const hasMismatch = Math.abs(totals.total - total_amount) > (total_amount * 0.015);

  return (
    <Card className={cn(
      "relative transition-all duration-200 hover:shadow-lg",
      isExpanded && "ring-2 ring-blue-200",
      className
    )}>
      {/* Processing Spinner */}
      {isProcessing && (
        <div className="absolute bottom-4 right-4 z-10">
          <div className="flex items-center space-x-2 bg-white rounded-full shadow-lg px-3 py-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <span className="text-sm font-medium text-blue-600">Processing</span>
          </div>
        </div>
      )}

      <CardHeader className="pb-3">
        {/* Header Row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Badge className={getDocTypeColor()}>
              {doc_type.replace('_', ' ').toUpperCase()}
            </Badge>
            <h3 className="font-semibold text-lg">{supplier_name}</h3>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-2xl font-bold text-gray-900">
              {formatCurrency(total_amount)}
            </span>
            {hasMismatch && (
              <Badge className="bg-red-100 text-red-800" variant="outline">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Mismatch
              </Badge>
            )}
          </div>
        </div>

        {/* Meta Information */}
        <div className="grid grid-cols-2 gap-4 mt-3">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-600">
              {invoice_number} • {formatDate(invoice_date)}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <User className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-600">
              {page_range ? `Pages ${page_range}` : 'Page 1'}
            </span>
          </div>
        </div>

        {/* Addresses */}
        {addresses && (addresses.supplier_address || addresses.delivery_address) && (
          <div className="grid grid-cols-1 gap-2 mt-3">
            {addresses.supplier_address && (
              <div className="flex items-start space-x-2">
                <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs font-medium text-gray-500">Supplier Address:</span>
                  <p className="text-sm text-gray-700">{addresses.supplier_address}</p>
                </div>
              </div>
            )}
            {addresses.delivery_address && (
              <div className="flex items-start space-x-2">
                <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs font-medium text-gray-500">Delivery Address:</span>
                  <p className="text-sm text-gray-700">{addresses.delivery_address}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Status and Confidence */}
        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center space-x-2">
            <Badge className={getStatusColor()}>
              {status.replace('_', ' ').toUpperCase()}
            </Badge>
            <Badge className={getConfidenceColor(confidence)}>
              {Math.round(confidence * 100)}% Confidence
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 h-8 w-8"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
      </CardHeader>

      {/* Collapsible Content */}
      {isExpanded && (
        <CardContent className="pt-0">
          {/* Line Items Table */}
          {line_items.length > 0 && (
            <div className="mb-6">
              <LineItemsTable
                lineItems={editedLineItems}
                onLineItemUpdate={handleLineItemUpdate}
                totals={totals}
                hasMismatch={hasMismatch}
              />
            </div>
          )}

          {/* Signature/Handwriting Thumbnails */}
          {signature_regions.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Signatures & Handwriting</h4>
              <SignatureStrip signatureRegions={signature_regions} />
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="flex items-center space-x-2">
              <Button
                size="sm"
                onClick={handleSave}
                disabled={isProcessing}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Save className="w-4 h-4 mr-1" />
                Save Changes
              </Button>
              {verification_status === 'unreviewed' && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onMarkReviewed?.(id)}
                >
                  <CheckCircle className="w-4 h-4 mr-1" />
                  Mark Reviewed
                </Button>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onFlagIssues?.(id)}
              >
                <Flag className="w-4 h-4 mr-1" />
                Flag Issues
              </Button>
              {onSplitMerge && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onSplitMerge(id)}
                >
                  <Scissors className="w-4 h-4 mr-1" />
                  Split/Merge
                </Button>
              )}
              {onOpenPDF && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onOpenPDF(id)}
                >
                  <Download className="w-4 h-4 mr-1" />
                  Open PDF
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export default InvoiceCard; 