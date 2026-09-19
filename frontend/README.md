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
`/applications/[applicationId]` supports flexible timeline events and lifecycle
status updates. `/dashboard` aggregates total, active, terminated, and Offer counts
and links the five most recent applications back to their timelines. Funnel and
reminder modules remain outside MVP 0.1.

## Quality checks

```bash
npm run lint
npm test
npm run build
```
