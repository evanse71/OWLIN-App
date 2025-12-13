#!/usr/bin/env python3
import os, sys, datetime, json, sqlite3
sys.path.insert(0, 'backend')
from db_manager_unified import get_db_manager

NOW = datetime.datetime.utcnow().isoformat(timespec="seconds")

def table_info(c, table):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    # rows: (cid, name, type, notnull, dflt_value, pk)
    return [{
        "name": r[1],
        "type": (r[2] or "").upper(),
        "notnull": bool(r[3]),
        "default": r[4],
        "pk": bool(r[5]),
    } for r in rows]

def required_cols(cols):
    # NOT NULL columns without a default must be provided
    return [c["name"] for c in cols if c["notnull"] and c["default"] is None and not c["pk"]]

def fill_defaults(row, cols, table):
    r = dict(row)
    nn = required_cols(cols)
    for col in nn:
        if r.get(col) is not None:
            continue
        # sensible generic defaults by name/type
        t = next((c["type"] for c in cols if c["name"] == col), "")
        name = col.lower()
        if "time" in name or "date" in name or name in ("created_at","updated_at","upload_timestamp"):
            r[col] = NOW
        elif "status" in name:
            r[col] = "unmatched" if table in ("delivery_notes",) else "ok"
        elif "currency" in name:
            r[col] = "GBP"
        elif "confidence" in name:
            r[col] = 1.0
        elif "total_amount_pennies" in name or "line_total_pennies" in name or name.endswith("_pennies"):
            r[col] = 0
        elif "quantity" in name or "qty" in name or "packs" in name or "units_per_pack" in name:
            r[col] = 0.0
        elif t.startswith("INT"):
            r[col] = 0
        elif t.startswith("REAL"):
            r[col] = 0.0
        else:
            r[col] = ""
    return r

def insert_row(c, table, cols, row):
    # ensure all columns are present in order
    ordered_vals = [row.get(col["name"]) for col in cols]
    placeholders = ",".join(["?"]*len(cols))
    names = ",".join([c_["name"] for c_ in cols])
    c.execute(f"INSERT OR REPLACE INTO {table}({names}) VALUES ({placeholders})", ordered_vals)

