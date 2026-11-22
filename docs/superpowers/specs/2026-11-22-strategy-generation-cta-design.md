# Strategy Generation CTA Design

## Intent

Close the missing transition between a completed reference analysis and the three strategy proposals. A user should always see the next valid action instead of reaching an empty strategy page with only instructional text.

## Chosen Approach

Use the existing synchronous strategy generation API when the project already has the minimum eligible fact set and an analyzed reference. Add the same recovery action to both the inspiration page and an empty strategy page. When facts are not ready, preserve the Agent gate and show a direct action to the Agent workspace rather than issuing a model request that must fail.

Alternatives rejected:

- Requiring users to discover the Agent workspace themselves leaves the current navigation gap unchanged.
- Automatically generating strategies immediately after reference analysis consumes model quota without an explicit user action.

## Behavior

- A completed reference analysis exposes a visible next-step panel.
- If one eligible activity fact and one eligible detail fact exist, the primary button says `生成 3 个创作策略`.
- Clicking the button posts to `/api/projects/{project_id}/strategies/generate`; success navigates to `/project/{project_id}/strategy`.
- While generating, the button is disabled and the taskbar says `正在生成 3 个创作策略…`.
- API errors remain on the current page, appear in the taskbar, and re-enable the button.
- If the minimum fact set is missing, the panel explains the prerequisite and links to `/project/{project_id}/agent` with `先让 Agent 整理活动事实`.
- An empty strategy page renders the same panel, so direct navigation is recoverable.
- Existing facts, reference and strategy service gates remain authoritative; the UI does not duplicate weaker business rules.

## Constraints

- Reuse FastAPI, Jinja2 and native JavaScript; add no dependency.
- Do not generate strategies automatically.
- Do not bypass fact eligibility or reference-method isolation.
- Keep all runtime files under the existing project runtime root.

## Verification

- Template behavior tests cover eligible and missing-fact states on both pages.
- A browser regression covers clicking the enabled CTA, receiving three strategies and landing on the proposal page when the local E2E server is available.
- Existing strategy service and provider tests remain green.
