# CareerPilot Frontend

The CareerPilot web application uses Next.js App Router, TypeScript, Tailwind CSS, and ESLint.

## Development

```bash
npm install
npm run dev
```

Open <http://localhost:3000>.

The protected application includes the resume master editor, manual job matching,
evidence-rich job details, the Resume Tailor comparison workspace, and application
tracking. Resume Tailor drafts remain browser-only until the user explicitly saves
them. The save action revalidates the draft through the backend, and saved
job-targeted versions appear in the Resume Library without replacing the Resume
Master. `/applications` provides status filters and responsive list views, while
`/applications/new?jobId=...` creates a record from a matched job, optionally
linking a saved job-specific resume. `/applications/[applicationId]` supports flexible timeline events and lifecycle
status updates. `/dashboard` aggregates total, active, terminated, and Offer counts
and links the five most recent applications back to their timelines. Funnel and
reminder modules remain outside MVP 0.1.

## Quality checks

```bash
npm run lint
npm test
npm run build
```

## Browser journey

Install Chromium once, then build and run the Playwright check:

```bash
npx playwright install chromium
NEXT_PUBLIC_API_BASE_URL=http://localhost:8765/api/v1 npm run build
npm run test:e2e
```

The browser test starts its own local API fixture and production Next.js server
on ports 8765 and 3100. It covers registration, login, resume creation, job
analysis, tailored resume saving, application creation, timeline, and dashboard.
The fixture makes frontend navigation deterministic; it does not test the real
backend, database, or AI model. Backend integration is checked in the backend
test suite. CI installs Chromium and runs this browser check after the build.
