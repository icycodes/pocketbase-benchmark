# PocketBase Superuser and Task Seeding via CLI

## Goal
Write an idempotent shell script `setup.sh` at `/home/user/myproject/setup.sh` that prepares a clean PocketBase v0.31.0 instance: creates a superuser non-interactively, applies a migration that defines a `tasks` collection, starts the server in the background, and seeds five predefined task records via the PocketBase REST API. Running the script multiple times must NOT create duplicates and must not error.

## Acceptance Criteria
- Project path: `/home/user/myproject`
- The PocketBase v0.31.0 binary is available at `/home/user/myproject/pocketbase` (already pre-installed in the environment).
- Command: `bash setup.sh`
- After the command completes (the first time and every subsequent time), all of the following must hold:
    - The PocketBase server is running and responds to `GET http://127.0.0.1:8090/api/health` with HTTP 200.
    - Exactly one superuser record exists in the `_superusers` collection with email `admin@example.com` and password `Adm1n_passw0rd!`. The password must work with the `POST /api/collections/_superusers/auth-with-password` endpoint.
    - A collection named `tasks` (type `base`) exists with the following schema fields: `title` (text, required), `done` (bool), `due` (date).
    - Exactly 5 records exist in the `tasks` collection with the following `title` values (one record per title, no duplicates, exact case):
        - `Buy groceries`
        - `Walk the dog`
        - `Read a book`
        - `Write weekly report`
        - `Call mom`
- Idempotency: Running `bash setup.sh` two times in a row from the same project directory must exit with status 0 both times and must leave the counts at exactly 1 superuser and exactly 5 `tasks` records.
- The server started by the script must keep running after the script exits (so the REST API can be queried).

