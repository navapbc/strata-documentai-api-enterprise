# Extraction rules

When a document is processed, the platform extracts every field the AI model finds. Extraction rules let you control which of those fields matter - and which should be ignored - on a per-tenant, per-document-type basis.

## The problem they solve

Different organizations care about different things from the same document. A driver's license processed for one consumer might need name, date of birth, and license number. Another consumer might only need name and expiration date, and must not retain the license number. Without rules, every tenant gets every field the model returns - including fields they don't need and may not be permitted to store.

## How rules work

A rule is a configuration attached to a specific tenant and document type. It has two lists:

- **Required fields** - fields that must be present for the document to be considered successfully processed. If the model couldn't extract a required field, it shows up as missing in the result.
- **Optional fields** - fields the tenant wants if available, but won't fail without.

Any field not on either list is excluded from the result entirely. The tenant never sees it.

## What "excluded" means in practice

If a field isn't in required or optional, it's filtered out before the result is stored or returned. It doesn't appear in the document viewer, it doesn't show up in the API response, and it isn't written to the database. The raw model output still exists in S3, but the processed result only contains what the rule allows.

## Default behavior

If no rule exists for a tenant and document type, all extracted fields are returned as-is. This is the default behavior - useful during initial setup or testing, but not recommended for production tenants where field control matters.

## Managing rules

Rules are managed through the admin console under the Extraction Rules section, or directly via the API. Each rule is scoped to a tenant + document type pair, so the same document type can have different rules for different tenants.

You can create, update, or delete rules at any time. Changes take effect on the next document processed - existing results are not retroactively updated.

## Example

A tenant processes passport documents. Their rule:

- Required: `full_name`, `date_of_birth`, `passport_number`, `expiration_date`
- Optional: `nationality`, `place_of_birth`

If the model extracts `full_name`, `date_of_birth`, `passport_number`, `expiration_date`, and `mrz_code`, the result will contain the four required fields and drop `mrz_code` - it wasn't on either list. If `expiration_date` couldn't be read from the document, it appears in the missing fields list and the result is flagged as incomplete.
