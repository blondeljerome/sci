-- Schéma initial pour la gestion de SCI avec Turso / SQLite

-- 1. Informations générales sur la SCI
CREATE TABLE IF NOT EXISTS sci_info (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT 'Ma SCI Immobilière',
    siren TEXT DEFAULT '',
    address TEXT DEFAULT '',
    postal_code TEXT DEFAULT '',
    city TEXT DEFAULT '',
    manager_name TEXT DEFAULT '',
    manager_email TEXT DEFAULT '',
    manager_phone TEXT DEFAULT '',
    iban TEXT DEFAULT '',
    bic TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insérer la ligne unique par défaut si elle n'existe pas
INSERT OR IGNORE INTO sci_info (id, name) VALUES (1, 'Ma SCI Immobilière');

-- 2. Biens immobiliers / Appartements / Lots
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
    target_rent REAL DEFAULT 0.0, -- Loyer cible HC
    target_charges REAL DEFAULT 0.0, -- Provision pour charges cible
    status TEXT DEFAULT 'vacant', -- 'loue', 'vacant', 'en_travaux'
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Locataires
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

-- Contrainte d'unicité pour une période donnée et un locataire
CREATE UNIQUE INDEX IF NOT EXISTS idx_rent_tenant_period 
ON rent_payments(tenant_id, period_year, period_month);

-- 5. Charges globales de la SCI (structure, emprunts, assurances, comptabilité)
CREATE TABLE IF NOT EXISTS sci_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, -- YYYY-MM-DD
    category TEXT NOT NULL, 
    -- Catégories courantes :
    -- 'Assurance PNO', 'Honoraires comptables & gestion', 'Frais bancaires',
    -- 'Taxe foncière (part SCI)', 'Intérêts d''emprunt', 'Remboursement capital emprunt',
    -- 'Gros travaux de structure', 'Frais juridiques / assemblée', 'Autre'
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT DEFAULT 'Virement',
    invoice_ref TEXT DEFAULT '',
    is_deductible_2072 INTEGER DEFAULT 1, -- Déductible sur la déclaration 2072
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Charges spécifiques aux appartements / lots (copropriété, réparations, TEOM)
CREATE TABLE IF NOT EXISTS property_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD
    category TEXT NOT NULL,
    -- Catégories :
    -- 'Charges de copropriété générales', 'Eau / Compteurs', 'Chauffage collectif',
    -- 'Taxe ordures ménagères (TEOM)', 'Petites réparations locatives', 'Travaux propriétaire', 'Autre'
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    is_recoverable INTEGER DEFAULT 0, -- 1 = Récupérable auprès du locataire, 0 = Non récupérable
    tenant_id INTEGER, -- Optionnel : rattaché à un locataire pour le calcul de régularisation
    is_regularized INTEGER DEFAULT 0, -- 1 si déjà régularisé auprès du locataire
    invoice_ref TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE SET NULL
);

-- Index pour optimiser les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
CREATE INDEX IF NOT EXISTS idx_tenants_property ON tenants(property_id);
CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active);
CREATE INDEX IF NOT EXISTS idx_rent_payments_date ON rent_payments(period_year, period_month);
CREATE INDEX IF NOT EXISTS idx_rent_payments_status ON rent_payments(status);
CREATE INDEX IF NOT EXISTS idx_sci_expenses_date ON sci_expenses(date);
CREATE INDEX IF NOT EXISTS idx_property_expenses_property ON property_expenses(property_id);
CREATE INDEX IF NOT EXISTS idx_property_expenses_date ON property_expenses(date);
