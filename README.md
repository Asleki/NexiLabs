<div align="center">

<img src="frontend/public/brand/nexilabs/vectors/nexilabs_logo_horizontal.svg" alt="NexiLabs" width="420">

# NexiLabs

**Governed simulation, registry, identity/authentication and geospatial platform for the Nexa ecosystem.**

[![Main branch](https://img.shields.io/github/last-commit/Asleki/NexiLabs/main?label=main&logo=github)](https://github.com/Asleki/NexiLabs/commits/main)
[![Repository size](https://img.shields.io/github/repo-size/Asleki/NexiLabs?logo=github)](https://github.com/Asleki/NexiLabs)
[![Top language](https://img.shields.io/github/languages/top/Asleki/NexiLabs)](https://github.com/Asleki/NexiLabs)
![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-governed%20authority-336791)
![AWS](https://img.shields.io/badge/AWS-deployment%20foundation-232F3E)

[![Milestone Tags](https://img.shields.io/badge/Browse-Milestone%20Tags-181717?logo=github)](https://github.com/Asleki/NexiLabs/tags)
[![Architecture](https://img.shields.io/badge/Open-Architecture-0D1B2A)](docs/architecture/)
[![PWA Source](https://img.shields.io/badge/Open-NexiLabs%20PWA-0D1B2A)](frontend/)
[![NoveGeo](https://img.shields.io/badge/Open-NoveGeo-0D1B2A)](data/novegeo/)

</div>

> [!IMPORTANT]
> NexiLabs is under active engineering. The repository contains qualified Production authorities and substantial PWA, PostgreSQL, NoveGeo/NNGLA and infrastructure foundations, but the public `nexaecosystem.com` deployment is **not yet advertised as live** from this repository.

## What NexiLabs is

NexiLabs is the governed platform in this repository for building and operating Nexa ecosystem simulation, registry, identity/authentication, geospatial and shared infrastructure capabilities.

The codebase began as the **Nexa Provider Platform (NPP)** engineering foundation. That historical identity remains important provenance, but the current product and repository identity is **NexiLabs**.

NexiLabs currently brings together:

- an installable/offline-capable Progressive Web App;
- explicit **Simulation** and **Production** product runtimes;
- NexaDevs Developer authentication and enrollment foundations;
- layered NexiLabs Admin authority inside authenticated Production Developer sessions;
- PostgreSQL-backed account, credential, audit and registry authorities;
- NoveGeo and NNGLA geography, naming and spatial-publication capabilities;
- a shared FastAPI infrastructure read API;
- AWS deployment and HTTPS delivery foundations;
- governed migrations, verification, audit/event infrastructure and milestone provenance.

NexiLabs is **not** a browser-to-database application. Browser clients consume governed application/API boundaries; PostgreSQL credentials and privileged authorities remain server-side.

## Current capability status

| Capability | Repository state |
|---|---|
| NexiLabs PWA shell | **Implemented** — installable/offline application shell with governed runtime navigation |
| Simulation runtime | **Implemented** — explicit simulation-facing experience and NoveGeo exploration |
| Production runtime | **Implemented** — governed Production entry and authenticated workspace resolution |
| NoveGeo / NNGLA | **Implemented / qualified foundation** — geography, map presentation, spatial authority, naming and PostgreSQL read paths |
| Production NexaDevs authentication | **Qualified** — primary credentials followed by Developer Enigma |
| Layered Admin authentication | **Qualified** — server-side eligibility followed by separate Admin credentials and fresh Admin Enigma |
| Developer enrollment UI | **Frontend foundation** — request, Setup verification, registration, OTP and credential-provisioning presentations exist |
| Developer enrollment persistence | **Foundation implemented** — governed request, Setup, account, email, credential and Enigma persistence exists |
| Admin review persistence | **Foundation implemented** — Admin operator and Developer decision authority exists |
| Full Admin review workspace | **Planned** — operational review UI/workflow is not yet presented as complete |
| Email OTP persistence | **Foundation implemented** — challenge authority exists; real external mail delivery is a later operational step |
| Credential bundle/delivery persistence | **Foundation implemented** — bundle, secret and delivery authorities exist; public secure delivery is not yet live |
| Shared Infrastructure API | **Implemented foundation** — FastAPI read boundary for health, geography, NNGLA/map and publication surfaces |
| Public NexiLabs domain | **Planned** — no live-project button is published here until DNS/TLS/public qualification is complete |

## Runtime model

NexiLabs distinguishes **product runtime semantics** from engineering/deployment environments.

### Product runtimes

```text
NexiLabs
├── Simulation
│   └── public/simulation-facing governed experiences
└── Production
    ├── authenticated Guest context
    └── NexaDevs Developer
        └── conditional NexiLabs Admin elevation
```

Admin is **not a third runtime**. Admin authority is an elevation inside an already authenticated Production NexaDevs Developer session after the server proves an active Admin binding.

Engineering environments such as development, testing or staging may still exist for deployment and verification purposes; they do not create additional user-facing product runtimes.

## Architecture at a glance

```text
                         NexiLabs PWA
                              │
                 ┌────────────┴────────────┐
                 │                         │
             Simulation                Production
                 │                         │
              NoveGeo            Guest / NexaDevs Developer
                 │                         │
                 │                 Developer authentication
                 │                         │
                 │                 conditional Admin elevation
                 │                         │
                 └────────────┬────────────┘
                              │
                 governed server-side APIs/services
                       │                 │
            Shared Infrastructure   NexiLabs Auth Authority
                    API                   │
                       └──────────┬────────┘
                                  │
                          PostgreSQL / RDS
```

The shared Infrastructure API and the NexiLabs authentication authority are separate boundaries. The existing shared API should not be interpreted as a public credential/authentication endpoint merely because both ultimately consume governed PostgreSQL state.

## NexaDevs

NexaDevs is the Developer-facing NexiLabs surface.

The current repository already contains the presentation and persistence foundations for the intended governed enrollment lifecycle:

```text
Developer access request
        ↓
NexiLabs Admin review
        ↓
approved Developer Setup
        ↓
Developer Setup verification
        ↓
Developer account + Developer identity
        ↓
username/password establishment
        ↓
approved-email verification
        ↓
Developer-specific Enigma provisioning
        ↓
protected credential-bundle delivery
        ↓
Production sign-in
        ↓
Developer Enigma
        ↓
Production Developer Workspace
```

Not every step above is operational end-to-end yet. The repository deliberately separates **persistence foundations**, **frontend foundations** and **live-qualified runtime authorities** rather than presenting deferred work as complete.

## Layered Admin authority

The current Admin model preserves the Production runtime boundary:

```text
Production NexaDevs Developer
        ↓
Developer password
        ↓
Developer Enigma
        ↓
authenticated Developer session
        ↓
server-side Admin eligibility
        ↓
separate Admin credentials
        ↓
fresh Admin Enigma
        ↓
temporary Admin elevation
```

The public browser does not receive a top-level standalone Admin runtime. Admin eligibility is evaluated only after successful Developer authentication.

## NoveGeo / NNGLA

NoveGeo is a major current NexiLabs domain, not the identity of the entire platform.

The repository includes governed material for, among other things:

- sovereign and administrative geography;
- regions, cities, municipalities, city districts and towns;
- place identity and geographic naming;
- road and addressing foundations;
- spatial qualification and publication;
- PostgreSQL-backed national read models;
- map presentation, cartography, semantic zoom and environment layers;
- NNGLA governance and verification.

Qualified data and evidence live under `data/novegeo/`, while runtime/domain authority is distributed across `registries/`, `infrastructure/`, `database/`, `frontend/` and `verification/`.

## Security boundaries

NexiLabs is engineered around explicit authority separation.

- Browser clients never receive PostgreSQL credentials.
- Public/non-loopback API endpoints are expected to use HTTPS.
- Production wildcard CORS is rejected by the shared infrastructure configuration.
- RDS/PostgreSQL authority remains server-side.
- Private local authentication material under `development/auth/private/` is intentionally excluded from Git.
- The First-Admin bootstrap path is not intended to become a permanent public bootstrap endpoint.
- Admin authority is conditional on an authenticated Developer principal plus a server-side Admin binding.
- Credential bundles, delivery tokens, OTP values, passwords and Enigma secrets are not public repository artifacts.
- Historical migrations, milestone tags and authority identifiers are provenance and are not casually renamed when product branding evolves.

## Public namespace direction

The repository is preparing for a public Nexa ecosystem namespace, but it does not advertise those hosts as live yet.

Planned topology:

```text
nexaecosystem.com
├── nexilabs.nexaecosystem.com
│   └── NexiLabs PWA and governed application surface
├── secure.nexilabs.nexaecosystem.com
│   └── protected NexiLabs credential delivery boundary
└── novegeo.nexaecosystem.com
    └── reserved future NoveGeo public surface
```

DNS, TLS, public authentication transport and secure-delivery qualification belong to the separate **Public NexiLabs Trust Boundary** milestone.

## Repository structure

| Path | Purpose |
|---|---|
| `backend/` | NexiLabs authentication and backend authorities |
| `frontend/` | NexiLabs PWA, account/auth experiences, workspaces and NoveGeo presentation |
| `infrastructure/` | shared API, database runtime, geography services and AWS deployment foundation |
| `registries/` | governed registry, naming, NNGLA and relationship authorities |
| `database/` | schemas, migrations, seeds, migration control and qualification |
| `data/novegeo/` | NoveGeo source, qualified spatial data, evidence and publication material |
| `shared/` | shared audit, event, configuration, repository and storage foundations |
| `verification/` | milestone/runtime qualification programs |
| `tests/` | Python unit, contract, integration, registry and verification coverage |
| `docs/architecture/` | historical and current architecture records |
| `.github/workflows/` | repository automation and deployment workflows |

## Verification and milestone governance

NexiLabs uses milestone-oriented engineering and explicit qualification.

A typical governed change is expected to move through:

```text
source lock
  → repository/architecture inspection
  → implementation
  → isolated tests
  → package/subsystem regression
  → full repository regression
  → runtime/database qualification where applicable
  → final diff review
  → commit
  → milestone tag
  → push
```

Historical tests are preserved when successors add coverage. Applied migrations, milestone identifiers and tags are treated as provenance rather than rewritten to match later branding.

The latest qualified product milestone before this repository-presentation alignment is:

**P006.UI.10.3 — First Admin Production Authentication & Runtime Qualification**

[View the qualified commit](https://github.com/Asleki/NexiLabs/commit/d63691240960fff4f0ac8cde8ee224a52aca5425) · [Browse milestone tags](https://github.com/Asleki/NexiLabs/tags)

## Historical NPP provenance

The repository began as the **Nexa Provider Platform (NPP)** engineering foundation. You will therefore still find legitimate historical identifiers such as:

```text
NPP-001 ... NPP-015
npp_* database/runtime identifiers
P006... milestone identifiers
historical roadmap and architecture references
```

Those names are retained intentionally where they represent immutable engineering provenance, applied database authority, compatibility contracts or historical milestone state.

A repository rename to **NexiLabs** does **not** imply rewriting historical migrations, tags, source locks or architecture IDs.

## Public project status

NexiLabs is currently in the transition from locally qualified/controlled runtime operation to a governed public trust boundary.

That means this repository intentionally does **not** yet publish:

- an “Open NexiLabs” live-site button;
- a “Production Live” badge;
- a public deployment-health badge;
- a CI-passing badge unsupported by current GitHub status checks.

Those will be added only when the corresponding public systems exist and are independently qualified.

---

<div align="center">

**NexiLabs** — governed infrastructure for the evolving Nexa ecosystem.

[Repository](https://github.com/Asleki/NexiLabs) · [Tags](https://github.com/Asleki/NexiLabs/tags) · [Architecture](docs/architecture/) · [PWA](frontend/) · [NoveGeo](data/novegeo/)

</div>
