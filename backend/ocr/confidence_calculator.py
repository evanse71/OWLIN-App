from typing import Dict, Any, List
import re

class ConfidenceCalculator:
    FIELD_WEIGHTS = {
        "supplier_name": 2.0,
        "invoice_number": 2.0,
        "invoice_date": 2.0,
        "total_amount": 3.0,
        "addresses": 1.5,
        "line_items": 3.0,
    }

    def normalize(self, x: float) -> float:
        return max(0.30, min(0.98, float(x)))

    def _pattern_conf(self, text: str, pattern: str) -> float:
        return 0.9 if re.search(pattern, text or "", re.IGNORECASE) else 0.5

    def field_confidences(self, extracted: Dict[str, Any], ocr_signals: Dict[str, float]) -> Dict[str, float]:
        fields: Dict[str, float] = {}
        # Start with OCR signals (0..1)
        avg_ocr = float(ocr_signals.get("avg_confidence", 0.6))
        fields["supplier_name"] = self.normalize(0.6 * avg_ocr + 0.4 * (1.0 if extracted.get("supplier_name") and extracted.get("supplier_name") != "Unknown Supplier" else 0.4))
        fields["invoice_number"] = self.normalize(0.5 * avg_ocr + 0.5 * self._pattern_conf(extracted.get("invoice_number", ""), r"\b(?:inv|invoice)[-\s#:]*[A-Za-z0-9]{3,}\b"))
        fields["invoice_date"] = self.normalize(0.5 * avg_ocr + 0.5 * self._pattern_conf(extracted.get("invoice_date", ""), r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b"))
        fields["total_amount"] = self.normalize(0.6 * avg_ocr + 0.4 * (1.0 if float(extracted.get("total_amount") or 0) > 0 else 0.4))
        # Addresses presence
        addr = extracted.get("addresses") or {}
        fields["addresses"] = self.normalize(0.4 * avg_ocr + 0.6 * (1.0 if (addr.get("supplier_address") or addr.get("delivery_address")) else 0.4))
        # Line items present
        items = extracted.get("line_items") or []
        fields["line_items"] = self.normalize(0.4 * avg_ocr + 0.6 * (1.0 if items else 0.5))
        # Totals reconciliation if available
        subtotal = extracted.get("subtotal")
        vat = extracted.get("vat")
        if subtotal is not None and vat is not None and extracted.get("total_amount") is not None:
            try:
                calc_total = float(subtotal) + float(vat)
                total = float(extracted.get("total_amount"))
                diff = abs(calc_total - total)
                rel = diff / max(1.0, total)
                # Reduce total_amount conf a bit if mismatch
                if rel > 0.015:
                    fields["total_amount"] = self.normalize(fields["total_amount"] - min(0.2, rel))
            except Exception:
                pass
        return fields

    def line_item_confidences(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for it in items:
            desc = it.get("description") or ""
            qty = it.get("quantity")
            unit_price = it.get("unit_price")
            vat_rate = it.get("vat_percent") or it.get("vat_rate")
            line_total = it.get("line_total") or it.get("total_price")
            base = float(it.get("confidence", 0.6))

            def plaus(x, kind: str) -> float:
                try:
                    v = float(x)
                    if kind in ("qty",) and v < 0:
                        return 0.35
                    if kind != "qty" and v < 0:
                        return 0.35
                    if v > 1e6:
                        return 0.4
                    return 0.7
                except Exception:
                    return 0.5

            d_conf = self.normalize(0.5 * base + 0.5 * (0.8 if len(str(desc)) >= 2 else 0.4))
            q_conf = self.normalize(0.5 * base + 0.5 * plaus(qty, "qty"))
            u_conf = self.normalize(0.5 * base + 0.5 * plaus(unit_price, "price"))
            v_conf = self.normalize(0.4 * base + 0.6 * plaus(vat_rate, "vat")) if vat_rate is not None else 0.5
            t_conf = self.normalize(0.5 * base + 0.5 * plaus(line_total, "total"))

            it2 = dict(it)
            it2["description_confidence"] = d_conf
            it2["quantity_confidence"] = q_conf
            it2["unit_price_confidence"] = u_conf
            it2["vat_confidence"] = v_conf
            it2["line_total_confidence"] = t_conf
            it2["confidence"] = self.normalize((d_conf + q_conf + u_conf + t_conf) / 4.0)
            out.append(it2)
        return out

    def overall(self, fields: Dict[str, float], items: List[Dict[str, Any]]) -> float:
        if not fields:
            return 0.5
        num = 0.0
        den = 0.0
        for k, v in fields.items():
            w = self.FIELD_WEIGHTS.get(k, 1.0)
            num += float(v) * w
            den += w
        if items:
            avg_items = sum(float(i.get("confidence", 0.6)) for i in items) / max(1, len(items))
            num += avg_items * 3.0
            den += 3.0
        return self.normalize(num / max(1e-6, den)) 