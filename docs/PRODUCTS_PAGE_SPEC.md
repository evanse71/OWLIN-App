# Products Page Specification

## Document Purpose

This specification serves as a complete blueprint for implementing the Products (Produce) page in Owlin. It defines layout, components, metrics, user flows, and data requirements following Owlin design patterns.

---

## 1. Page Purpose & Mental Model

### What This Page Answers

The Products page answers the question: **"For a given product – say Carling 11g keg or Chicken breast 5kg – what's happening with its price, how much have we spent, which suppliers are providing it, and how much we're wasting?"**

### Mental Model

This page is **item-centric**, not invoice-centric. Users think about products as entities with:
- Price history and trends
- Total spend over time
- Supplier relationships
- Waste and yield metrics
- Price volatility and alerts

### User Goals

1. **Price Monitoring**: Track if products are getting more expensive over time
2. **Spend Analysis**: Understand total spend per product and identify high-cost items
3. **Supplier Comparison**: See which suppliers provide each product and at what prices
4. **Waste Management**: Identify products with high waste percentages that need attention
5. **Cost Control**: Make informed decisions about ordering, supplier switching, or portion control

### Page Structure Concept

- **Left**: Product browser (all items you buy)
- **Middle**: Product overview & price graph (selected product details)
- **Right**: Spend, suppliers, waste & alerts (contextual metrics)

---

## 2. Layout Structure

### Grid System

The page uses a **12-column responsive grid** following Owlin layout rules.

### Desktop Layout (≥1024px)

```
┌─────────────────────────────────────────────────────────────┐
│ Header (full width, 12/12 columns)                          │
├──────────────┬──────────────────────────┬──────────────────┤
│              │                           │                   │
│ Product List │ Product Overview &       │ Metrics & Alerts │
│              │ Price Graph               │                   │
│ (3/12 cols)  │ (6/12 cols)              │ (3/12 cols)       │
│              │                           │                   │
│ Fixed width  │ Flexible                  │ Fixed width      │
│ ~360-420px   │                           │ ~360-420px       │
│              │                           │                   │
│ Scrollable   │ Scrollable               │ Scrollable        │
└──────────────┴──────────────────────────┴──────────────────┘
```

### Column Specifications

- **Left Column (3/12)**: Fixed width 360-420px, scrollable product list
- **Middle Column (6/12)**: Flexible width, scrollable product details
- **Right Column (3/12)**: Fixed width 360-420px, scrollable metrics

### Responsive Behavior

- **Tablet (768px-1023px)**: Stack columns vertically, maintain order
- **Mobile (<768px)**: Single column, collapsible sections

### Spacing

- Page padding: 24px minimum
- Column gap: 24px
- Section spacing: 24-32px
- Card spacing: 16px vertical

---

## 3. Page Header Component

### Component Name

`ProductsHeader` (following `InvoicesHeader` pattern)

### Layout

Full-width header bar with left and right sections, similar to `InvoicesHeader`.

### Left Section

#### Title & Subtitle
- **Title**: "Products" (h1, font-weight 600, 24px)
- **Subtitle**: "Track pricing, spend and waste for every item you buy." (muted text, 14px)

#### Venue Selector
- **Type**: Dropdown button (glass-button style)
- **Icon**: `Building2` (Lucide, 16px)
- **Label**: Current venue or "All venues"
- **Options**:
  - "All venues" (default, shows aggregate data)
  - Individual venue names (e.g., "Waterloo", "Royal Oak", "Main Restaurant")
- **Behavior**: Selecting a venue filters all metrics to that venue's scope
- **State**: Stored in context (similar to `DashboardFiltersContext`)

#### Product Category Filter
- **Type**: Chip/dropdown selector
- **Label**: "All categories" (default)
- **Options**:
  - All categories
  - Beer
  - Wine
  - Meat
  - Veg
  - Dry goods
  - Utilities
  - (Dynamic list from backend)
- **Behavior**: Filters the left-hand product list

