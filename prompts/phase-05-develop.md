# Phase 5 — AI Assistance — Development

Obiettivo: aggiungere AI come copilota controllato, provider-agnostic e sempre soggetto a human review.

## AIProvider boundary

Creare/riusare un service layer unico per i provider. Nessuna chiamata LLM sparsa in componenti UI/controller.

Supportare configurazione provider/model senza hardcoding del dominio.

## Use case MVP

1. Mapping suggestion
   - input: requirement + controls/mappings esistenti;
   - output strutturato: suggestedControl, relation, confidence, rationale, uncoveredDelta.

2. Regulatory change analysis
   - input: old/new/diff + requirements rilevanti;
   - output: relevance, summary, impactedRequirements, suggestedActions, confidence.

3. Gap explanation
   - input: requirement, mapping, client implementation, evidence metadata consentita;
   - output: coverage explanation, missing elements, suggested remediation.

## Human review

Ogni proposta AI deve essere distinguibile come `AI_SUGGESTED` e non può automaticamente:

- approvare mapping;
- pubblicare framework/version;
- cambiare baseline;
- cambiare status cliente;
- dichiarare compliance.

## Tenant control

Rispettare `aiProcessingEnabled` (default false o policy equivalente già decisa). Nessun contenuto cliente a provider esterno se disabilitato.

## Structured outputs

Validare output con schema. Fallimenti/parsing invalidi devono essere gestiti senza mutare dominio. Registrare metadata essenziali della suggestion, non segreti.

## Prompt/data minimization

Inviare solo il contesto necessario al use case. Non inviare intere evidence/file se non esplicitamente richiesto e consentito.

## UI

Mostrare chiaramente:

- AI generated;
- confidence come segnale, non verità;
- approve/edit/reject dove appropriato;
- source context utilizzato;
- nessuna auto-apply.

## Test

Usare fake/mock provider deterministico per test automatici. Testare disabled tenant, invalid structured output, provider failure, approve/reject flow e authorization.

## Fuori scope

Niente autonomous compliance decisions; niente Prowler (Phase 6).

## Machine result

`AWAITING_VERIFICATION` o `BLOCKED`.
