import { useEffect, useState } from "react";
import { fetchPairingSuggestions, PairSuggestion } from "@/lib/pairing";

export function usePairingSuggestions(invoiceId?: string | null) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<PairSuggestion[]>([]);
  
  useEffect(() => {
    let alive = true;
    if (!invoiceId) { 
      setSuggestions([]); 
      return; 
    }
    
    setLoading(true);
    fetchPairingSuggestions(invoiceId).then((s) => {
      if (!alive) return;
      setSuggestions(s || []);
      setLoading(false);
    }).catch(() => { 
      if (alive) setLoading(false); 
    });
    
    return () => { alive = false; };
  }, [invoiceId]);
  
  return { loading, suggestions, top: suggestions?.[0] };
} 