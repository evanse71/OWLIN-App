import React from 'react'
import { UploadBarGen } from '../components/invoices-gen/UploadBarGen'
import { UploadBoxGen } from '../components/invoices-gen/UploadBoxGen'
import { InvoiceColumnGen, type InvoiceSummary } from '../components/invoices-gen/InvoiceColumnGen'
import { DetailViewGen } from '../components/invoices-gen/DetailViewGen'
import { DeliveryNoteColumnGen, type DeliveryNoteSummary } from '../components/invoices-gen/DeliveryNoteColumnGen'
import { ReviewFooterGen } from '../components/invoices-gen/ReviewFooterGen'
import {
  AnalysisAssistantGen,
  type AnalysisIssue,
  type StatusState,
} from '../components/invoices-gen/AnalysisAssistantGen'
import '../styles/invoices-gen.css'
import './InvoicesGenPage.css'

export default function InvoicesGenPage() {
  const [selectedInvoiceId, setSelectedInvoiceId] = React.useState<string | null>(null)
  const [selectedDeliveryNoteId, setSelectedDeliveryNoteId] = React.useState<string | null>(null)
  const [activeMobileTab, setActiveMobileTab] = React.useState<'invoices' | 'details' | 'delivery'>('invoices')

  // Dummy data for testing
  const invoices: InvoiceSummary[] = [
    {
      id: 'inv-001',
      supplierName: 'Greenside Produce',
      invoiceNumber: 'INV-001234',
      totalAmount: 256.40,
      status: 'ready',
    },
  ]

  const deliveryNotes: DeliveryNoteSummary[] = [
    {
      id: 'dn-001',
      supplierName: 'Greenside Produce',
      noteNumber: 'DN-7781',
      status: 'unlinked',
    },
  ]

  return (
    <div className="invoices-gen-page">
      <div className="invoices-gen-page__content">
        {/* Header */}
        <UploadBarGen />
        
        {/* Upload Box - Liquid Glass Style */}
        <UploadBoxGen />
        
        {/* Desktop: 3-column layout */}
        <div className="invoices-gen-page__main-row invoices-gen-page__main-row--desktop">
          {/* Container for the three main columns (Invoices, Summary, Delivery Notes) */}
          <div className="invoices-gen-page__columns-container">
            {/* LEFT: invoices list */}
            <InvoiceColumnGen
              invoices={invoices}
              selectedInvoiceId={selectedInvoiceId}
              onSelectInvoice={setSelectedInvoiceId}
            />

            {/* MIDDLE: details + delivery notes side-by-side */}
            <div className="invoices-gen-page__middle-column">
              <DetailViewGen selectedInvoiceId={selectedInvoiceId} />

              <DeliveryNoteColumnGen
                deliveryNotes={deliveryNotes}
                selectedDeliveryNoteId={selectedDeliveryNoteId}
                onSelectDeliveryNote={setSelectedDeliveryNoteId}
              />
            </div>
          </div>

          {/* RIGHT: full-height analysis / discrepancy assistant */}
          <AnalysisAssistantGen
            status="issues-found"
            issueCount={3}
            issues={[
              {
                id: 'issue-1',
                type: 'price-mismatch',
                severity: 'warning',
                title: 'Price mismatch',
                context: 'Carling 30L Keg − Supplier increased price from £82.40 → £105.00 (+27%).',
                aiNote: 'Unusual jump vs 90-day average.',
                invoiceId: 'inv-001',
                lineItemId: 'line-1',
              },
              {
                id: 'issue-2',
                type: 'missing-dn',
                severity: 'error',
                title: 'Missing delivery note',
                context: 'Invoice INV-001234 has no paired delivery note.',
                aiNote: 'Owlin found 1 potential match from last week.',
                invoiceId: 'inv-001',
              },
              {
                id: 'issue-3',
                type: 'credit-suggestion',
                severity: 'info',
                title: 'Likely credit',
                context: 'Heineken 50L Keg – delivered 3, invoiced 4.',
                aiNote: 'Estimated overcharge: £142.00.',
                invoiceId: 'inv-001',
                lineItemId: 'line-2',
              },
            ]}
          />
        </div>

        {/* Mobile: Tab-based layout */}
        <div className="invoices-gen-page__tabs invoices-gen-page__tabs--mobile">
          <div className="invoices-gen-page__tab-buttons">
            <button
              type="button"
              className={`invoices-gen-page__tab-button ${activeMobileTab === 'invoices' ? 'invoices-gen-page__tab-button--active' : ''}`}
              onClick={() => setActiveMobileTab('invoices')}
            >
              Invoices
            </button>
            <button
              type="button"
              className={`invoices-gen-page__tab-button ${activeMobileTab === 'details' ? 'invoices-gen-page__tab-button--active' : ''}`}
              onClick={() => setActiveMobileTab('details')}
            >
              Details
            </button>
            <button
              type="button"
              className={`invoices-gen-page__tab-button ${activeMobileTab === 'delivery' ? 'invoices-gen-page__tab-button--active' : ''}`}
              onClick={() => setActiveMobileTab('delivery')}
            >
              Delivery Notes
            </button>
          </div>
          <div className="invoices-gen-page__tab-content">
            {activeMobileTab === 'invoices' && (
              <InvoiceColumnGen
                invoices={invoices}
                selectedInvoiceId={selectedInvoiceId}
                onSelectInvoice={setSelectedInvoiceId}
              />
            )}
            {activeMobileTab === 'details' && (
              <DetailViewGen selectedInvoiceId={selectedInvoiceId} />
            )}
            {activeMobileTab === 'delivery' && (
              <DeliveryNoteColumnGen
                deliveryNotes={deliveryNotes}
                selectedDeliveryNoteId={selectedDeliveryNoteId}
                onSelectDeliveryNote={setSelectedDeliveryNoteId}
              />
            )}
          </div>
        </div>

        {/* Review & Submit - aligned with columns container */}
        <div className="invoices-gen-page__review-row invoices-gen-page__review-row--desktop">
          <ReviewFooterGen
            status="all-clear"
            hasDocuments={true}
            issues={[]}
          />
        </div>

        {/* Review & Submit - Mobile */}
        <div className="invoices-gen-page__review-row invoices-gen-page__review-row--mobile">
          <ReviewFooterGen
            status="all-clear"
            hasDocuments={true}
            issues={[]}
          />
        </div>
      </div>
    </div>
  )
}

