# Changelog

## Unreleased

- Serialize shared file-cache login failure updates without losing concurrent
  attempts; preserve existing lockouts and sliding windows.
- Reserve client and normalized-username login capacity during authentication,
  releasing it on success, refusal and exceptions, with a five-minute crash lease.
- Recheck Micropub target identity, liveness, slug ambiguity and fresh Wagtail
  publication permissions after waiting for the parent-row lock.
- Add a channel-discovery query-scaling oracle covering inherited permissions,
  denied branches, inactive users, superusers, drafts and ambiguous slugs; the
  supported Wagtail cache already keeps SQL bounded.
