# WayFold Compliance

GRC multi-framework per consulenza cybersecurity.

- **Produzione:** https://compliance.wayfold.xyz
- **Repo:** https://github.com/DiMichele/WayFold-Compliance
- **Brand prodotto:** solo *WayFold Compliance* (il motore GRC sottostante è un dettaglio di implementazione e non compare in UI)

Questo README spiega come **clonare il repo e far partire l'engine in locale** in pochi minuti. Per deploy, sicurezza e decisioni di prodotto vedi i documenti in `docs/`.

---

## Requisiti

| Tool | Versione |
|------|----------|
| Git | qualsiasi recente |
| Python | **3.11+** (testato con 3.12) |

Opzionale: Docker, solo se vuoi anche lo stack GRC core di produzione (non serve per l'UI consulente locale).

---

## Avvio rapido (locale)

### 1. Clona e entra nella cartella

```bash
git clone https://github.com/DiMichele/WayFold-Compliance.git
cd WayFold-Compliance
```

### 2. Ambiente virtuale e dipendenze

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r engine/requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r engine/requirements.txt
```

### 3. Configurazione locale

Copia il template e (se vuoi) modifica i valori:

```bash
cp .env.example .env
```

Su Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Per lo sviluppo locale il mode consigliato è **open access + demo seed** (già impostato in `.env.example`):

- niente login obbligatorio
- dati demo caricati dai fixture in `engine/fixtures/`
- accesso UI con `?superuser=1` oppure `?actor_tenants=<tenant-id>`

Carica le variabili prima di avviare il server.

**Windows (PowerShell):**

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $k, $v = $_ -split '=', 2
  Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim()
}
```

**macOS / Linux:**

```bash
set -a
source .env
set +a
```

### 4. Avvia l'engine

```bash
python -m engine.api
```

Dovresti vedere:

```text
WayFold Compliance listening on http://127.0.0.1:8092
```

Apri nel browser:

```text
http://127.0.0.1:8092/portfolio?superuser=1
```

Health check:

```text
http://127.0.0.1:8092/healthz
```

Per fermare il server: `Ctrl+C`.

---

## Cosa ottieni in locale

L'engine (`python -m engine.api`) è la **superficie prodotto** WayFold Compliance: portfolio, gap, evidence, task, report, framework KB, ecc.

Con i default di `.env.example`:

- dati demo da `engine/fixtures/` (`WAYFOLD_SEED_DEMO=1`)
- store runtime in `engine/data/` (gitignored, creato al primo avvio)
- porta **8092** su `127.0.0.1`

Lo stack Docker di produzione (backend GRC + frontend + nginx TLS) **non è necessario** per sviluppare o provare l'UI consulente in locale.

---

## Route utili

| Vista | URL locale |
|-------|------------|
| Portfolio | `/portfolio?superuser=1` |
| Client | `/client?program_id=…&superuser=1` |
| Gap | `/gaps?superuser=1` |
| Checklist | `/checklist?superuser=1` |
| Evidence | `/evidence?superuser=1` |
| Task | `/tasks?superuser=1` |
| Report | `/report?superuser=1` |
| Health | `/healthz` |

Auth locale (dev): `?superuser=1` **oppure** `?actor_tenants=<tenant-id>` quando `WAYFOLD_ALLOW_QS_AUTH=1` / seed demo attivi.

---

## Test automatici

Dalla root del repo, con venv attivo:

```bash
python -m engine.tests.test_unified_compliance
python -m engine.tests.test_consultant_ux
python -m engine.tests.test_kb_authoring
python -m engine.tests.test_security_realignment
```

Altre suite: vedi `docs/review/REVIEW-TEST-ACTIONS.md`.

CLI (senza HTTP):

```bash
python -m engine --superuser --format text
```

---

## Login locale (opzionale)

Se preferisci la pagina `/login` invece di open access:

1. In `.env` imposta ad esempio:

```env
WAYFOLD_OPEN_ACCESS=0
WAYFOLD_ALLOW_QS_AUTH=0
WAYFOLD_MFA_ENFORCE=0
WAYFOLD_AUTH_USER=admin
WAYFOLD_AUTH_PASSWORD=cambia-questa-password
WAYFOLD_SESSION_SECRET=una-stringa-lunga-casuale-solo-locale
```

2. Ricarica le env e riavvia `python -m engine.api`
3. Apri `http://127.0.0.1:8092/login`

**Non usare queste credenziali in produzione.** In produzione MFA, seed demo e open access sono bloccati (`WAYFOLD_OPEN_ACCESS=0`, `WAYFOLD_SEED_DEMO=0`, `WAYFOLD_MFA_ENFORCE=1`).

---

## Layout del progetto

```text
.
  README.md          <- questo file
  .env.example       <- template env per locale
  engine/            <- prodotto (UI HTTP + servizi + test + fixture)
  docs/              <- architettura, progress, security, UX
  deploy/            <- produzione su compliance.wayfold.xyz
  automation/        <- orchestratore fasi (overnight)
  prompts/           <- prompt Cursor per le fasi
  scripts/           <- utility di supporto
```

Documentazione di approfondimento:

| Doc | Contenuto |
|-----|-----------|
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Stato fasi |
| [`docs/ui.md`](docs/ui.md) | UI |
| [`docs/unified-compliance.md`](docs/unified-compliance.md) | Motore unified compliance |
| [`docs/consultant-ux.md`](docs/consultant-ux.md) | Workflow consulente |
| [`docs/security.md`](docs/security.md) | Auth, CSRF, RBAC |
| [`docs/deployment.md`](docs/deployment.md) | Deploy produzione |

---

## Problemi comuni

| Sintomo | Cosa controllare |
|---------|------------------|
| `ModuleNotFoundError: engine` | Sei nella cartella sbagliata: resta nella root del clone (`WayFold-Compliance`) |
| Porta 8092 occupata | Chiudi l'altra istanza, oppure `python -m engine.api --port 8093` |
| Redirect a `/login` | Hai `WAYFOLD_OPEN_ACCESS=0`: usa login oppure rimetti `=1` per il mode open |
| Portfolio vuoto | Verifica `WAYFOLD_SEED_DEMO=1` (default locale) e che i fixture in `engine/fixtures/` ci siano |
| MFA / enrollment | In locale tieni `WAYFOLD_MFA_ENFORCE=0` |
| Dipendenze | `pip install -r engine/requirements.txt` nel venv attivo |

---

## Deploy produzione

Solo se stai aggiornando il server (non serve per lavorare in locale):

```powershell
powershell -ExecutionPolicy Bypass -File deploy/deploy-compliance.ps1
```

Dettagli: [`docs/deployment.md`](docs/deployment.md).