#### Time Range Selector
- **Type**: Dropdown button
- **Label**: "Last 12 months" (default)
- **Options**:
  - Last 3 months
  - Last 6 months
  - Last 12 months
  - Custom (opens date picker)
- **Behavior**: Drives price graph, spend totals, waste % calculations
- **State**: Affects all time-based metrics on the page

### Right Section

#### Search Bar
- **Type**: Text input with search icon
- **Icon**: `Search` (Lucide, 16px, left side)
- **Placeholder**: "Search products by name or SKU…"
- **Behavior**: 
  - Real-time filtering of product list
  - Searches product name and SKU fields
  - Debounced (300ms delay)

#### View Toggle (Optional)
- **Type**: Segmented control (two buttons)
- **Options**:
  - "Key items" (favourites/high-spend products)
  - "All items"
- **Behavior**: Filters product list to show only starred/high-value items or all items

### Styling

Follow `InvoicesHeader.css` patterns:
- Glass-button style for dropdowns
- Search input with icon
- Segmented control for toggles
- Consistent spacing and alignment

### Component Props

```typescript
interface ProductsHeaderProps {
  venue: string
  onVenueChange: (venue: string) => void
  category: string
  onCategoryChange: (category: string) => void
  timeRange: '3m' | '6m' | '12m' | 'custom'
  onTimeRangeChange: (range: '3m' | '6m' | '12m' | 'custom') => void
  searchQuery: string
  onSearchChange: (query: string) => void
  viewMode?: 'key' | 'all'
  onViewModeChange?: (mode: 'key' | 'all') => void
  venues?: string[]
  categories?: string[]
}
```

---

## 4. Left Column – Product List (3/12)

### Component Name

`ProductList` (following `DocumentList` pattern)

### Section Header

- **Title**: "Products" (font-weight 600, 16px)
- **Right side**: Sort dropdown
  - Label: "Sort by: Spend" (default)
  - Options:
    - Spend (descending)
    - Price volatility (descending)
    - Name A–Z (ascending)
    - Name Z–A (descending)

### Product Cards

Each product card displays:

#### Top Row
- **Left**: Product name (e.g., "Carling 11g keg")
  - Font-weight: 500
  - Font-size: 15px
  - Color: Primary text
- **Right**: Category tag (e.g., "Beer")
  - Badge style (pill shape)
  - Background: `rgba(0,0,0,0.08)`
  - Font-size: 11px
  - Padding: 4px 8px

#### Second Row
- **Main metric**: Average price per unit
  - Format: "£X.XX avg/unit"
  - Font-weight: 600
  - Font-size: 16px
- **Trend indicator** (below price):
  - "+8% vs last year" (muted amber if increase)
  - "-3% vs last year" (muted green if decrease)
  - Font-size: 12px
  - Color: Muted text

#### Bottom Row (Meta Information)
- **Spend**: "£24,300 spend" (over selected time range)
- **Suppliers**: "2 suppliers" or "1 supplier"
- **Waste**: "3.2% waste" or "—" if unknown
- Font-size: 12px
- Color: Muted text
- Layout: Horizontal with separators (•)

### Card Styling

- Background: White
- Border: 1px solid `rgba(0,0,0,0.05)`
- Border-radius: 6px
- Shadow: `0 1px 2px rgba(0,0,0,0.04)`
- Padding: 16px
- Margin-bottom: 12px
- Hover: Subtle background change `rgba(0,0,0,0.02)`
- Selected state: Border color `#2B3A55`, background `rgba(43,58,85,0.05)`

### Selection Behavior

- Clicking a card:
  - Highlights it (selected state)
  - Loads product details in middle column
  - Loads metrics in right column
  - Scrolls card into view if needed
- Keyboard navigation (future):
  - Up/Down arrows navigate list
  - Enter selects product

### Empty States

#### No Products Match Filters
- Icon: `Package` (Lucide, 48px, muted)
- Title: "No products match your filters"
- Description: "Try adjusting your search or category filter"
- Action button: "Clear filters" (secondary button style)

