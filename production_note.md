# Production note: NovaMart internal assistant

This prototype proves the interaction model: grounded answers with citations, live order
lookups, honest refusals. Here is how I would take it to production for NovaMart on
Google's enterprise stack.

## Gemini Enterprise or custom build: both, split by workload

I would not frame this as either-or. The knowledge-assistant surface (employees asking
policy questions) is exactly what Gemini Enterprise (the platform formerly Agentspace)
ships out of the box: a governed chat surface, connectors into enterprise content, and
admin controls. Rebuilding that is undifferentiated work. I would deploy Gemini
Enterprise for the general surface and keep the custom agent for what the platform does
not know: NovaMart's order system, the delayed-order goodwill rules, and any workflow
that calls internal APIs. The custom agent stays on the Agent Development Kit, deployed
on Agent Runtime (formerly Agent Engine) on the Gemini Enterprise Agent Platform (the
evolution of Vertex AI), and registers into Gemini Enterprise so employees see one
assistant, not two. Tool-heavy workflows remain versioned code we test and evaluate;
knowledge search remains managed infrastructure.

## Connecting real data

The invented corpus becomes managed retrieval: NovaMart's policy repository (SharePoint,
Drive, or their CMS) connects through first-party connectors with ACL-aware indexing, so
an employee can never retrieve a document their account cannot open. The order lookup
tool points at the real OMS API behind a service account with read-only scope, or an MCP
server if NovaMart standardizes tool access across agents. BigQuery stays the analytics
backbone: every turn logs question, retrieved sources, tools called, verdict, latency,
and cost there.

## Security and governance

Identity through Google Workspace SSO, so access follows joiners and leavers
automatically. VPC Service Controls around the project, CMEK on stored data, DLP scans
on logs. The prototype's free-tier key disappears: enterprise endpoints do not train on
customer data, keys move to Secret Manager with rotation. Audit trail: every answer is
reconstructable (model version, prompt, retrieved chunks, tool responses) from the
BigQuery log. The refusal contract is a governance feature: the assistant never invents
policy, and every refusal is logged with the question that caused it.

## Quality over time

The eval suite in this repo is the seed of the regression gate: it runs in CI against
every prompt, corpus, or model change, and a release that drops below the current pass
rate does not ship. In production, sample live traffic weekly into the judge pipeline,
track groundedness and refusal correctness by bucket, and alert on drift. Employee
feedback (one tap: helpful or wrong) joins the same BigQuery table. The knowledge-gap
log closes the loop: refused questions cluster into missing-documentation reports, an
LLM drafts candidate policy pages from them, and the operations team reviews and
publishes; only human-approved pages enter the retrieval corpus. Cost and latency sit on
a dashboard from day one, because at 200 stores the interesting failure is not one bad
answer, it is a slow drift nobody is watching.
