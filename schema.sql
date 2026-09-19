-- Schéma complet pour la gestion de SCI à l'IS (Impôt sur les Sociétés) avec Turso / SQLite

-- 1. Informations générales sur la SCI & Paramètres SMTP
CREATE TABLE IF NOT EXISTS sci_info (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT 'Ma SCI Immobilière',
    siren TEXT DEFAULT '',
    tax_regime TEXT DEFAULT 'IS', -- Régime fiscal : 'IS' (Impôt sur les Sociétés)
    address TEXT DEFAULT '',
    postal_code TEXT DEFAULT '',
    city TEXT DEFAULT '',
    manager_name TEXT DEFAULT '',
    manager_email TEXT DEFAULT '',
    manager_phone TEXT DEFAULT '',
    iban TEXT DEFAULT '',
    bic TEXT DEFAULT '',
    share_capital REAL DEFAULT 1000.0, -- Capital social statutaire de la SCI
    -- Configuration SMTP pour l'envoi d'emails
    smtp_server TEXT DEFAULT '',
    smtp_port INTEGER DEFAULT 587,
    smtp_username TEXT DEFAULT '',
    smtp_password TEXT DEFAULT '',
    smtp_use_tls INTEGER DEFAULT 1,
    smtp_sender_email TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insérer la ligne unique par défaut si elle n'existe pas
INSERT OR IGNORE INTO sci_info (id, name, tax_regime) VALUES (1, 'Ma SCI Immobilière', 'IS');

-- 2. Biens immobiliers / Appartements / Lots (avec paramètres d'amortissement IS)
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'Appartement', -- Appartement, Parking, Local commercial, Maison, Cave
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    surface REAL DEFAULT 0.0,
    rooms INTEGER DEFAULT 1,
    floor INTEGER DEFAULT 0,
    door_number TEXT DEFAULT '',
    tantiemes REAL DEFAULT 1000.0, -- Quote-part de copropriété (en millièmes ou tantièmes)
    acquisition_date TEXT,
    acquisition_price REAL DEFAULT 0.0,
    notary_fees REAL DEFAULT 0.0, -- Frais de notaire / d'acquisition
    land_share_pct REAL DEFAULT 15.0, -- Quote-part du terrain non amortissable (généralement 15-20%)
    amortization_years INTEGER DEFAULT 25, -- Durée d'amortissement comptable de l'immeuble (ex: 25 ou 30 ans)
    furniture_value REAL DEFAULT 0.0, -- Valeur du mobilier amortissable
    furniture_years INTEGER DEFAULT 5, -- Durée d'amortissement du mobilier (ex: 5 à 7 ans)
    target_rent REAL DEFAULT 0.0, -- Loyer cible HC
    target_charges REAL DEFAULT 0.0, -- Provision pour charges cible
    status TEXT DEFAULT 'vacant', -- 'loue', 'vacant', 'en_travaux'
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Locataires (avec paramètres IRL)
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    lease_start TEXT NOT NULL, -- YYYY-MM-DD
    lease_end TEXT,           -- YYYY-MM-DD (optionnel si en cours)
    rent_amount REAL NOT NULL DEFAULT 0.0, -- Loyer mensuel HC en euros
    charges_provision REAL NOT NULL DEFAULT 0.0, -- Provision mensuelle sur charges
    deposit_amount REAL DEFAULT 0.0, -- Dépôt de garantie versé
    is_active INTEGER DEFAULT 1, -- 1 = locataire actuel, 0 = ancien locataire
    guarantor_info TEXT DEFAULT '',
    -- Paramètres d'indexation IRL
    irl_reference_quarter TEXT DEFAULT 'T3 2024', -- Trimestre de référence du bail
    irl_reference_value REAL DEFAULT 144.51,      -- Valeur de l'indice de référence
    last_revision_date TEXT DEFAULT '',           -- Date de la dernière révision YYYY-MM-DD
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE SET NULL
);

-- 4. Échéances de loyers et encaissements
CREATE TABLE IF NOT EXISTS rent_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    property_id INTEGER NOT NULL,
    period_month INTEGER NOT NULL, -- 1 à 12
    period_year INTEGER NOT NULL,  -- ex: 2026
    due_date TEXT NOT NULL,        -- YYYY-MM-DD
    rent_amount REAL NOT NULL,     -- Loyer HC dû
    charges_amount REAL NOT NULL,  -- Charges dues
    total_due REAL NOT NULL,       -- Total = rent_amount + charges_amount
    amount_paid REAL DEFAULT 0.0,  -- Montant réellement payé
    payment_date TEXT,             -- Date d'encaissement YYYY-MM-DD
    payment_method TEXT DEFAULT 'Virement', -- Virement, Chèque, Espèces, Prélèvement
    status TEXT DEFAULT 'en_attente', -- 'paye', 'partiel', 'en_attente', 'retard'
    notes TEXT DEFAULT '',
    receipt_sent_date TEXT,        -- Date d'envoi de quittance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rent_tenant_period 
ON rent_payments(tenant_id, period_year, period_month);

-- 5. Charges globales de la SCI (structure, emprunts, assurances, comptabilité)
CREATE TABLE IF NOT EXISTS sci_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, -- YYYY-MM-DD
    category TEXT NOT NULL, 
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT DEFAULT 'Virement',
    invoice_ref TEXT DEFAULT '',
    is_deductible_2072 INTEGER DEFAULT 1, -- Déductible au compte de résultat IS
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Charges spécifiques aux appartements / lots (copropriété, réparations, TEOM)
CREATE TABLE IF NOT EXISTS property_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    is_recoverable INTEGER DEFAULT 0, -- 1 = Récupérable auprès du locataire, 0 = Non récupérable (déductible IS)
    tenant_id INTEGER,
    is_regularized INTEGER DEFAULT 0,
    invoice_ref TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE SET NULL
);