#### No Products at All
- Icon: `Package` (Lucide, 48px, muted)
- Title: "No products yet"
- Description: "Products will appear here once invoices are processed"
- No action button (informational only)

### Scrollable Container

- Fixed height: Viewport height minus header
- Overflow-y: Auto
- Smooth scrolling
- Auto-scroll to selected product on selection change

### Component Props

```typescript
interface ProductListItem {
  id: string
  name: string
  sku?: string
  category: string
  averagePrice: number
  priceTrend: number // percentage change vs previous period
  totalSpend: number
  supplierCount: number
  wastePercentage: number | null
}

interface ProductListProps {
  products: ProductListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  sortBy: 'spend' | 'volatility' | 'name'
  onSortChange: (sort: 'spend' | 'volatility' | 'name') => void
  loading?: boolean
}
```

---

## 5. Middle Column – Product Overview & Price Graph (6/12)

### Empty State (No Product Selected)

Centered message card:
- Icon: `Package` (Lucide, 64px, muted)
- Title: "Select a product"
- Description: "Choose an item from the left to see its price, spend and waste."
- Styling: Muted colors, calm presentation

### Product Overview Card (When Selected)

#### Header
- **Product name**: Largest text (font-weight 600, 24px)
- **Subtitle line**:
  - Category badge
  - Unit specification (e.g., "11g keg", "5kg", "case of 24")
  - Font-size: 14px, muted

#### Content: Key Metric Tiles

Four small metric cards in a row (2x2 grid on smaller screens):

##### 1. Current Price
- **Value**: "£X.XX / unit"
- **Subtext**: "As of latest invoice on 12 Nov 2025"
- **Icon**: `DollarSign` (Lucide, 20px)
- **Color**: Primary (navy)

##### 2. Average Price (Time Range)
- **Value**: "£Y.YY / unit"
- **Subtext**: "+Z% vs previous period" (with trend indicator)
- **Icon**: `TrendingUp` or `TrendingDown` (Lucide, 20px)
- **Color**: Green if decrease, amber if increase

##### 3. Total Spend
- **Value**: "£XX,XXX"
- **Subtext**: "Invoices in selected period"
- **Icon**: `Receipt` (Lucide, 20px)
- **Color**: Primary (navy)

##### 4. Waste %
- **Value**: "W%" or "—"
- **Subtext**: "Equivalent to £N,NNN lost" (if data available) or "No waste records logged"
- **Icon**: `AlertTriangle` (Lucide, 20px) if waste > 5%, else `CheckCircle2`
- **Color**: Amber if waste > 5%, green if < 5%, muted if no data

#### Metric Tile Styling

- Background: White
- Border: 1px solid `rgba(0,0,0,0.05)`
- Border-radius: 6px
- Padding: 16px
- Shadow: `0 1px 2px rgba(0,0,0,0.04)`
- Grid layout: 2 columns on desktop, 1 column on mobile

### Price History & Forecast Card

#### Header
- **Left**: "Price history & forecast" (font-weight 600, 16px)
- **Right**: Controls
  - Toggle: "Price per unit" / "Price per litre/kg" (if normalization available)
  - Checkbox: "Show forecast" (on/off)
  - Pill badge: "Data since: Jan 2023" (muted, small)

#### Graph Content

Uses `UniversalTrendGraph` component (similar to `TrendsGraph`):

- **Library**: Recharts (AreaChart/LineChart)
- **X-axis**: Time (within selected range)
- **Y-axis**: Price (per normalized unit)
- **Lines**:
  - Solid line: Historical price (navy `#2B3A55`)
  - Dotted/soft line: Forecast (if enabled, sage green `#7B9E87`)
- **Optional shading**: Min-max price bands (very light fill)
- **Grid lines**: Ultra-light `rgba(0,0,0,0.05)`
- **Tooltip**: 
  - Date
  - Price
  - Supplier(s) that supplied at that price (optional list)
  - Styling: Rounded, soft shadow, calm colors

#### Below Graph: Mini Stats Row

