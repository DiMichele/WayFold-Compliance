# Architecture — WayFold Compliance (Phase 0)

## Selected core

**CISO Assistant Community** — Django/DRF backend + SvelteKit frontend + PostgreSQL (compose ufficiale).

Dominio previsto: `compliance.wayfold.xyz` (ingress da definire in Phase 1+; non deployato in Phase 0).

## Strategy B

```text
compliance.wayfold.xyz
        │
        ▼
┌───────────────────────┐
│ Compliance UI         │  CISO frontend (+ future Wayfold consultant views)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ GRC CORE              │  CISO Assistant
│ Folders/Perimeters    │
│ Frameworks/Libraries  │
│ RequirementNodes      │
│ ReferenceControls     │
│ AppliedControls       │
│ Assessments           │
│ Evidence / Tasks      │
│ IAM / RBAC            │
└───────────┬───────────┘
            │ REST/OpenAPI
            ▼
┌───────────────────────┐
│ WAYFOLD ENGINE        │  Custom (future phases)
│ Regulatory sources    │
│ Snapshots / Diff      │
│ Client impact         │
│ Mapping intelligence  │
│ Optional OpenCRE      │
│ Control ROI           │
└───────────────────────┘
```

## Database boundaries

- **Core DB:** PostgreSQL gestito da CISO (unico source of truth GRC operativo).
- **Wayfold Engine DB:** database separato per regulatory snapshots/diff/impact (Phase 4+); niente silent mutation delle library pubblicate nel core.

## API boundaries

- Wayfold Engine **legge/scrive** il core solo tramite API documentata (DRF).
- Nessun accesso diretto al DB core dal regulatory engine in produzione.
- OpenCRE (se usato) è servizio read-oriented per suggerimenti mapping; approvazione umana obbligatoria.

## Storage

- Evidence files: storage CISO (EvidenceRevision attachments).
- Regulatory raw snapshots: object storage / filesystem del Wayfold Engine (futuro).

## Deployment (target)

- Stack CISO via Docker Compose dietro reverse proxy verso `compliance.wayfold.xyz`.
- Wayfold Engine come servizio aggiuntivo (compose profile o host separato) quando Phase 4 inizia.
- Pattern operativo simile a Bills (`apps/wayfold-bills/deploy/`) ma **separato** dal deploy viaggi.

## Semantic map (do not rename in DB)

| WayFold product language | CISO entity |
|---|---|
| Client | Folder (DOMAIN) and/or Perimeter |
| Compliance Program | Campaign + ComplianceAssessment set |
| Canonical Control | ReferenceControl |
| Control Implementation | AppliedControl |
| Requirement | RequirementNode |
| Framework Version | LoadedLibrary.version (+ Framework.library pin) |

## Phase 0 constraint

Questa architettura è documentata **prima** del run locale del core; la demo Michele deve validare il fit, non solo il bootstrap Docker.
