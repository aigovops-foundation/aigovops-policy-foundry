# Policy: AI-assisted changes to plant software (REQ-1042) -- EXAMPLE

Owner: Director, Manufacturing Systems Engineering. Review date: 12 months from publication.

## Applies to
Any code, configuration, or script change to plant-supporting software (MES, quality, historian
integrations, maintenance systems) where an AI system authored or materially modified the change.

## Requirements
1. AI-assisted changes are never deployed directly into an OT zone (Levels 0-3). They go through
   the plant Management of Change (MOC) process with a ticket number.
2. At least one human who is not the author reviews the change. Agent reviews do not count.
3. Safety-relevant changes need two human reviewers, one holding the functional-safety role.
4. Every change traces to at least one approved requirement ID.
5. Tests pass and a software bill of materials (SBOM) is attached.

## Exceptions
Requested through the AI Governance Board; time-limited; recorded as a signed exception receipt.
