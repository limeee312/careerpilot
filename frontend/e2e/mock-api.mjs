import { createServer } from "node:http";

// A stateful, deliberately small API double for the browser journey. Backend
// contracts and persistence are tested separately by backend tests.
const now = "2026-09-21T08:00:00Z";
const ids = {
  resume: "11111111-1111-4111-8111-111111111111",
  batch: "22222222-2222-4222-8222-222222222222",
  job: "33333333-3333-4333-8333-333333333333",
  result: "44444444-4444-4444-8444-444444444444",
  version: "55555555-5555-4555-8555-555555555555",
  application: "66666666-6666-4666-8666-666666666666",
};
const state = { user: null, resume: null, batch: null, version: null, application: null };
const origin = "http://localhost:3100";

function respond(response, status, data, headers = {}) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    Vary: "Origin",
    ...headers,
  });
  response.end(JSON.stringify(data));
}

async function body(request) {
  let value = "";
  for await (const chunk of request) {
    value += chunk;
    if (value.length > 100_000) throw new Error("request body too large");
  }
  return value ? JSON.parse(value) : {};
}

function jobDetail() {
  const job = state.batch.jobs[0];
  return {
    job_id: ids.job,
    batch_id: ids.batch,
    result_id: ids.result,
    company_name: job.company_name,
    title: job.title,
    location: job.location,
    department: job.department,
    source_url: job.source_url,
    role_summary: "负责产品运营与用户增长。",
    eligibility_status: "PASS",
    total_score: "82.00",
    display_score: 82,
    confidence_score: "76.00",
    confidence_level: "HIGH",
    recommendation_level: "STRONG",
    recommendation: "建议投递",
    strengths: ["具有可核实的运营经历"],
    gaps: [],
    dimension_scores: [],
    hard_gates: [],
    requirement_assessments: [],
    analyzed_at: now,
  };
}

