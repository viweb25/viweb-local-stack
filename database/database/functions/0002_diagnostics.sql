-- Developer diagnostics. No customer rows. SECURITY INVOKER, never SECURITY DEFINER.
CREATE SCHEMA platform;
CREATE FUNCTION platform.usp_database_name() RETURNS text
LANGUAGE sql STABLE AS $$ SELECT current_database()::text $$;
CREATE FUNCTION platform.usp_database_size_bytes() RETURNS bigint
LANGUAGE sql STABLE AS $$ SELECT pg_database_size(current_database()) $$;
CREATE FUNCTION platform.usp_server_version() RETURNS text
LANGUAGE sql STABLE AS $$ SELECT current_setting('server_version') $$;
CREATE FUNCTION platform.usp_schema_version() RETURNS text
LANGUAGE sql STABLE AS $$ SELECT version_num::text FROM public.alembic_version $$;
CREATE FUNCTION platform.usp_connection_count() RETURNS bigint
LANGUAGE sql STABLE AS $$ SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() $$;
CREATE FUNCTION platform.usp_active_connection_count() RETURNS bigint
LANGUAGE sql STABLE AS $$ SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'active' $$;
CREATE FUNCTION platform.usp_transaction_read_only() RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT current_setting('transaction_read_only')::boolean $$;
CREATE FUNCTION platform.usp_is_replica() RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT pg_is_in_recovery() $$;
CREATE FUNCTION platform.usp_table_sizes() RETURNS TABLE(table_name text, bytes bigint)
LANGUAGE sql STABLE AS $$
  SELECT schemaname || '.' || relname, pg_total_relation_size(relid)
  FROM pg_stat_user_tables WHERE schemaname = 'public' ORDER BY relname
$$;
CREATE FUNCTION platform.usp_migration_table_exists() RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT to_regclass('public.alembic_version') IS NOT NULL $$;
REVOKE ALL ON SCHEMA platform FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA platform FROM PUBLIC;
