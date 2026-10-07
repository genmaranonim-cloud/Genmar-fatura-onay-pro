"""Backward-compatible imports for the XML-first invoice reader."""
from invoice_reader import approval_description, read_invoice, read_ubl_invoice

__all__ = ["approval_description", "read_invoice", "read_ubl_invoice"]
