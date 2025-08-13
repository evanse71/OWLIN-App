from typing import List, Dict
from matching import score_invoice_delivery_match

def batch_match(invoices: List[dict], delivery_notes: List[dict]) -> List[dict]:
    results = []
    for inv in invoices:
        candidates = []
        inv_id = inv.get('invoice_id') or inv.get('id') or inv.get('filename')
        for note in delivery_notes:
            note_id = note.get('delivery_note_number') or note.get('note_id') or note.get('id') or note.get('filename')
            score_data = score_invoice_delivery_match(inv, note)
            candidates.append({
                "note_id": note_id,
                "score": score_data["match_score"]
            })
        # Sort candidates by score descending, take top 3
        top_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:3]
        results.append({
            "invoice_id": inv_id,
            "candidates": top_candidates
        })
    return results 