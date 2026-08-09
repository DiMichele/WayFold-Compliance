# AI Assistance — WayFold Phase 5

## Goal

AI **suggests**; humans **approve**. The product remains useful with AI disabled (default).

Never auto:

- publish framework
- approve mapping
- modify client baseline
- mark client compliant

## Architecture

```text
UI / API (:8092)
      │
      ▼
AIAssistanceService   ← only entrypoint
      │
      ├── TenantAISettings (ai_processing_enabled default false)
      ├── AIProvider (HeuristicAIProvider local; swappable LLM later)
      └── AIStore (engine/data/ai/)
```

No LLM SDK calls from controllers or HTML templates.

## Capabilities

| Kind | Endpoint | Output |
|---|---|---|
| Mapping suggestion | `/api/ai/mapping-suggest` | control + relation + confidence + delta |
| Regulatory diff summary | `/api/ai/regulatory-summary` | relevance + impacted reqs + actions |
| Impact suggestion | `/api/ai/impact-suggest` | narrative + recommended reviews |
| Gap explanation | `/api/ai/gap-explain` | coverage + missing + remediation |

All persisted as `AISuggestion` with `review_status=AI_SUGGESTED`.

## Human review

```text
/api/ai/review?suggestion_id=…&status=APPROVED|REJECTED
```

`materialize_approved_mapping()` builds a `MappingRecord` only after APPROVED — does **not** write CISO DB or mark compliance.

## Tenant setting

```text
ai_processing_enabled = false   # default
/api/ai/settings?tenant_id=…&enabled=1|0
```

Disabled → `403 ai_processing_disabled` on suggest endpoints.

## Provider note

`HeuristicAIProvider` is deterministic (token overlap / rule summaries) so overnight runs need **no** external AI credentials. Replace with a real LLM provider implementing `AIProvider` when keys are available — still through the service layer only.
