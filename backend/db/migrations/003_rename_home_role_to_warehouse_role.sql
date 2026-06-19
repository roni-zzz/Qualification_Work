-- Migrate legacy user_table.home_role to user_table.warehouse_role, then drop legacy column.
-- Safe to run multiple times.

ALTER TABLE user_table ADD COLUMN IF NOT EXISTS warehouse_role VARCHAR(20) DEFAULT 'admin';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'user_table' AND column_name = 'home_role'
    ) THEN
        EXECUTE '
            UPDATE user_table
            SET warehouse_role = COALESCE(NULLIF(TRIM(home_role), ''''''), ''admin'')
            WHERE COALESCE(TRIM(warehouse_role), '''''') = ''''''
        ';
        EXECUTE 'ALTER TABLE user_table DROP COLUMN IF EXISTS home_role';
    END IF;
END $$;

ALTER TABLE user_table ALTER COLUMN warehouse_role SET DEFAULT 'admin';
