# PocketBase API Rules: Relational Access Control

## Background
You are building a document management system using PocketBase standalone. You need to implement a relational access control model where a document can be edited by its owner OR by users who have been explicitly granted edit permissions via a separate relational table.

## Requirements
- Initialize a PocketBase project.
- Create a `documents` collection with fields:
  - `title` (text)
  - `author` (relation to the `users` collection, single, required)
- Create a `document_edit_permissions` collection with fields:
  - `document` (relation to the `documents` collection, single, required)
  - `grantee` (relation to the `users` collection, single, required)
- Configure the API rules for the `documents` collection:
  - **View Rule**: Allow anyone to view documents.
  - **Update Rule**: Allow an authenticated user to update a document ONLY IF they are the `author` OR if their user ID exists as a `grantee` in a `document_edit_permissions` record that points to this document.
- You may use JS migrations in the `pb_migrations` directory to programmatically define these collections and rules.

## Implementation Hints
- Download and extract the PocketBase standalone binary (v0.31.0) into the project directory.
- Write a JS migration script in `pb_migrations/` to create the collections. When PocketBase starts, it will automatically apply the migration.
- To check a back-relation in PocketBase API rules, use the syntax `[currentField].[referencedCollection]_via_[referencedField].[fieldToCheck]`. For example, to check if the current document's `id` is referenced by the `document` field of the `document_edit_permissions` collection, you can use `id.document_edit_permissions_via_document.grantee`.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- The `documents` collection must exist with the correct fields.
- The `document_edit_permissions` collection must exist with the correct fields.
- The `View` API rule on `documents` must be public (allow anyone).
- The `Update` API rule on `documents` must enforce that only the author or a grantee can update the document.

