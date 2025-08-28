import { FileText, Link, AlertTriangle, RefreshCw, Upload, CheckCircle2 } from 'lucide-react';
import type { ComponentType, SVGProps } from 'react';

export type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;
export const Icons: Record<string, IconComponent> = {
  file: FileText,
  link: Link,
  alert: AlertTriangle,
  refresh: RefreshCw,
  upload: Upload,
  check: CheckCircle2,
};

export default Icons; 