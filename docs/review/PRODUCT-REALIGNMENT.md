# WAYFOLD COMPLIANCE — PRODUCT REALIGNMENT

Date: 2026-08-09  
Repository: https://github.com/DiMichele/WayFold-Compliance  
Live: https://compliance.wayfold.xyz/  
Deployed commit: `dab74ce204fcbfffa6e58a6d4942f1f27c0e1feb`  
Screenshots: `docs/review/realign/` · `docs/review/final/`

## STATUS

**COMPLETE** (core authoring workflow CREATE → MAP → PUBLISH → ASSIGN → ASSESS from UI)

## NAVIGATION

Area di lavoro: Portfolio · Clienti · Attività  
Programma corrente: (solo con `program_id`) Panoramica · Controlli unificati · Gap · Evidenze · Report  
Knowledge Base: Framework e normative · Catalogo controlli · Mappature · Intelligence normativa  
Amministrazione: Utenti e ruoli · Registro attività · Impostazioni  

Topbar: breadcrumb + **+ Nuovo** (Quick Create)

## FEATURES HIDDEN

Responsabili · Scadenze · Fonti · Suggerimenti FW · Suggerimenti AI · Connettori · Evidenze auto · selettore EN  
(route backend preservate, non in nav primaria)

## KNOWLEDGE BASE AUTHORING

| Capability | Result |
|---|---|
| Create framework | PASS |
| Create version | PASS |
| Create requirement | PASS |
| CSV import | PASS |
| Control catalog | PASS |
| Create control | PASS |
| Create mapping | PASS |
| FULL | PASS |
| PARTIAL + delta | PASS |
| SUPPORTING | PASS |
| Publish | PASS |
| Published immutability | PASS |

## CLIENT WORKFLOW

| Capability | Result |
|---|---|
| Create client | PASS |
| Create program | PASS |
| Select FrameworkVersion | PASS (solo PUBLISHED) |
| Generate unified checklist | PASS (dedup) |
| Edit implementation | PASS |
| Evidence upload | PASS (form metadata; binary path esistente) |
| Task/remediation | PASS |

## KNOWN BUGS

| Item | Result |
|---|---|
| TASK flag Completed+Open | PASS (fixed) |
| Evidence flag existing+Missing | PASS (fixed) |
| Version consistency NIS2 2026.2 | PASS (same framework_id) |
| Raw enums | PASS (IT labels) |
| Raw timestamps | PASS (`format_display_datetime`) |
| Italian UI | PASS |

## SECURITY REGRESSION

| Item | Result |
|---|---|
| Authentication | PASS |
| RBAC | PASS |
| Tenant isolation | PASS |
| Evidence authorization | PASS |
| Framework immutability | PASS |

## TESTS

- `test_kb_authoring` OK  
- `test_production_hardening` OK (12)  
- `test_ui_design_system` OK (5)  
- `test_review_demo` OK (11)  
- `test_unified_compliance` OK (13)  
- `test_consultant_ux` OK (10)

## SCREENSHOT PACK

Live verified 1920×1080 during deploy review:

- portfolio  
- framework-list (`Framework e normative` + CTA)  
- framework-create  
- control-catalog  
- nis2-versions (2026.1 + 2026.2)  
- clients (+ Nuovo cliente/programma)

Path sessione: `docs/review/realign/` (rigenerare se necessario da live)

## READY FOR EXTERNAL REVIEW

**YES**

## READY FOR REAL CLIENT DATA

**NO**

Reason: temporary admin credential + MFA pending
