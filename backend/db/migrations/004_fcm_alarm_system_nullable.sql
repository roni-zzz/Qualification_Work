-- Allow token registration before user is linked to a warehouse/system.
-- Tokens can then be resolved by user_id once the user is linked later.

ALTER TABLE fcm_tokens ALTER COLUMN alarm_system_id DROP NOT NULL;