- **Price volatility**: "12%" (with indicator if high)
- **Max**: "£X.XX"
- **Min**: "£Y.YY"
- **Median**: "£Z.ZZ"
- Layout: Horizontal, evenly spaced
- Font-size: 12px, muted

### Volume / Orders Card (Optional, Future)

#### Title
"Orders & volume"

#### Chart
- **Type**: Bar or area chart
- **X-axis**: Time
- **Y-axis**: Quantity purchased
- **Styling**: Follows Owlin graph rules

#### Stats
- **Total units purchased**: Number over time range
- **Average delivery frequency**: "Every 4.2 days" (calculated)

### Component Props

```typescript
interface ProductDetail {
  id: string
  name: string
  category: string
  unitSpec: string
  currentPrice: number
  currentPriceDate: string
  averagePrice: number
  priceChangePercent: number
  totalSpend: number
  wastePercentage: number | null
  wasteValue: number | null
  priceHistory: PriceHistoryPoint[]
  forecast?: PriceHistoryPoint[]
  priceVolatility: number
  priceMax: number
  priceMin: number
  priceMedian: number
  volumeHistory?: VolumeHistoryPoint[]
  totalUnitsPurchased?: number
  averageDeliveryFrequency?: number
}

interface PriceHistoryPoint {
  date: string
  price: number
  suppliers?: string[]
}

interface ProductOverviewProps {
  product: ProductDetail | null
  timeRange: '3m' | '6m' | '12m' | 'custom'
  showForecast: boolean
  priceUnit: 'per_unit' | 'per_normalized'
}
```

---

## 6. Right Column – Spend, Supplier Mix, Waste, Alerts (3/12)

### Card Stack

Four cards stacked vertically with 16px spacing:

### 6.1 Spend Breakdown Card

#### Title
"Spend breakdown" (font-weight 600, 16px)

#### Content

- **Big number**: "£XX,XXX" (total spend in current time range)
  - Font-weight: 600
  - Font-size: 24px
  - Color: Primary

- **Breakdown**:
  - "£X,XXX last 30 days"
  - "£Y,YYY previous 30 days" (+Z% or -Z% change indicator)
  - Font-size: 14px
  - Muted colors

- **Optional**: Mini bar chart visualization (light, subtle)
  - Two bars side by side
  - Current period vs previous period
  - Height proportional to spend

#### Styling
- Standard Owlin card styling
- Padding: 20px

### 6.2 Supplier Mix Card

#### Title
"Supplier mix" (font-weight 600, 16px)

#### Goal
Show how this product is split between suppliers (by spend or volume).

#### Layout Option: List with Horizontal Bars (Preferred)

Each supplier row:
- **Supplier name** (left)
- **Percent + spend** (right): "60% of spend (£15,000)"
- **Visual bar**: Horizontal bar showing percentage
  - Background: `rgba(0,0,0,0.05)`
  - Fill: Owlin navy or sage green
  - Height: 8px
  - Border-radius: 4px
- **Badge** (optional, future):
  - "Preferred" (green)
  - "Secondary" (amber)
  - "New" (blue)

#### Footer
- Text: "Multi-supplier item" or "Single-supplier item"
- Optional hint (if single supplier and price rising): "Consider diversifying supplier mix"

#### Alternative: Pie Chart
- If preferred, use clean pie chart
- Few colors (navy, sage green, muted variants)
- Show percentage labels
- Legend below chart

#### Styling
- Standard Owlin card styling
- Padding: 20px

### 6.3 Waste & Yield Card

#### Title
"Waste & yield" (font-weight 600, 16px)

#### Content

- **Main metric**: 
  - "Waste: 3.2% of volume" or "—" if unknown
  - Font-weight: 600
  - Font-size: 20px

- **Subtext**: 
  - "£1,280 estimated value lost in selected period" (if data available)

- **Breakdown** (if data available):
  - "Recorded waste: 120 units"
  - "Consumed / sold: 3,580 units"
  - Font-size: 12px, muted

- **Waste reasons** (if tracked):
  - Mini list:
    - "Spoilage: 50%"
    - "Over-portioning: 30%"
    - "Returns: 20%"
  - Each with small progress bar or percentage indicator

