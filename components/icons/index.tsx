import { FileText, Link, AlertTriangle, RefreshCw, Upload, CheckCircle2 } from 'lucide-react';
import type { ComponentType, SVGProps } from 'react';

// Import SVG icons
import PairSuggestIcon from './svg/PairSuggestIcon';
import PairConfirmIcon from './svg/PairConfirmIcon';
import PairRejectIcon from './svg/PairRejectIcon';
import HealthOkIcon from './svg/HealthOkIcon';
import HealthDegradedIcon from './svg/HealthDegradedIcon';
import HealthCriticalIcon from './svg/HealthCriticalIcon';

export type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

export const Icons: Record<string, IconComponent> = {
  // Existing lucide icons
  file: FileText,
  link: Link,
  alert: AlertTriangle,
  refresh: RefreshCw,
  upload: Upload,
  check: CheckCircle2,
  
  // New SVG icons
  'pair-suggest': PairSuggestIcon,
  'pair-confirm': PairConfirmIcon,
  'pair-reject': PairRejectIcon,
  'health-ok': HealthOkIcon,
  'health-degraded': HealthDegradedIcon,
  'health-critical': HealthCriticalIcon,
};

export default Icons; 