def main():
    print("🧊 BRUTAL JUDGE PROTOCOL - FOREIGN KEY SEEDING TEST")
    print("==================================================")

    db = get_db_manager()
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys=ON;")
    fk_on = c.execute("PRAGMA foreign_keys;").fetchone()[0]
    print("✅ Foreign keys enabled" if fk_on else "❌ Foreign keys OFF (fix PRAGMA)")

    # introspect live schema
    uf_cols = table_info(c, "uploaded_files")
    inv_cols = table_info(c, "invoices")
    ili_cols = table_info(c, "invoice_line_items")
    dn_cols  = table_info(c, "delivery_notes")
    dli_cols = table_info(c, "delivery_line_items")

    print("📋 Table columns:")
    print(f"  uploaded_files: {[x['name'] for x in uf_cols]}")
    print(f"  invoices: {[x['name'] for x in inv_cols]}")
    print(f"  invoice_line_items: {[x['name'] for x in ili_cols]}")
    print(f"  delivery_notes: {[x['name'] for x in dn_cols]}")
    print(f"  delivery_line_items: {[x['name'] for x in dli_cols]}]")

    # 1) Parent file for invoice
    uf = {
        "id": "seed_file",
        "original_filename": "seed.pdf",
        "canonical_path": "/tmp/seed.pdf",
        "file_size": 123,
        "file_hash": "deadbeef",
        "mime_type": "application/pdf",
        "upload_timestamp": NOW,
        "doc_type": "invoice",
        "doc_type_confidence": 1.0,
        "processing_status": "completed",
    }
    uf = fill_defaults(uf, uf_cols, "uploaded_files")
    insert_row(c, "uploaded_files", uf_cols, uf)
    print("✅ uploaded_files seeded")

    # 2) Parent file for delivery note (some schemas require file_id on DN)
    uf2 = {
        "id": "seed_dn_file",
        "original_filename": "seed_dn.pdf",
        "canonical_path": "/tmp/seed_dn.pdf",
        "file_size": 123,
        "file_hash": "beefdead",
        "mime_type": "application/pdf",
        "upload_timestamp": NOW,
        "doc_type": "delivery_note",
        "doc_type_confidence": 1.0,
        "processing_status": "completed",
    }
    uf2 = fill_defaults(uf2, uf_cols, "uploaded_files")
    insert_row(c, "uploaded_files", uf_cols, uf2)
    print("✅ uploaded_files (dn parent) seeded")

    # 3) Invoice (FK to uploaded_files.id)
    inv = {
        "id": "inv_seed",
        "file_id": uf["id"],
        "invoice_number": "INV-SEED-001",
        "invoice_date": NOW.split("T")[0],
        "supplier_name": "Seed Supplier Ltd",
        "total_amount_pennies": 7200,  # £72
    }
    inv = fill_defaults(inv, inv_cols, "invoices")
    insert_row(c, "invoices", inv_cols, inv)
    print("✅ invoices seeded")

    # 4) Delivery note (FK to uploaded_files.id)
    dn = {
        "id": "dn_seed",
        "file_id": uf2["id"],
        "delivery_note_number": "DN-SEED-001",
        "delivery_date": NOW.split("T")[0],
        "supplier_name": "Seed Supplier Ltd",
        "status": "unmatched",
    }
    dn = fill_defaults(dn, dn_cols, "delivery_notes")
    insert_row(c, "delivery_notes", dn_cols, dn)
    print("✅ delivery_notes seeded")

    # 5) Invoice line item (child of inv_seed)
    li = {
        "id": 4001 if any(c_["name"] == "id" for c_ in ili_cols) else None,
        "invoice_id": inv["id"],
        "row_idx": 0,
        "description": "TIA MARIA 1L",
        # Handle whichever quantity column your schema uses:
        "quantity_each": 6.0 if any(c_["name"] == "quantity_each" for c_ in ili_cols) else None,
        "quantity": 6.0 if any(c_["name"] == "quantity" for c_ in ili_cols) else None,
        "unit_price_pennies": 1200,
        "line_total_pennies": 7200,
        "line_flags": "[]",
        "flags": "[]",
    }
    li = fill_defaults(li, ili_cols, "invoice_line_items")
    insert_row(c, "invoice_line_items", ili_cols, li)
    print("✅ invoice_line_items seeded")

    # 6) Delivery line item (child of dn_seed)
    dli = {
        "id": 5001 if any(c_["name"] == "id" for c_ in ili_cols) else None,
        "delivery_note_id": dn["id"],
        "row_idx": 0,
        "description": "TIA MARIA 1L",
        "quantity": 6.0,
        "unit_price_pennies": 1200,
        "line_total_pennies": 7200 if any(c_["name"] == "line_total_pennies" for c_ in dli_cols) else None,
    }
    dli = fill_defaults(dli, dli_cols, "delivery_line_items")
    insert_row(c, "delivery_line_items", dli_cols, dli)
    print("✅ delivery_line_items seeded")

    conn.commit()

    # Verify counts
    def count(table):
        return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print("\n🔍 VERIFYING SEEDED DATA...")
    print("  uploaded_files:", count("uploaded_files"))
    print("  invoices:", count("invoices"))
    print("  invoice_line_items:", count("invoice_line_items"))
    print("  delivery_notes:", count("delivery_notes"))
    print("  delivery_line_items:", count("delivery_line_items"))
    print("✅ SEED_DATA_OK")

if __name__ == "__main__":
    try:
        main()
    except sqlite3.IntegrityError as e:
        print("❌ SEED_DATA_FAILED: FOREIGN KEY/NOT NULL violation")
        raise 