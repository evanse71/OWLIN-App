SUPPLIER_ALIASES = {
    "Heineken UK Ltd": "Heineken",
    "HEINEKEN": "Heineken",
    "Heineken Group": "Heineken",
    # Add more known variants
}

def normalize_supplier_name(name: str) -> str:
    for alias, canonical in SUPPLIER_ALIASES.items():
        if alias.lower() in name.lower():
            return canonical
    return name 