#### Empty State (No Waste Data)
- Quiet message: "No waste logged for this product yet"
- Hint text: "Link this product to your waste logs to see yield"
- Muted colors, non-alarming

#### Styling
- Standard Owlin card styling
- Padding: 20px
- Color coding: Amber if waste > 5%, green if < 5%

### 6.4 Alerts & Insights Card

#### Title
"Insights & alerts" (font-weight 600, 16px)

#### Content

Short, bullet-style insights list:

Examples:
- "Price has increased 9% over the last 3 months."
- "Supplier B is consistently 5–7% cheaper than Supplier A."
- "Waste above 5% in the last 60 days – consider reviewing portion sizes or ordering patterns."

#### Insight Classification

Each insight has a small label badge:
- "Pricing" (navy)
- "Supplier" (sage green)
- "Waste" (amber)
- "Volume" (muted)

#### Layout
- List of insight items
- Each item: Badge + text
- Spacing: 12px between items
- Font-size: 14px

#### Actions (Bottom Row)

- **Button**: "View supplier details"
  - Navigates to Supplier page filtered by this product
  - Secondary button style

- **Text link**: "Export product report" (future)
  - Muted, small text
  - Future: PDF or CSV export for that item

#### Styling
- Standard Owlin card styling
- Padding: 20px
- No harsh reds unless critical alert

### Component Props

```typescript
interface SpendBreakdown {
  totalSpend: number
  currentPeriodSpend: number
  previousPeriodSpend: number
  changePercent: number
}

interface SupplierMix {
  suppliers: {
    name: string
    spendShare: number
    spendAmount: number
    volumeShare?: number
    isPreferred?: boolean
  }[]
  isMultiSupplier: boolean
}

interface WasteYield {
  wastePercentage: number | null
  wasteValue: number | null
  wasteUnits: number | null
  consumedUnits: number | null
  wasteReasons?: {
    type: string
    percentage: number
  }[]
}

interface Insight {
  id: string
  type: 'pricing' | 'supplier' | 'waste' | 'volume'
  message: string
  severity?: 'info' | 'warning' | 'critical'
}

interface ProductMetricsProps {
  spendBreakdown: SpendBreakdown
  supplierMix: SupplierMix
  wasteYield: WasteYield
  insights: Insight[]
  onViewSupplierDetails: (productId: string) => void
}
```

---

## 7. User Flows

### Flow A – Check if a Product is Getting More Expensive

**Goal**: Monitor price trends for a specific product

**Steps**:
1. Land on Products page
2. Ensure venue = "All venues" or select specific site
3. Search for product name (e.g., "Carling") or use category filter (e.g., "Beer")
4. Click product card in left column (e.g., "Carling 11g keg")
5. Review in middle column:
   - Product overview → Compare "Current price" vs "Average price"
   - Price graph → Observe trend over last 12 months
6. Check right column:
   - Insights card → Look for "Price up X% over Y months" alert
7. Decision: Is price increase significant enough to act on?
   - If yes: Consider supplier switching or negotiation
   - If no: Continue monitoring

**Success Criteria**: User can quickly identify price trends and make informed decisions

### Flow B – See How Much We're Spending and With Whom

**Goal**: Understand spend distribution and supplier relationships

**Steps**:
1. Select a product from the list
2. Check right column → "Spend breakdown" card:
   - See total spend this year/period
   - Compare current period vs previous period
3. Check right column → "Supplier mix" card:
   - See which suppliers provide this product
   - See percentage share of spend per supplier
   - Identify if single-supplier dependency exists
4. Optional: Click "View supplier details" button
   - Navigate to Supplier page filtered by this product
   - See detailed supplier pricing and performance

**Success Criteria**: User understands spend patterns and can identify supplier diversification opportunities

### Flow C – Waste/Vulnerability Check

**Goal**: Identify products with high waste that need attention

