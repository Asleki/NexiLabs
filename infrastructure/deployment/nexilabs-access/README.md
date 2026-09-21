# NexiLabs Public Access Boundary

This package defines a replaceable outer access policy for the future public
NexiLabs application hostname.

It is intentionally separate from NexiLabs product authentication.

## Modes

`DEVELOPMENT_PRIVATE`

- Google OAuth/OIDC is required at the public edge.
- Authorization is an exact email allowlist stored only on the server.
- Unknown or missing configuration does not become public.
- oauth2-proxy listens only on `127.0.0.1:4180`.
- Caddy is the only public HTTP/HTTPS listener.
- The normal NexiLabs service worker is replaced at the private edge with a
  tiny cleanup worker so a previously authorized browser cannot keep opening
  the cached application while offline.

`PUBLIC`

- The outer Google allowlist is removed.
- Public site access is allowed.
- Normal NexiLabs Guest/Developer/Admin authorization remains unchanged.
- The normal PWA service worker is served again by the application upstream.

Changing modes is a deployment operation. It is not a frontend feature flag.

## Private material

The repository must never contain:

- the real Google OAuth client secret;
- the oauth2-proxy cookie secret;
- the real allowed-email file.

The production paths are:

- `/etc/nexa/nexilabs-access.env`
- `/etc/nexa/nexilabs-access/allowed-emails`

The allowlist contains one exact email address per line.

## Boundary order

```text
Internet
  |
Caddy :443
  |
  +-- /oauth2/* --> oauth2-proxy 127.0.0.1:4180
  |
  +-- other paths --> forward_auth --> exact email allowlist
                                      |
                                      +--> NexiLabs PWA upstream
```

The Google gate is an outer deployment boundary only. It does not replace
Developer credentials, Developer Enigma, Admin eligibility, Admin credentials,
or Admin Enigma.

## Public launch

Public launch is explicit:

1. change `NEXILABS_ACCESS_MODE=PUBLIC` in the private server environment;
2. run the access-mode activation script;
3. qualify the resulting Caddy configuration and public behavior.

There is no implicit fallback from invalid/missing configuration to PUBLIC.
