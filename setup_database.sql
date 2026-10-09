-- =============================================================================
-- Gold & Silver Loan Management System — Database Setup
-- Run ONCE on server: mysql -h 127.0.0.1 -P 3306 -u root -p < setup_database.sql
-- Or via SSH:  ssh -p 56022 root@38.159.122.193 "mysql -u root -p" < setup_database.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `gold_loan_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `gold_loan_db`;

-- -------------------------
-- 1. users
-- -------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id`                     INT            NOT NULL AUTO_INCREMENT,
  `username`               VARCHAR(50)    NOT NULL,
  `email`                  VARCHAR(100)   NOT NULL,
  `full_name`              VARCHAR(100)   NOT NULL,
  `password_hash`          VARCHAR(255)   NOT NULL,
  `role`                   ENUM('admin','lender','viewer') NOT NULL DEFAULT 'lender',
  `is_active`              TINYINT(1)     NOT NULL DEFAULT 1,
  `must_change_password`   TINYINT(1)     NOT NULL DEFAULT 0,
  `last_login`             DATETIME       NULL,
  `failed_login_attempts`  INT            NOT NULL DEFAULT 0,
  `locked_until`           DATETIME       NULL,
  `phone`                  VARCHAR(20)    NULL,
  `created_by`             INT            NULL,
  `created_at`             DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`             DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_email`    (`email`),
  KEY `ix_users_username`        (`username`),
  KEY `ix_users_email`           (`email`),
  CONSTRAINT `fk_users_created_by` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 2. login_history
