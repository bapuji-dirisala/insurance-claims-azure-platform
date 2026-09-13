-- Minimum-privilege grants for each principal.
--
-- Principals:
--   * `claims_platform_sp` — the service principal running production jobs
--   * `claims_actuaries`   — Entra ID group with read access to gold
--   * `claims_engineers`   — Entra ID group with full silver + ability to run notebooks
--   * `claims_adf_sp`      — ADF managed identity (bronze writer)

-- Bronze: only the ADF SP + platform SP can touch it.
GRANT ALL PRIVILEGES ON CATALOG claims_bronze TO `claims_platform_sp`;
GRANT USE CATALOG, USE SCHEMA, SELECT ON CATALOG claims_bronze TO `claims_adf_sp`;
GRANT MODIFY ON CATALOG claims_bronze TO `claims_adf_sp`;

-- Silver: engineers get full access; platform SP has operational privileges.
GRANT ALL PRIVILEGES ON CATALOG claims_silver TO `claims_platform_sp`;
GRANT USE CATALOG, USE SCHEMA, SELECT, MODIFY, CREATE TABLE ON CATALOG claims_silver TO `claims_engineers`;

-- Gold: actuaries read-only; engineers read-only (silver is their playground);
-- platform SP writes.
GRANT ALL PRIVILEGES ON CATALOG claims_gold TO `claims_platform_sp`;
GRANT USE CATALOG, USE SCHEMA, SELECT ON CATALOG claims_gold TO `claims_actuaries`;
GRANT USE CATALOG, USE SCHEMA, SELECT ON CATALOG claims_gold TO `claims_engineers`;