**Steps**:
1. Select a high-cost item (e.g., steaks, fresh fish) from product list
2. Check right column → "Waste & yield" card:
   - See waste percentage
   - See estimated value lost
   - Review waste breakdown (if available)
3. Check right column → "Insights & alerts" card:
   - Look for "Waste above 5%" or similar alerts
   - Review waste reason breakdown
4. Use insights to prompt internal conversation:
   - Ordering patterns review
   - Portion size adjustments
   - Storage/handling improvements

**Success Criteria**: User can quickly identify waste issues and take corrective action

### Flow D – Compare Products Across Categories

**Goal**: Understand which product categories have highest spend or waste

**Steps**:
1. Use category filter to select a category (e.g., "Meat")
2. Review product list:
   - Sort by "Spend" to see highest-cost items
   - Observe waste percentages in product cards
3. Select individual products to drill down
4. Compare metrics across products in same category

**Success Criteria**: User can identify problem areas at category level

---

## 8. Data Requirements

### API Endpoints Needed

#### 8.1 Get Products List

**Endpoint**: `GET /api/products`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `category` (optional): Filter by category
- `search` (optional): Search by name or SKU
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`
- `sortBy` (optional): `spend` | `volatility` | `name`
- `viewMode` (optional): `key` | `all`

**Response**:
```typescript
{
  products: ProductListItem[]
  total: number
  categories: string[]
}
```

#### 8.2 Get Product Detail

**Endpoint**: `GET /api/products/:productId`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`
- `includeForecast` (optional): boolean

**Response**:
```typescript
ProductDetail
```

#### 8.3 Get Product Price History

**Endpoint**: `GET /api/products/:productId/price-history`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`
- `includeForecast` (optional): boolean
- `normalizeUnit` (optional): boolean (price per litre/kg)

**Response**:
```typescript
{
  history: PriceHistoryPoint[]
  forecast?: PriceHistoryPoint[]
  stats: {
    volatility: number
    max: number
    min: number
    median: number
  }
}
```

#### 8.4 Get Product Spend Breakdown

**Endpoint**: `GET /api/products/:productId/spend`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`

**Response**:
```typescript
SpendBreakdown
```

#### 8.5 Get Product Supplier Mix

**Endpoint**: `GET /api/products/:productId/suppliers`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`

**Response**:
```typescript
SupplierMix
```

#### 8.6 Get Product Waste Data

**Endpoint**: `GET /api/products/:productId/waste`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`

**Response**:
```typescript
WasteYield
```

#### 8.7 Get Product Insights

**Endpoint**: `GET /api/products/:productId/insights`

**Query Parameters**:
- `venue` (optional): Filter by venue ID
- `timeRange` (required): `3m` | `6m` | `12m` | `custom`

**Response**:
```typescript
{
  insights: Insight[]
}
```

### Data Models

#### ProductListItem
```typescript
interface ProductListItem {
  id: string
  name: string
  sku?: string
  category: string
  averagePrice: number
  priceTrend: number // percentage change vs previous period
  totalSpend: number
  supplierCount: number
  wastePercentage: number | null
}
```

#### ProductDetail
```typescript
interface ProductDetail {
  id: string
  name: string
  sku?: string
  category: string
  unitSpec: string // e.g., "11g keg", "5kg"
  currentPrice: number
  currentPriceDate: string
  averagePrice: number
  priceChangePercent: number
  totalSpend: number
  wastePercentage: number | null
  wasteValue: number | null
  priceHistory: PriceHistoryPoint[]
  forecast?: PriceHistoryPoint[]
  priceVolatility: number
  priceMax: number
  priceMin: number
  priceMedian: number
  volumeHistory?: VolumeHistoryPoint[]
  totalUnitsPurchased?: number
  averageDeliveryFrequency?: number
}
```

#### PriceHistoryPoint
```typescript
interface PriceHistoryPoint {
  date: string // ISO date string
  price: number
  suppliers?: string[] // Optional list of suppliers at this price point
}
```

#### VolumeHistoryPoint
```typescript
interface VolumeHistoryPoint {
  date: string // ISO date string
  quantity: number
}
```

