# aigis-api-route

Guide for adding a new API route that spans both the FastAPI backend and React frontend.

## Architecture

- **Backend**: FastAPI routers under `src/aigis/web/routes/`, all mounted at `/api` prefix
- **Frontend**: React 19 + TypeScript + TanStack React Query + React Router
- API client at `src/aigis/web/frontend/src/api/client.ts` provides `apiFetch<T>()`

## Steps to Add a New Route

### 1. Create the Backend Router

Create `src/aigis/web/routes/<name>.py`:

```python
"""<Name> API routes."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MyResponse(BaseModel):
    """Response model."""
    items: list[dict]


@router.get("/<name>")
async def list_items() -> MyResponse:
    return MyResponse(items=[])


@router.post("/<name>")
async def create_item(payload: MyCreateRequest) -> MyResponse:
    # implementation
    return MyResponse(items=[])
```

To access shared app state (config, config_path):

```python
from fastapi import Request

@router.get("/<name>")
async def list_items(request: Request) -> MyResponse:
    config = request.app.state.config
    # ...
```

### 2. Register the Router

In `src/aigis/web/app.py`, add:

```python
from aigis.web.routes.<name> import router as <name>_router

# Inside create_app():
app.include_router(<name>_router, prefix="/api", tags=["<name>"])
```

### 3. Create the Frontend API Module

Create `src/aigis/web/frontend/src/api/<name>.ts`:

```typescript
import { apiFetch } from "./client";

export interface MyItem {
  id: string;
  // ... fields matching backend response
}

export function fetchItems(): Promise<MyItem[]> {
  return apiFetch<MyItem[]>("/<name>");
}

export function createItem(data: Partial<MyItem>): Promise<MyItem> {
  return apiFetch<MyItem>("/<name>", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
```

### 4. Create the React Component

Create `src/aigis/web/frontend/src/components/<name>/<Name>.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { fetchItems } from "../../api/<name>";

export function MyPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["<name>"],
    queryFn: fetchItems,
  });

  if (isLoading) return <div className="p-6 text-zinc-400">Loading...</div>;
  if (error) return <div className="p-6 text-red-400">Error: {error.message}</div>;

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-zinc-100 mb-4">Title</h1>
      {/* render data */}
    </div>
  );
}
```

### 5. Add the Route to React Router

In `src/aigis/web/frontend/src/App.tsx`:

```tsx
import { MyPage } from "./components/<name>/<Name>";

// Inside <Routes>:
<Route path="/<name>" element={<MyPage />} />
```

### 6. Add Sidebar Link

In `src/aigis/web/frontend/src/components/layout/Sidebar.tsx`, add a nav entry with a Lucide icon.

### 7. Write Tests

- **Backend**: Add `tests/test_web_<name>.py` using FastAPI TestClient
- **Frontend**: Test the component renders with mocked query data

## Key Files

| Layer | File | Purpose |
|-------|------|---------|
| Backend | `src/aigis/web/routes/<name>.py` | FastAPI router |
| Backend | `src/aigis/web/app.py` | Router registration |
| Frontend | `src/aigis/web/frontend/src/api/<name>.ts` | API client functions |
| Frontend | `src/aigis/web/frontend/src/components/<name>/` | React components |
| Frontend | `src/aigis/web/frontend/src/App.tsx` | Route registration |
| Frontend | `src/aigis/web/frontend/src/components/layout/Sidebar.tsx` | Navigation |
| Frontend | `src/aigis/web/frontend/src/types/index.ts` | Shared TypeScript types |

## Reference Implementations

- **Simple CRUD**: `routes/audit.py` + `api/audit.ts` + `components/audit/AuditLog.tsx`
- **SSE streaming**: `routes/scan.py` + `hooks/useSSE.ts` + `components/dashboard/ScanOutput.tsx`
- **Settings with mutations**: `routes/settings.py` + `api/settings.ts` + `components/settings/Settings.tsx`

## Conventions

- All API paths are prefixed with `/api` automatically by `app.include_router`
- Frontend `apiFetch` prepends `/api` — pass paths without the prefix (e.g., `"/<name>"`)
- Use Pydantic `BaseModel` for all request/response schemas
- Use TanStack `useQuery` for reads, `useMutation` for writes
- Styling: Tailwind CSS with dark theme (bg-black/zinc palette)
