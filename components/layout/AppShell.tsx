import * as React from "react";
import { Sidebar } from "./Sidebar";

export interface AppShellProps {
  children: React.ReactNode;
  title?: string;
}

export default function AppShell({ children, title }: AppShellProps) {
  const [sidebarWidth, setSidebarWidth] = React.useState(280);
  const [isExpanded, setIsExpanded] = React.useState(true);

  return (
    <div className="flex h-screen bg-background">
      <Sidebar 
        onWidthChange={setSidebarWidth}
        onToggle={setIsExpanded}
      />
      <main className="flex-1 overflow-auto">
        {title && (
          <header className="border-b bg-background px-6 py-4">
            <h1 className="text-2xl font-semibold">{title}</h1>
          </header>
        )}
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}