# Changelog

## Unreleased

- Serialize shared file-cache login failure updates without losing concurrent
  attempts; preserve existing lockouts and sliding windows.
- Reserve client and normalized-username login capacity during authentication,
  releasing it on success, refusal and exceptions, with a five-minute crash lease.
