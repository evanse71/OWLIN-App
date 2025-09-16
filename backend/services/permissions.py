from typing import Literal
Role = Literal["GM", "Finance", "Shift Lead"]

def can_create_invoice(role: Role) -> bool: return role in ("GM", "Finance")
def can_edit_invoice(role: Role) -> bool:   return role in ("GM", "Finance")
def can_create_dn(role: Role) -> bool:      return role in ("GM", "Finance", "Shift Lead")
def can_edit_dn_full(role: Role) -> bool:   return role in ("GM", "Finance")
def can_edit_dn_notes_only(role: Role) -> bool: return role == "Shift Lead"
def can_pair(role: Role) -> bool:           return role in ("GM", "Finance")