-- 7. Comptes Courants d'Associés (CCA) pour SCI à l'IS
CREATE TABLE IF NOT EXISTS partner_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_name TEXT NOT NULL,
    date TEXT NOT NULL,
    type TEXT NOT NULL, -- 'apport' ou 'remboursement'
    amount REAL NOT NULL,
    description TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Emprunts Bancaires & Crédits Immobiliers
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER, -- Optionnel : rattaché à un bien spécifique
    bank_name TEXT NOT NULL,
    loan_reference TEXT DEFAULT '',
    start_date TEXT NOT NULL, -- YYYY-MM-DD (date de première mensualité)
    amount REAL NOT NULL, -- Capital emprunté en euros
    annual_interest_rate REAL NOT NULL, -- Taux d'intérêt annuel en % (ex: 3.15)
    duration_months INTEGER NOT NULL, -- Durée en mois (ex: 240 pour 20 ans)
    monthly_insurance REAL DEFAULT 0.0, -- Assurance mensuelle en euros
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE SET NULL
);

-- 9. Indices Trimestriels de Référence des Loyers (IRL INSEE)
CREATE TABLE IF NOT EXISTS irl_indices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quarter TEXT UNIQUE NOT NULL, -- ex: 'T1 2023', 'T2 2023', 'T3 2023', 'T4 2023', 'T1 2024', etc.
    value REAL NOT NULL, -- Valeur de l'indice
    published_date TEXT DEFAULT '' -- Date de publication au JO
);

-- Insertion des indices IRL récents officiels de l'INSEE
INSERT OR IGNORE INTO irl_indices (quarter, value, published_date) VALUES 
('T1 2023', 138.61, '2023-04-14'),
('T2 2023', 140.59, '2023-07-13'),
('T3 2023', 141.03, '2023-10-13'),
('T4 2023', 142.06, '2024-01-16'),
('T1 2024', 143.46, '2024-04-12'),
('T2 2024', 145.17, '2024-07-12'),
('T3 2024', 144.51, '2024-10-15'),
('T4 2024', 144.82, '2025-01-16'),
('T1 2025', 145.45, '2025-04-15');

-- 10. Coffre-fort Numérique & Gestion Électronique des Documents (GED)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL, -- 'Bail & État des lieux', 'Assurance', 'Diagnostic', 'Facture / Devis', 'Statuts & Kbis', 'Autre'
    entity_type TEXT NOT NULL, -- 'property', 'tenant', 'sci', 'loan'
    entity_id INTEGER, -- Identifiant de l'entité liée
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,        -- URL Cloudinary (secure_url) ou chemin local (legacy)
    cloudinary_public_id TEXT DEFAULT '', -- public_id Cloudinary pour la suppression
    file_size INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
CREATE INDEX IF NOT EXISTS idx_tenants_property ON tenants(property_id);
CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active);
CREATE INDEX IF NOT EXISTS idx_rent_payments_date ON rent_payments(period_year, period_month);
CREATE INDEX IF NOT EXISTS idx_sci_expenses_date ON sci_expenses(date);
CREATE INDEX IF NOT EXISTS idx_property_expenses_property ON property_expenses(property_id);
CREATE INDEX IF NOT EXISTS idx_partner_accounts_name ON partner_accounts(partner_name);
CREATE INDEX IF NOT EXISTS idx_loans_property ON loans(property_id);
CREATE INDEX IF NOT EXISTS idx_documents_entity ON documents(entity_type, entity_id);

-- 11. Utilisateurs & Authentification
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT DEFAULT '',
    role TEXT DEFAULT 'admin', -- 'admin' ou 'gestionnaire'
    is_active INTEGER DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
