import * as React from "react";

export interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div data-stub="AppShell" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "1rem", borderBottom: "1px solid #ccc" }}>
        <h1>Owlin App</h1>
      </header>
      <main style={{ flex: 1, padding: "1rem" }}>
        {children}
      </main>
    </div>
  );
}