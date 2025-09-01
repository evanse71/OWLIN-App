import { Icons } from "@/components/icons";
import React from "react";

type IconType = React.ComponentType<React.SVGProps<SVGSVGElement>>;
const entries = Object.entries(Icons as Record<string, IconType>);

export default function TestIcons() {
  return (
    <div className="grid gap-4">
      {entries.map(([name, Icon]) => (
        <div key={String(name)} className="flex items-center gap-2">
          <Icon aria-hidden />
          <span>{String(name)}</span>
        </div>
      ))}
    </div>
  );
} 