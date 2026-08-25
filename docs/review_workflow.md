# Human-review workflow

`data/reviews/decisions.json` is the tracked record for the three human-input items in this
scope: dataset terms/legal review, the optional screenshot decision, and optional deployment
authorization. It intentionally contains no approval, screenshot, deployment, reviewer, date, or
legal conclusion.

## Collecting a review

1. Review the question and scope for the stable `id` in `decisions.json`.
2. A human reviewer records a decision by changing `status` from `pending` to `approved` or
   `rejected`. Do not infer a decision from the code, provenance metadata, or an absent value.
3. Fill `decision`, `reviewer`, `reviewed_at_utc`, and `rationale`. Use an ISO 8601 UTC timestamp,
   preferably with the `Z` suffix (for example, `2025-01-01T00:00:00Z`).
4. Populate `evidence_refs` with a non-empty reference for every field named by that item's
   `evidence_fields`. References may identify a URL, file, or review record; do not paste raw data
   or unsupported claims into this repository.
5. Run `python scripts/validate_reviews.py` and include the resulting file and evidence references
   in the review change. Pending items are reported and are not counted as complete.

The exact evidence fields are:

| ID | Required | Evidence fields |
| --- | --- | --- |
| `dataset_terms_legal_review` | Yes | `dataset_source_ref`, `terms_or_license_ref`, `review_scope_ref` |
| `screenshot_decision` | No | `decision_basis_ref`, `screenshot_ref_or_rejection_basis_ref` |
| `deployment_authorization` | No | `authorization_ref`, `deployment_scope_ref` |

## Evidence packets and recommended authority

These are recommendations, not assigned reviewers. The three records remain `pending`; the paths
below are available tracked context, not completed review evidence.

| Stable ID | Available tracked evidence paths | Still missing | Recommended human authority/role |
| --- | --- | --- | --- |
| `dataset_terms_legal_review` | `data/raw/provenance.json`; `docs/data_dictionary.md` | Human evidence for `terms_or_license_ref` and `review_scope_ref`: an independent determination covering intended use, presentation, and redistribution. The existing terms caveat is not that determination. | Terms/licensing authority |
| `screenshot_decision` | `README.md` (records the local-only boundary and that no screenshot is claimed) | Human evidence for `decision_basis_ref` and either a screenshot reference or rejection basis; no screenshot file or completed decision record is available. | Project owner/instructor |
| `deployment_authorization` | `README.md`; `ROADMAP.md` (record the local, non-hosted boundary) | Human evidence for `authorization_ref` and `deployment_scope_ref`, including the target and operational access; none is currently available. | Deployment/system owner |

## Status and audit rules

- `pending` is the only unresolved state. Its decision, reviewer, timestamp, and rationale remain
  null or empty; it does not satisfy the review.
- Only `approved` and `rejected` are terminal decisions. Both require a reviewer, UTC timestamp,
  rationale, and every exact evidence field; approval is not implied by validation passing.
- Keep stable IDs and preserve the prior JSON in version control when correcting a decision. Do not
  silently replace a terminal decision or reuse an ID for a different question; explain any change
  in the new rationale and review evidence.
- The `required` flag identifies whether an item is a required gate. Optional items may remain
  pending, but their pending status must remain visible and must not be described as decided.
