export const SEL = {
  // Layout components
  sidebar: '[data-ui="sidebar"]',
  page: '[data-ui="invoices-page"]',
  
  // Filter panel
  filterPanel: '[data-ui="filter-panel"]',
  searchInput: '[data-ui="search-input"]',
  supplierSelect: '[data-ui="supplier-select"]',
  venueSelect: '[data-ui="venue-select"]',
  dateRangeStart: '[data-ui="date-start"]',
  dateRangeEnd: '[data-ui="date-end"]',
  statusToggle: '[data-ui="status-toggle"]',
  sortSelect: '[data-ui="sort-select"]',
  resetFilters: '[data-ui="reset-filters"]',
  
  // Upload section
  uploadSection: '[data-ui="upload-section"]',
  uploadArea: '[data-ui="upload-area"]',
  fileInput: '[data-ui="file-input"]',
  browseButton: '[data-ui="browse-button"]',
  offlineQueue: '[data-ui="offline-queue"]',
  queuedFile: '[data-ui="queued-file"]',
  
  // Invoice cards
  cardsPanel: '[data-ui="invoice-cards"]',
  invoiceCard: '[data-ui="invoice-card"]',
  expandedCard: '[data-ui="invoice-card"][data-expanded="true"]',
  collapsedCard: '[data-ui="invoice-card"][data-expanded="false"]',
  
  // Invoice details
  detailBox: '[data-ui="invoice-detail"]',
  confidenceBadge: '[data-ui="confidence-badge"]',
  issuesBadge: '[data-ui="issues-badge"]',
  
  // Progress indicators
  progress: '[data-ui="progress"]',
  loadingSpinner: '[data-ui="loading-spinner"]',
  
  // Pairing suggestions
  pairingSuggestion: '[data-ui="pairing-suggestion"]',
  
  // Common elements
  button: 'button, [role="button"]',
  input: 'input, textarea, select',
  link: 'a[href]',
}; 