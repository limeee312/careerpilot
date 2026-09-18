# CareerPilot Frontend

The CareerPilot web application uses Next.js App Router, TypeScript, Tailwind CSS, and ESLint.

## Development

```bash
npm install
npm run dev
```

Open <http://localhost:3000>.

The protected application includes the resume master editor, manual job matching,
evidence-rich job details, and the Resume Tailor comparison workspace. Resume
Tailor drafts remain browser-only until the user explicitly saves them. The save
action revalidates the draft through the backend, and saved job-targeted versions
appear in the Resume Library without replacing the Resume Master.

## Quality checks

```bash
npm run lint
npm run build
```
