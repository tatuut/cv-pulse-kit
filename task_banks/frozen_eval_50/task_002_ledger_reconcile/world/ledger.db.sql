CREATE TABLE invoices (
    invoice_id TEXT PRIMARY KEY,
    amount_cents INTEGER NOT NULL,
    tax_cents INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE system_flags (
    flag_name TEXT PRIMARY KEY,
    flag_value TEXT NOT NULL
);

INSERT INTO invoices VALUES ('INV-2026-041', 10000, 1000, 11000, 'RECONCILED');
INSERT INTO invoices VALUES ('INV-2026-042', 25000, 2500, 25000, 'PENDING_RECONCILE');
INSERT INTO invoices VALUES ('INV-2026-043', 40000, 4000, 44000, 'RECONCILED');
INSERT INTO system_flags VALUES ('audit_lock', 'ENABLED');
