# Changelog

## Unreleased

- Report rendition cache purge failures separately from committed repairs and
  add a cache-only retry by rendition ID.
- Stage and atomically publish weeknote conversion reports, retaining recovery
  receipts and completed revision identities on handled failures. Published
  reports keep the umask-derived mode or the mode of the report they replace.

- Give cover uploads operation-specific names and compensate only storage with
  a proven exclusive-create contract; retain uncertain names with recovery diagnostics.
- Fence rendition repair attachment against current row identity and compensate
  losing repair output instead of overwriting a concurrent replacement.

- Reload and lock cover publication state, refuse competing drafts, and require
  the social rendition before committing a cover change.

- Convert historical portfolio live/latest conclusions independently and stream
  page hydration in forward and reverse migration passes, retaining rollback preflight.

- Serialize shared file-cache login failure updates without losing concurrent
  attempts; preserve existing lockouts and sliding windows.
- Reserve client and normalized-username login capacity during authentication,
  releasing it on success, refusal and exceptions, with a five-minute crash lease.
- Recheck Micropub target identity, liveness, slug ambiguity and fresh Wagtail
  publication permissions after waiting for the parent-row lock.
- Add a channel-discovery query-scaling oracle covering inherited permissions,
  denied branches, inactive users, superusers, drafts and ambiguous slugs; the
  supported Wagtail cache already keeps SQL bounded.