-- -------------------------
CREATE TABLE IF NOT EXISTS `login_history` (
  `id`             INT          NOT NULL AUTO_INCREMENT,
  `user_id`        INT          NULL,
  `username`       VARCHAR(50)  NOT NULL,
  `login_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `logout_at`      DATETIME     NULL,
  `ip_address`     VARCHAR(45)  NULL,
  `success`        TINYINT(1)   NOT NULL DEFAULT 1,
  `failure_reason` VARCHAR(100) NULL,
  `session_id`     VARCHAR(64)  NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_lh_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 3. customers
-- -------------------------
CREATE TABLE IF NOT EXISTS `customers` (
  `id`                   INT          NOT NULL AUTO_INCREMENT,
  `customer_id`          VARCHAR(20)  NOT NULL,
  `full_name`            VARCHAR(100) NOT NULL,
  `father_spouse_name`   VARCHAR(100) NULL,
  `date_of_birth`        DATE         NULL,
  `mobile`               VARCHAR(15)  NOT NULL,
  `alt_mobile`           VARCHAR(15)  NULL,
  `address`              TEXT         NULL,
  `city`                 VARCHAR(50)  NULL,
  `state`                VARCHAR(50)  NULL,
  `pincode`              VARCHAR(10)  NULL,
  `photo_path`           VARCHAR(500) NULL,
  `kyc_type`             ENUM('aadhaar','pan','voter_id','passport','driving_licence','other') NULL,
  `kyc_ref_encrypted`    VARCHAR(500) NULL,
  `kyc_consent_date`     DATETIME     NULL,
  `kyc_status`           ENUM('pending','verified','rejected') NOT NULL DEFAULT 'pending',
  `kyc_verified_by`      INT          NULL,
  `kyc_verified_at`      DATETIME     NULL,
  `kyc_rejection_reason` TEXT         NULL,
  `notes`                TEXT         NULL,
  `is_active`            TINYINT(1)   NOT NULL DEFAULT 1,
  `created_by`           INT          NULL,
  `created_at`           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_customers_customer_id` (`customer_id`),
  KEY `ix_customers_customer_id` (`customer_id`),
  KEY `ix_customers_full_name`   (`full_name`),
  KEY `ix_customers_mobile`      (`mobile`),
  CONSTRAINT `fk_cust_verified_by` FOREIGN KEY (`kyc_verified_by`) REFERENCES `users`(`id`),
  CONSTRAINT `fk_cust_created_by`  FOREIGN KEY (`created_by`)      REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 4. kyc_documents
-- -------------------------
CREATE TABLE IF NOT EXISTS `kyc_documents` (
  `id`                INT          NOT NULL AUTO_INCREMENT,
  `customer_id`       INT          NOT NULL,
  `doc_type`          VARCHAR(50)  NOT NULL,
  `doc_ref_encrypted` VARCHAR(500) NULL,
  `file_path`         VARCHAR(500) NULL,
  `is_primary`        TINYINT(1)   NOT NULL DEFAULT 0,
  `uploaded_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `uploaded_by`       INT          NULL,
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_kyc_customer_id` (`customer_id`),
  CONSTRAINT `fk_kyc_customer_id`  FOREIGN KEY (`customer_id`) REFERENCES `customers`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_kyc_uploaded_by`  FOREIGN KEY (`uploaded_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 5. loans
-- -------------------------
CREATE TABLE IF NOT EXISTS `loans` (
  `id`                     INT            NOT NULL AUTO_INCREMENT,
  `loan_number`            VARCHAR(30)    NOT NULL,
  `customer_id`            INT            NOT NULL,
  `status`                 ENUM('draft','pending_approval','approved','disbursed','active',
                                'partially_repaid','overdue','closed','renewed','auction_review')
                           NOT NULL DEFAULT 'draft',
  `principal_amount`       DECIMAL(15,2)  NOT NULL,
  `approved_amount`        DECIMAL(15,2)  NULL,
  `disbursed_amount`       DECIMAL(15,2)  NULL,
  `outstanding_principal`  DECIMAL(15,2)  NULL,
  `outstanding_interest`   DECIMAL(15,2)  NULL,
  `total_outstanding`      DECIMAL(15,2)  NULL,
  `interest_rate`          DECIMAL(5,2)   NOT NULL,
  `interest_method`        ENUM('simple','reducing_balance') NOT NULL DEFAULT 'simple',
  `tenure_days`            INT            NOT NULL,
  `disbursement_date`      DATE           NULL,
  `maturity_date`          DATE           NULL,
  `ltv_percentage`         DECIMAL(5,2)   NULL,
  `total_collateral_value` DECIMAL(15,2)  NULL,
  `processing_fee`         DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
  `other_charges`          DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
  `payment_mode`           ENUM('cash','bank_transfer','upi','cheque','other') NOT NULL DEFAULT 'cash',
  `approved_by`            INT            NULL,
  `approved_at`            DATETIME       NULL,
  `remarks`                TEXT           NULL,
  `renewal_count`          INT            NOT NULL DEFAULT 0,
  `parent_loan_id`         INT            NULL,
  `created_by`             INT            NULL,
  `created_at`             DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`             DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_loans_loan_number` (`loan_number`),
  KEY `ix_loans_loan_number`   (`loan_number`),
  KEY `ix_loans_customer_id`   (`customer_id`),
  KEY `ix_loans_status`        (`status`),
  CONSTRAINT `fk_loans_customer_id`    FOREIGN KEY (`customer_id`)   REFERENCES `customers`(`id`),
  CONSTRAINT `fk_loans_approved_by`    FOREIGN KEY (`approved_by`)   REFERENCES `users`(`id`),
  CONSTRAINT `fk_loans_created_by`     FOREIGN KEY (`created_by`)    REFERENCES `users`(`id`),
  CONSTRAINT `fk_loans_parent_loan_id` FOREIGN KEY (`parent_loan_id`) REFERENCES `loans`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 6. collateral_items
-- -------------------------
CREATE TABLE IF NOT EXISTS `collateral_items` (
  `id`                    INT            NOT NULL AUTO_INCREMENT,
  `loan_id`               INT            NOT NULL,
  `metal_type`            ENUM('gold','silver') NOT NULL,
  `item_category`         ENUM('ring','chain','necklace','bracelet','coin','bar','utensils','other')
                          NOT NULL DEFAULT 'other',
  `gross_weight`          DECIMAL(10,3)  NOT NULL,
  `stone_weight`          DECIMAL(10,3)  NOT NULL DEFAULT 0.000,
  `net_weight`            DECIMAL(10,3)  NOT NULL,
  `purity`                VARCHAR(10)    NOT NULL,
  `purity_value`          DECIMAL(8,4)   NULL,
  `assayed_purity`        TINYINT(1)     NOT NULL DEFAULT 0,
  `market_rate`           DECIMAL(15,4)  NULL,
  `valuation_rate`        DECIMAL(15,4)  NULL,
  `valuation_date`        DATETIME       NULL,
  `pure_metal_weight`     DECIMAL(10,4)  NULL,
  `indicative_value`      DECIMAL(15,2)  NULL,
  `description`           TEXT           NULL,
  `photo_paths`           TEXT           NULL,
  `tag_number`            VARCHAR(50)    NULL,
  `storage_location`      VARCHAR(100)   NULL,
  `appraiser_remarks`     TEXT           NULL,
  `is_released`           TINYINT(1)     NOT NULL DEFAULT 0,
  `release_date`          DATE           NULL,
  `release_authorized_by` INT            NULL,
  `created_at`            DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_collateral_tag_number` (`tag_number`),
  KEY `ix_collateral_loan_id`   (`loan_id`),
  KEY `ix_collateral_tag_number`(`tag_number`),
  CONSTRAINT `fk_coll_loan_id`   FOREIGN KEY (`loan_id`)               REFERENCES `loans`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_coll_rel_auth`  FOREIGN KEY (`release_authorized_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 7. repayments
-- -------------------------
CREATE TABLE IF NOT EXISTS `repayments` (
  `id`                      INT            NOT NULL AUTO_INCREMENT,
  `loan_id`                 INT            NOT NULL,
  `receipt_number`          VARCHAR(30)    NOT NULL,
  `principal_paid`          DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
  `interest_paid`           DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
  `fee_paid`                DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
  `penalty_paid`            DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
  `total_paid`              DECIMAL(15,2)  NOT NULL,
  `payment_date`            DATE           NOT NULL,
  `payment_mode`            ENUM('cash','bank_transfer','upi','cheque','other') NOT NULL DEFAULT 'cash',
  `transaction_ref`         VARCHAR(100)   NULL,
  `balance_principal_after` DECIMAL(15,2)  NULL,
  `balance_interest_after`  DECIMAL(15,2)  NULL,
  `total_outstanding_after` DECIMAL(15,2)  NULL,
  `is_reversed`             TINYINT(1)     NOT NULL DEFAULT 0,
  `reversal_reason`         TEXT           NULL,
  `reversed_by`             INT            NULL,
  `reversed_at`             DATETIME       NULL,
  `created_by`              INT            NULL,
  `notes`                   TEXT           NULL,
  `created_at`              DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`              DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_repayments_receipt_number` (`receipt_number`),
  KEY `ix_repayments_loan_id`        (`loan_id`),
  KEY `ix_repayments_receipt_number` (`receipt_number`),
  KEY `ix_repayments_payment_date`   (`payment_date`),
  CONSTRAINT `fk_rep_loan_id`      FOREIGN KEY (`loan_id`)     REFERENCES `loans`(`id`),
  CONSTRAINT `fk_rep_reversed_by`  FOREIGN KEY (`reversed_by`) REFERENCES `users`(`id`),
  CONSTRAINT `fk_rep_created_by`   FOREIGN KEY (`created_by`)  REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 8. loan_status_history
-- -------------------------
CREATE TABLE IF NOT EXISTS `loan_status_history` (
  `id`          INT         NOT NULL AUTO_INCREMENT,
  `loan_id`     INT         NOT NULL,
  `from_status` VARCHAR(30) NULL,
  `to_status`   VARCHAR(30) NOT NULL,
  `changed_by`  INT         NULL,
  `remarks`     TEXT        NULL,
  `changed_at`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_lsh_loan_id` (`loan_id`),
  CONSTRAINT `fk_lsh_loan_id`    FOREIGN KEY (`loan_id`)    REFERENCES `loans`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_lsh_changed_by` FOREIGN KEY (`changed_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 9. interest_accruals
-- -------------------------
CREATE TABLE IF NOT EXISTS `interest_accruals` (
  `id`                  INT           NOT NULL AUTO_INCREMENT,
  `loan_id`             INT           NOT NULL,
  `accrual_date`        DATE          NOT NULL,
  `days_accrued`        INT           NOT NULL,
  `principal_balance`   DECIMAL(15,2) NOT NULL,
  `interest_accrued`    DECIMAL(15,2) NOT NULL,
  `cumulative_interest` DECIMAL(15,2) NOT NULL,
  `created_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_ia_loan_id` (`loan_id`),
  CONSTRAINT `fk_ia_loan_id` FOREIGN KEY (`loan_id`) REFERENCES `loans`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 10. metal_rate_history
-- -------------------------
CREATE TABLE IF NOT EXISTS `metal_rate_history` (
  `id`             INT            NOT NULL AUTO_INCREMENT,
  `metal_type`     ENUM('gold','silver') NOT NULL,
  `rate_per_gram`  DECIMAL(15,4)  NOT NULL,
  `rate_per_10gram`DECIMAL(15,4)  NOT NULL,
  `currency`       VARCHAR(10)    NOT NULL DEFAULT 'INR',
  `source`         VARCHAR(50)    NOT NULL,
  `purity_basis`   VARCHAR(20)    NOT NULL DEFAULT '24K/999',
  `is_stale`       TINYINT(1)     NOT NULL DEFAULT 0,
  `fetched_at`     DATETIME       NOT NULL,
  `created_at`     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_mrh_metal_type` (`metal_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 11. audit_logs
-- -------------------------
CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id`          INT          NOT NULL AUTO_INCREMENT,
  `user_id`     INT          NULL,
  `username`    VARCHAR(50)  NULL,
  `action`      VARCHAR(100) NOT NULL,
  `entity_type` VARCHAR(50)  NULL,
  `entity_id`   INT          NULL,
  `entity_ref`  VARCHAR(50)  NULL,
  `old_value`   TEXT         NULL,
  `new_value`   TEXT         NULL,
  `ip_address`  VARCHAR(45)  NULL,
  `extra`       TEXT         NULL,
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_al_username`    (`username`),
  KEY `ix_al_action`      (`action`),
  KEY `ix_al_entity_type` (`entity_type`),
  KEY `ix_al_created_at`  (`created_at`),
  CONSTRAINT `fk_al_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 12. app_settings
-- -------------------------
CREATE TABLE IF NOT EXISTS `app_settings` (
  `id`            INT          NOT NULL AUTO_INCREMENT,
  `setting_key`   VARCHAR(100) NOT NULL,
  `setting_value` TEXT         NULL,
  `description`   TEXT         NULL,
  `is_encrypted`  TINYINT(1)   NOT NULL DEFAULT 0,
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_by`    INT          NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_app_settings_key` (`setting_key`),
  KEY `ix_app_settings_key` (`setting_key`),
  CONSTRAINT `fk_as_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- 13. backup_history
-- -------------------------
CREATE TABLE IF NOT EXISTS `backup_history` (
  `id`               INT          NOT NULL AUTO_INCREMENT,
  `backup_path`      VARCHAR(500) NULL,
  `backup_type`      ENUM('manual','automatic') NOT NULL DEFAULT 'manual',
  `status`           ENUM('success','failed')   NOT NULL DEFAULT 'success',
  `file_size_bytes`  INT          NULL,
  `error_message`    TEXT         NULL,
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by`       INT          NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_bh_created_by` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Default application settings
-- =============================================================================
INSERT IGNORE INTO `app_settings` (`setting_key`, `setting_value`, `description`) VALUES
  ('session_timeout_minutes',  '30',           'Auto-logout after N minutes of inactivity'),
  ('max_ltv_gold',             '75',           'Maximum LTV % allowed for gold loans'),
  ('max_ltv_silver',           '60',           'Maximum LTV % allowed for silver loans'),
  ('default_interest_rate',    '24',           'Default annual interest rate (%)'),
  ('default_tenure_days',      '180',          'Default loan tenure in days'),
  ('default_processing_fee',   '0',            'Default processing fee (INR)'),
  ('gold_api_key',             '',             'API key for goldapi.io live rates'),
  ('rate_provider',            'goldapi',      'Metal rate provider: goldapi or manual'),
  ('rate_stale_minutes',       '60',           'Minutes before a cached rate is marked stale'),
  ('company_name',             'Gold Silver Loan Services', 'Company name on receipts/reports'),
  ('company_address',          '',             'Company address on receipts/reports'),
  ('company_phone',            '',             'Company phone on receipts/reports'),
  ('company_gstin',            '',             'GSTIN on receipts/reports'),
  ('auction_grace_days',       '7',            'Grace days before overdue loan goes to auction review'),
  ('penalty_rate_per_day',     '0.05',         'Penalty interest % per day on overdue loans');

-- =============================================================================
-- NOTE: The default admin user (admin / Admin@1234) is created automatically
--       by the application on first launch when the users table is empty.
--       You do NOT need to insert it here.
-- =============================================================================

SELECT 'Database setup complete.' AS status;
SELECT TABLE_NAME, TABLE_ROWS
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'gold_loan_db'
 ORDER BY TABLE_NAME;