const server = createServer(async (request, response) => {
  try {
    const path = new URL(request.url, `http://${request.headers.host}`).pathname;
    const method = request.method;
    if (method === "OPTIONS") return respond(response, 204, null);
    if (path === "/health") return respond(response, 200, { ok: true });
    if (!path.startsWith("/api/v1/")) return respond(response, 404, { error: { message: "Unknown path" } });
    const endpoint = path.slice("/api/v1".length);

    if (endpoint === "/auth/register" && method === "POST") {
      const input = await body(request);
      state.user = { id: "77777777-7777-4777-8777-777777777777", email: input.email, name: null };
      return respond(response, 201, { data: state.user });
    }
    if (endpoint === "/auth/login" && method === "POST") {
      const input = await body(request);
      if (input.email !== state.user?.email) return respond(response, 401, { error: { message: "Invalid login" } });
      return respond(response, 200, { data: state.user }, {
        "Set-Cookie": "careerpilot_session=e2e-session; HttpOnly; Path=/; SameSite=Lax",
      });
    }
    if (!request.headers.cookie?.includes("careerpilot_session=e2e-session")) {
      return respond(response, 401, { error: { message: "Please log in" } });
    }
    if (endpoint === "/auth/me" && method === "GET") return respond(response, 200, { data: state.user });
    if (endpoint === "/resume/master" && method === "GET") return respond(response, 200, { data: state.resume });
    if (endpoint === "/resume/master" && method === "PUT") {
      const input = await body(request);
      state.resume = {
        ...input,
        id: ids.resume,
        education: input.education.map((item, index) => ({ ...item, id: item.id ?? `education-${index}` })),
        experiences: input.experiences.map((item, index) => ({ ...item, id: item.id ?? `experience-${index}` })),
        projects: input.projects.map((item, index) => ({ ...item, id: item.id ?? `project-${index}` })),
        skills: input.skills.map((item, index) => ({ ...item, id: item.id ?? `skill-${index}` })),
        created_at: now,
        updated_at: now,
      };
      return respond(response, 200, { data: state.resume });
    }
    if (endpoint === "/job-match/batches" && method === "POST") {
      const input = await body(request);
      state.batch = {
        id: ids.batch,
        name: input.name || null,
        status: "DRAFT",
        total_jobs: input.jobs.length,
        successful_jobs: 0,
        failed_jobs: 0,
        jobs: input.jobs.map((job) => ({
          job_id: ids.job,
          company_name: job.company_name,
          title: job.title,
          location: job.location ?? null,
          department: job.department ?? null,
          source_url: job.source_url ?? null,
          analysis_status: "PENDING",
          error_code: null,
          result: null,
        })),
        created_at: now,
        updated_at: now,
      };
      return respond(response, 201, { data: state.batch });
    }
    if (endpoint === `/job-match/${ids.batch}` && method === "GET" && state.batch) {
      return respond(response, 200, { data: state.batch });
    }
    if (endpoint === `/job-match/batches/${ids.batch}/analyze` && method === "POST" && state.batch) {
      state.batch = {
        ...state.batch,
        status: "COMPLETED",
        successful_jobs: state.batch.total_jobs,
        jobs: state.batch.jobs.map((job) => ({
          ...job,
          analysis_status: "COMPLETED",
          result: {
            id: ids.result,
            rank: 1,
            near_tie_group: null,
            is_tied: false,
            eligibility_status: "PASS",
            total_score: "82.00",
            display_score: 82,
            confidence_score: "76.00",
            confidence_level: "HIGH",
            recommendation_level: "STRONG",
            recommendation: "建议投递",
            created_at: now,
          },
        })),
      };
      return respond(response, 200, { data: state.batch });
    }
    if (endpoint === `/jobs/${ids.job}` && method === "GET" && state.batch?.status === "COMPLETED") {
      return respond(response, 200, { data: jobDetail() });
    }
    if (endpoint === `/jobs/${ids.job}/resume-tailor` && method === "POST" && state.resume) {
      const experience = state.resume.experiences[0];
      return respond(response, 200, { data: {
        job_id: ids.job,
        match_result_id: ids.result,
        resume_master_id: ids.resume,
        company_name: state.batch.jobs[0].company_name,
        job_title: state.batch.jobs[0].title,
        source_resume_snapshot: state.resume,
        draft: {
          professional_summary: "具有产品运营实战经历。",
          experiences: experience ? [{
            source_id: experience.id,
            include: true,
            order: 1,
            bullets: [{ text: experience.description, evidence_refs: [{ source_field: "description", source_quote: experience.description }] }],
          }] : [],
          projects: [],
          skill_order: state.resume.skills.map((item) => item.id),
          improvement_suggestions: [],
          warnings: [],
        },
        skill_name: "resume-tailor",
        prompt_version: "test-v1",
        model: "deterministic-fixture",
        attempts: 1,
      } });
    }
    if (endpoint === "/resume/versions" && method === "GET") return respond(response, 200, { data: state.version ? [state.version] : [] });
    if (endpoint === "/resume/versions" && method === "POST" && state.resume) {
      const input = await body(request);
      state.version = {
        id: ids.version,
        resume_master_id: ids.resume,
        job_id: ids.job,
        match_result_id: ids.result,
        name: `${state.batch.jobs[0].company_name} · ${state.batch.jobs[0].title}`,
        status: "SAVED",
        company_name: state.batch.jobs[0].company_name,
        job_title: state.batch.jobs[0].title,
        prompt_version: input.prompt_version,
        model: input.model,
        content: input.draft,
        source_resume_snapshot: state.resume,
        source_job_snapshot: jobDetail(),
        created_at: now,
        updated_at: now,
      };
      return respond(response, 201, { data: state.version });
    }
    if (endpoint === "/applications" && method === "GET") {
      return respond(response, 200, { data: state.application ? [state.application] : [] });
    }
    if (endpoint === "/applications" && method === "POST" && state.batch) {
      const input = await body(request);
      if (input.job_id !== ids.job || (input.resume_version_id && input.resume_version_id !== state.version?.id)) {
        return respond(response, 422, { error: { message: "Unknown source" } });
      }
      const job = state.batch.jobs[0];
      state.application = {
        id: ids.application,
        job_id: ids.job,
        resume_version_id: input.resume_version_id ?? null,
        company_name: job.company_name,
        job_title: job.title,
        job_url: job.source_url,
        applied_at: `${input.applied_at.slice(0, 10)}T00:00:00Z`,
        current_stage: "APPLICATION",
        current_round: null,
        process_status: "ACTIVE",
        note: input.note ?? null,
        created_at: now,
        updated_at: now,
        events: [{
          id: "88888888-8888-4888-8888-888888888888",
          application_id: ids.application,
          event_type: "APPLICATION",
          custom_event_name: null,
          round_no: null,
          occurred_at: `${input.applied_at.slice(0, 10)}T00:00:00Z`,
          outcome: null,
          note: null,
          created_at: now,
          updated_at: now,
        }],
      };
      return respond(response, 201, { data: state.application });
    }
    if (endpoint === `/applications/${ids.application}` && method === "GET" && state.application) {
      return respond(response, 200, { data: state.application });
    }
    if (endpoint === "/dashboard" && method === "GET") {
      const items = state.application ? [state.application] : [];
      return respond(response, 200, { data: {
        overview: { total: items.length, active: items.length, rejected: 0, offer: 0, withdrawn: 0 },
        recent_applications: items,
      } });
    }
    console.error(`Unexpected mock API call: ${method} ${endpoint}`);
    return respond(response, 404, { error: { code: "NOT_FOUND", message: `${method} ${endpoint}` } });
  } catch (error) {
    console.error(error);
    respond(response, 500, { error: { message: String(error) } });
  }
});

server.listen(8765, "localhost", () => console.log("E2E API ready on localhost:8765"));
