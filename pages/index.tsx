import { useEffect, useState } from "react";
import api from "@/lib/api";

export default function Home() {
  const [ok, setOk] = useState<string>("checking...");
  
  useEffect(() => { 
    api.health()
      .then(() => setOk("ok"))
      .catch(e => setOk(String(e))); 
  }, []);

  return (
    <main style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1>Owlin UI (Dev)</h1>
      <p>Health: {ok}</p>
      <ul>
        <li><a href="/invoices">Invoices</a></li>
        <li><a href="/suppliers">Suppliers</a></li>
      </ul>
    </main>
  );
} 