# ChatVault AI Frontend

React + TypeScript interface for the local ChatVault AI backend.

## Stack

- React 19, Vite, TypeScript
- Tailwind CSS v4 (`@tailwindcss/vite`)
- React Router
- TanStack Query
- Axios
- React Markdown + remark-gfm
- Prism React Renderer
- Lucide React icons

## Setup

Start the FastAPI backend first (see the repository root README), then:

```bash
npm install
cp .env.example .env
npm run dev
```

The development server runs at <http://127.0.0.1:5173>.

`frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

The backend must allow the frontend origin through `CORS_ORIGINS`. The default
backend settings already allow `http://localhost:5173` and
`http://127.0.0.1:5173`.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite development server. |
| `npm run build` | Type-check with `tsc -b` and build to `dist/`. |
| `npm run preview` | Serve the production build locally. |
| `npm run lint` | Run Oxlint. |

## Pages

- **Dashboard** — live conversation, message, chunk, and index coverage stats.
- **AI Chat** — retrieval-augmented answers with source citations and follow-up history.
- **Library** — title search, sorting, filters, and conversation deletion.
- **Import** — validate a public ChatGPT share URL, import it, and index it automatically.
- **Conversation** — full Markdown transcript, code highlighting, copy actions, and PDF/DOCX export.
- **Settings** — Ollama/model availability, ChromaDB and SQLite status, and full index rebuild.

All data comes from the FastAPI backend. There are no mock conversations or
simulated AI responses in the UI.
