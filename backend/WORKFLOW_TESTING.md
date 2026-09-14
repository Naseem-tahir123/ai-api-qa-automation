# Stateful workflow testing

The workflow engine complements the existing independent endpoint tests. It builds a deterministic dependency graph from the parsed OpenAPI paths, captures identifiers returned by producer endpoints, and injects those real values into dependent requests.

## API flow

All routes require the existing bearer authentication token.

1. Generate endpoint test cases as usual.
2. Create a workflow with `POST /api/v1/workflows/specifications/{specification_id}/plans`.
3. Inspect its ordered steps with `GET /api/v1/workflows/plans/{plan_id}`.
4. Execute it with `POST /api/v1/workflows/plans/{plan_id}/execute` and this body:

   ```json
   {
     "target_base_url": "https://api.example.com",
     "auth_config": {"token": "target-api-token"},
     "stop_on_failure": true,
     "run_cleanup": true
   }
   ```

5. Fetch the diagnostic report from `GET /api/v1/workflows/plans/{plan_id}/report`.

The report distinguishes a direct failure from a blocked dependent step, retains the execution reason, shows safely persisted runtime context, and identifies the earliest root causes.

## Scaling strategy

Planning is deterministic and grouped by resource paths, so hundreds of endpoints are not sent to the language model in one prompt. The existing AI generation remains endpoint-scoped. More advanced OpenAPI links, request-body foreign keys, and business-specific workflows can later be added as explicit planning rules without replacing this execution model.

## Database migration

Run `alembic upgrade head` from the `backend` directory before using workflow routes.
