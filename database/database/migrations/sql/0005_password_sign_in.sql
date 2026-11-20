CREATE TABLE identity.password_credentials (
    user_id uuid PRIMARY KEY REFERENCES identity.users (id),
    email text NOT NULL UNIQUE CHECK (email = lower(btrim(email)) AND email <> ''),
    password_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE identity.sign_in_limits (
    bucket bytea PRIMARY KEY,
    window_started_at timestamptz NOT NULL DEFAULT now(),
    attempts integer NOT NULL CHECK (attempts > 0)
);

CREATE INDEX sign_in_limits_window_idx ON identity.sign_in_limits (window_started_at);