#### SpendBreakdown
```typescript
interface SpendBreakdown {
  totalSpend: number
  currentPeriodSpend: number
  previousPeriodSpend: number
  changePercent: number
}
```

#### SupplierMix
```typescript
interface SupplierMix {
  suppliers: {
    name: string
    spendShare: number // 0-100 percentage
    spendAmount: number
    volumeShare?: number // 0-100 percentage
    isPreferred?: boolean
  }[]
  isMultiSupplier: boolean
}
```

#### WasteYield
```typescript
interface WasteYield {
  wastePercentage: number | null // 0-100 percentage
  wasteValue: number | null // Estimated value lost
  wasteUnits: number | null
  consumedUnits: number | null
  wasteReasons?: {
    type: string // e.g., "spoilage", "over-portioning", "returns"
    percentage: number // 0-100 percentage
  }[]
}
```

#### Insight
```typescript
interface Insight {
  id: string
  type: 'pricing' | 'supplier' | 'waste' | 'volume'
  message: string
  severity?: 'info' | 'warning' | 'critical'
}
```

### Data Aggregation Rules

- **Price calculations**: Average price per unit over selected time range
- **Spend totals**: Sum of invoice line items for this product
- **Waste percentage**: (Waste units / Total units) × 100
- **Price volatility**: Standard deviation of prices over time range
- **Supplier share**: Percentage of total spend or volume per supplier

---

## 9. Design System Alignment

### Owlin Design Contract Compliance

All components must follow the **OWLIN_UI_DESIGN_CONTRACT.md** rules:

#### Colors
- **Primary**: Desaturated Navy `#2B3A55`
- **Secondary**: Sage Green `#7B9E87`
- **Backgrounds**: Soft Grey `rgba(0,0,0,0.08)`
- **No pure black/white**: Use softened variants

#### Typography
- **Font**: Inter or Work Sans
- **Weights**: 
  - 600 = section titles
  - 500 = labels
  - 400 = body text
- **Sizes**: 11-12px (labels), 14px (body), 16px (titles), 24px (headings)

#### Cards
- **Background**: White
- **Border**: 1px solid `rgba(0,0,0,0.05)`
- **Border-radius**: 4-6px
- **Shadow**: `0 1px 2px rgba(0,0,0,0.04)`
- **Padding**: 16-20px
- **Spacing**: 8pt grid (8/12/16/24px)

#### Badges
- **Height**: 16-18px
- **Shape**: Rounded pill
- **Colors**: Soft backgrounds
  - Green: `rgba(123,158,135,0.15)`
  - Amber: `rgba(255,165,0,0.15)`
  - Red: `rgba(255,90,90,0.12)` (critical only)
  - Grey: `rgba(0,0,0,0.08)`

#### Graphs
- **Primary line**: Owlin navy `#2B3A55`
- **Secondary line**: Sage green `#7B9E87`
- **Grid lines**: Ultra-light `rgba(0,0,0,0.05)`
- **Tooltips**: Rounded, soft shadow, calm colors
- **Hover**: Smooth, no jitter

#### Motion
- **Timing**: 150-250ms ease-out
- **No aggressive springs**: Light and controlled
- **Fades**: Use for entrances, not overshoots

#### Tone
- **Calm, professional, non-alarming**
- **No harsh reds** unless critical
- **Muted colors** for secondary information

### Component Patterns to Follow

#### Header Pattern
- Follow `InvoicesHeader` component structure
- Use `glass-button` style for dropdowns
- Search input with icon on left
- Segmented control for toggles

#### List Pattern
- Follow `DocumentList` component structure
- Scrollable container with fixed height
- Card-based items with hover states
- Empty states with icons and calm messaging

#### Graph Pattern
- Follow `TrendsGraph` component structure
- Use Recharts library (AreaChart/LineChart)
- Responsive container
- Custom tooltips with Owlin styling

#### Filter Context Pattern
- Follow `DashboardFiltersContext` pattern
- Global filter state management
- <100ms propagation
- localStorage persistence

### Responsive Behavior

