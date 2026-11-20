-- Company records continue to live in public.organisations.
CREATE SCHEMA identity;

-- This UUID is the stable actor ID used by the SaaS.
CREATE TABLE identity.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name text,
    email text,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- OpenID Connect identifies a person by the issuer and subject together.
CREATE TABLE identity.external_identities (
    issuer text NOT NULL,
    subject text NOT NULL,
    user_id uuid NOT NULL REFERENCES identity.users (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (issuer, subject)
);

CREATE INDEX external_identities_user_idx ON identity.external_identities (user_id);

-- A user can have a different role at every company.
CREATE TABLE identity.memberships (
    org_id uuid NOT NULL REFERENCES public.organisations (id),
    user_id uuid NOT NULL REFERENCES identity.users (id),
    role text NOT NULL CHECK (role IN ('owner', 'admin', 'operator', 'viewer')),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, user_id)
);

CREATE INDEX memberships_active_user_idx
    ON identity.memberships (user_id, org_id) WHERE status = 'active';

-- Store only a hash of the random browser token.
CREATE TABLE identity.sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES identity.users (id),
    token_hash bytea NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (octet_length(token_hash) = 32),
    CHECK (expires_at > created_at)
);

CREATE INDEX sessions_active_user_idx
    ON identity.sessions (user_id) WHERE revoked_at IS NULL;

CREATE INDEX sessions_expiry_idx ON identity.sessions (expires_at);