- **Desktop (≥1024px)**: 3-column layout as specified
- **Tablet (768px-1023px)**: Stack columns vertically
- **Mobile (<768px)**: Single column, collapsible sections
- **Touch targets**: Minimum 44px height
- **Spacing**: Maintains 8pt grid at all sizes

---

## 10. Implementation Notes

### Component File Structure

```
frontend_clean/src/
├── pages/
│   └── Products.tsx (main page component)
├── components/
│   └── products/
│       ├── ProductsHeader.tsx
│       ├── ProductsHeader.css
│       ├── ProductList.tsx
│       ├── ProductList.css
│       ├── ProductOverview.tsx
│       ├── ProductOverview.css
│       ├── PriceHistoryGraph.tsx
│       ├── PriceHistoryGraph.css
│       ├── ProductMetrics.tsx
│       ├── ProductMetrics.css
│       ├── SpendBreakdownCard.tsx
│       ├── SupplierMixCard.tsx
│       ├── WasteYieldCard.tsx
│       └── InsightsCard.tsx
├── lib/
│   └── productsApi.ts (API functions)
└── contexts/
    └── ProductsFiltersContext.tsx (optional, if needed)
```

### State Management

- Use React hooks (`useState`, `useEffect`) for local state
- Consider `ProductsFiltersContext` if filters need to be shared across components
- Follow `DashboardFiltersContext` pattern if implementing context

### Performance Considerations

- **Debounce search input**: 300ms delay
- **Lazy load product details**: Only fetch when product selected
- **Memoize expensive calculations**: Use `useMemo` for filtered/sorted lists
- **Virtual scrolling**: Consider for large product lists (>100 items)
- **Graph data caching**: Cache price history data per time range

### Accessibility

- **Keyboard navigation**: Up/Down arrows in product list
- **ARIA labels**: All interactive elements
- **Focus management**: Auto-focus on selected product
- **Screen reader support**: Descriptive text for all metrics

### Testing Considerations

- Unit tests for data transformations
- Integration tests for API calls
- E2E tests for user flows
- Visual regression tests for components

---

## 11. Future Enhancements

### Phase 2 Features

1. **Product Favorites**: Star/unstar products for quick access
2. **Product Comparison**: Compare multiple products side-by-side
3. **Export Reports**: PDF/CSV export for product analysis
4. **Price Alerts**: Set thresholds for price change notifications
5. **Supplier Recommendations**: AI-powered supplier suggestions
6. **Volume Forecasting**: Predict future order volumes
7. **Waste Tracking Integration**: Link to waste logging system
8. **Product Normalization**: Better unit conversion (litres/kg equivalents)

### Phase 3 Features

1. **Mobile App**: Native mobile experience
2. **Real-time Updates**: WebSocket for live price changes
3. **Advanced Analytics**: Machine learning insights
4. **Bulk Actions**: Update multiple products at once
5. **Product Groups**: Group related products for analysis

---

## Appendix: Reference Components

### Existing Components to Reference

1. **InvoicesHeader** (`frontend_clean/src/components/invoices/InvoicesHeader.tsx`)
   - Header layout and filter controls

2. **DocumentList** (`frontend_clean/src/components/invoices/DocumentList.tsx`)
   - List component with cards and selection

3. **TrendsGraph** (`frontend_clean/src/components/dashboard/TrendsGraph.tsx`)
   - Graph component with Recharts

4. **DashboardFiltersContext** (`frontend_clean/src/contexts/DashboardFiltersContext.tsx`)
   - Filter state management pattern

5. **MetricTile** (`frontend_clean/src/components/dashboard/MetricTile.tsx`)
   - Metric display patterns

### Design System Reference

- **OWLIN_UI_DESIGN_CONTRACT.md** (`docs/OWLIN_UI_DESIGN_CONTRACT.md`)
  - Complete design system rules

---

## Document Version

- **Version**: 1.0
- **Last Updated**: 2025-11-02
- **Author**: Specification Document
- **Status**: Ready for Implementation

---

**End of Specification**

