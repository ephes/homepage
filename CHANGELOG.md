# Changelog

## Unreleased

- Stream rendition repair diagnostics per post and keep only counts for blog
  and invocation summaries.

- Restore the Saira generator's handlers after partial signal setup failures.
- Cap ffprobe JSON reports at 64 KiB and reap the child on refusal or timeout.

- Verify all affected Saira destinations and backups before beginning rollback.
- Preserve the Saira generation result if closing its lock fails.

- Read portfolio shell and legal settings from the selected Wagtail site's
  database alias, with unsaved defaults when that site has no settings row.
- Recommend the sole public sibling in a draft portfolio project preview.

- `CastURLResolver` resolves Cast targets and their view restrictions in the
  selected Wagtail site's database.

- `CastURLResolver` accepts canonical Cast posts and their supported public
  episode routes and rejects unknown post subpaths. django-indieweb does not
  call this resolver, so incoming Webmention handling is unchanged.

- Escape non-printable characters and cap outgoing Webmention target
  diagnostics at 256 characters.

- Recheck the live revision and Wagtail view restrictions after rendering an
  outgoing Webmention so changes during rendering can suppress delivery.

- Return a generic `502` when a Fediverse DNS lookup raises an unexpected
  exception, and release its lookup slot.

- Reject a Fediverse proxy response that completes after the deadline with a
  `504`: the elapsed time is checked after receiving upstream headers and after
  reading and closing the response stream, even if the shutdown timer runs late.

- Preserve all upstream Fediverse `Cache-Control` directives in order.

- Close the upstream Fediverse response stream when a bounded read fails.

- Scan and report each blog once per database alias and page ID during
  rendition repair. Read its posts from the same database.

- Require database autocommit before repairing renditions so an outer rollback
  cannot orphan replacement files.

- Preserve the request method and form body when redirecting slashless portfolio
  POSTs.

- Show the project creation shortcut to editors with Wagtail add permission
  on a portfolio homepage they cannot edit.

- Report portfolio page creation only after the database commits.

- Keep unrelated uploads out of blog cover rollback even when they share the
  same storage backend.

- Stage blog cover uploads from one bounded regular file before publication so
  later changes to the source cannot change the uploaded bytes.

- Serialize portfolio creation under the Wagtail parent and report a conflicting
  hostname and port without leaving a draft page behind.

- Keep the local Micropub article title draft when switching between Article and Note.

- Reject Micropub category batches over 50 entries or 4,096 characters before
  expanding the local form input or validating individual tags.

- Publish both development ownership records atomically so cleanup always reads
  a complete record during startup.

- Restore development supervisor signal handlers after an output pipe close
  failure and preserve any existing exception or nonzero child exit status.

- Respect live reduced-motion preferences when closing the portfolio theme menu.

- Synchronize the portfolio theme, checked option and switch label across open
  tabs, including resets to System.

- Paginate the staff account directory by username and keep the profile links
  on every page.

- Save only the display name from a profile edit and return 404 if the account
  disappeared before saving.

- Display each legacy webmention type in one section after the preferred types.

- Keep undated webmentions at the end of each section in input order.

- Recover weeknote receipts only from bounded regular files that stay unchanged while being read.

- Sync the weeknote receipt directory before page writes and keep the journal until report publication is durable.

- Preserve rendition repairs and later commit callbacks when a deferred cache purge and its warning both fail.

- Verify the stored replacement name and available size before attaching a repaired rendition.

- Fetch unresolved Micropub source images from the post's database for both
  live and draft content.

- Return the normal missing-target response when a Micropub source page or its
  content type disappears during URL resolution.

- Load both homepage users with one query and preserve the missing-user fallback.

- Accept HEAD on `/favicon.ico` with the same file metadata and cache policy as GET.

- Resolve the published Post or Episode on the publishing database before
  scheduling outgoing webmentions.

- Keep committed publications and later commit callbacks running if both
  webmention delivery and its warning log fail.

- Require POST for the authenticated local Micropub preview.

- Preserve the local Micropub form's redirect and success message if logging
  fails after post creation.

- Sync legacy backup publication and staging cleanup before starting restore.
  Preserve the named backup and report its path if durability is uncertain.

- Cap legacy backup SFTP prefetch at 64 requests and disable it with older
  Paramiko versions that lack a request limit.

- Probe Wagtail routes using only page identity and load the full page from the
  selected site's database.

- Purge repaired rendition cache entries after the outer transaction commits.

- Scope portfolio seeding to the requested site root or default-site path.

- Allow portfolio sites on distinct ports of the same hostname while rejecting
  an occupied hostname and port with a mismatched root.

- Reuse portfolio detail navigation for recommendations and the project counter.

- Check each project content block once when preparing case-study sections.

- Skip deleted rendition rows during cache purge retry and report only renewed
  purge failures in the next retry command.

- Refuse ambiguous blog slugs before repairing any rendition and report the
  matching Wagtail page IDs and tree paths.

- Skip outgoing webmentions when an alias source disappears during publication.

- Skip outgoing webmentions for publications with cyclic page aliases.

- Group weeknote links in one pass while preserving display order.

- Render stored weeknote links with retired categories in a final Other links group.

- Require the database alias reported by rendition repair when retrying a cache purge.

- Keep the original rendition link when the file reappears or storage cannot
  confirm it is still absent during repair.

- Fetch post and gallery image relationships in batches during rendition repair.

- Resolve Wagtail page URLs using the target host’s portfolio or main URL routes.

- Open legal settings in Draftail when stored text contains uppercase or mixed-case
  HTML line breaks.

- Limit portfolio detail pages' teaser image and rendition loads to their
  recommendations.

- Use the base portfolio static URL in debug mode if an asset source disappears
  during a local rebuild.

- Hide optional portfolio rich-text blocks containing only encoded whitespace
  or starter placeholders, and treat plain-text fields literally.

- Reload the live Webmention post and check its access restrictions on the
  publishing database.
- Schedule Webmention delivery on the publishing database so a rollback on
  that connection discards the delivery.
- Log only allowlisted CSP directive names, violation keywords and non-HTTP(S)
  schemes, grouping unknown names under `other`.
- Validate CSP report body shapes against their browser media types before
  logging, while accepting empty Reporting API batches.
- Limit CSP report logs to reviewed same-origin route prefixes and show only
  origins for other HTTP(S) locations.
- Stop scanning Reporting API batches after the first five supported CSP reports.

- Security (owner decisions from the 2026-11-17 audit): IndieAuth sign-ins may
  only claim the logged-in account's own profile URL
  (`INDIEWEB_BIND_ME_TO_USER`, on by default), so no other account can sign in
  elsewhere as `https://wersdoerfer.de/jochen/`. Wagtail's unthrottled admin
  password reset (`/cms/password_reset/`) is off; allauth's rate-limited reset
  stays. The development server binds `127.0.0.1` (opt in with
  `DJANGO_RUNSERVER_ADDR`) and local `ALLOWED_HOSTS` default to local names.
  A first `Content-Security-Policy-Report-Only` policy reports violations to
  `/csp-report/`, which logs bounded, query-free lines (docs/csp.rst).

- Upgrade Wagtail 8.0.1 to 8.1 (range `>=8.1,<8.2`) and relock django-cast to
  develop e0c632ad (release 0.2.68 plus the 0.2.69 version bump; from
  93ac6cb4), which carries the Wagtail 8 hook order and media chooser fixes.
  draftjs-exporter moves to 7.3.1 with Wagtail. Neither Wagtail nor django-cast
  adds migrations in this range.

- Key allauth's per-IP rate limits (login, failed login, password reset,
  signup) on the client address Traefik appends to `X-Forwarded-For`
  (`ALLAUTH_TRUSTED_PROXY_COUNT`, following `DJANGO_NUM_PROXIES`). Previously
  all visitors shared the proxy's address, so one client could get
  `/accounts/login/` refused with 429 for everybody.

- Escape Micropub location labels as literal text in publication and preview,
  preserving tags and entities as supplied through source queries. Keep the
  generated map link and sanitizer; existing posts are unchanged.

- Admit zero-valued Micropub coordinates and validate finite decimal latitude/
  longitude ranges (at most 32 characters, exponent within ±32) before publication; reject malformed locations without
  partial writes. Build map URLs with standard URL encoding and share validation
  with optional preview locations, render coordinates in fixed-point notation
  and skip blank plain location labels. Existing posts are unchanged.

- Preserve exact source whitespace in Micropub plain-text fenced code through
  publication, preview and source queries; existing posts are unchanged.

- Append and fsync one weeknote receipt frame per completed page, then serialize
  the final JSON array once. Retain private journals and committed IDs on failures;
  recover validated checkpoints without replay and refuse incomplete frames.

- Bound weeknote conversion inventories by post, stored-body and receipt budgets;
  traverse uncached page IDs with explicit partial-run continuation and exact
  committed revision receipts. Guard hydration again during conflict checks.

- Check shared images only once per rendition repair invocation, including
  direct/gallery overlap across posts and blogs; count each repair or incomplete
  outcome once and report the number of unique images checked.

- Retain committed cover and social rendition files when a post-commit callback
  fails; report blog/image/revision IDs and pending callback recovery without
  repeating publication. Cover import now requires its own commit boundary.

- Bound legacy SSH command output and transport deadlines (download deadline scaled
  with the backup size, prefetching kept), require one successful backup announcement
  and a complete verified gzip download, close all transports before publication and
  preserve existing backups through private no-clobber staging.

- Make the legacy transfer helper inert on import, use literal Docker arguments,
  propagate process failures and delegate local SQL publication to the maintained
  restore with explicit existing-database replacement consent, checked before any
  transfer or Docker step.

- Stage and validate the complete Saira font/license/CSS set before publication,
  roll back handled failures (including Ctrl-C, SIGTERM and SIGHUP) and retain
  git-ignored recovery backups if rollback fails or is interrupted.
- Serialize Saira generation with a stable local lock and refuse changed source,
  license, stylesheet or output generations; preserve CSS outside the markers.

- Relock django-cast to develop 93ac6cb4 (from c290ec1a): transcript version
  admission, blog cache snapshots, public render and comment-target boundaries,
  regeneration consent, atomic glossary imports, configured-storage failures
  without silent fallback, preserved facet queries and bounded theme discovery.
  No new migrations.

- Limit development logs to a 5 MiB active file and two rotated backups (15 MiB
  total), preserving UTF-8 boundaries and the latest output.

- Stream development output in fixed byte chunks with incremental UTF-8 decoding
  and bounded colour-sequence carry, including large unterminated lines.

- Admit the stable development lock without truncation or symlink traversal,
  reject hardlinks/special files and fence its named inode after locking.

- Reserve the development supervisor's group identity until bounded TERM/KILL
  retirement completes, including resistant descendants of exited leaders;
  retain ownership evidence when retirement cannot be confirmed. The TERM grace
  stays ten seconds; on macOS the runner needs Python 3.13 or newer
  (`os.waitid`) and refuses older interpreters before starting services.

- Validate portfolio half-float filtering and framebuffer completeness, bound hero
  surfaces by device dimensions and pixel budget, and show terminal readable
  fallback on WebGL context loss while releasing allocated resources.
- Retire settled cursor frames and fence pending handwriting font completion by
  the live motion preference and startup generation. Reduced motion immediately
  restores plain about text and cancels its queued animation work.
- Resync reel overflow and ARIA state after intrinsic content changes, and bind
  dragging to one pointer through cancellation and capture loss.
- Bound optional about-line animation work without limiting editorial content;
  retire stale navigation focus/scroll flights on conflicting menu actions.

- Refresh Soup Sieve 2.10 to 4.1 (CVE-2026-126190 and related selector DoS
  advisories) and notebook-only Tornado 6.6 to 6.6.1 (CVE-2026-126347).
  Beautiful Soup 4.15.0 remains compatible. Document-level CSS selectors now
  skip inert HTML template contents; select on the template to inspect them.

- Vary fediverse discovery proxy responses on Accept and preserve upstream
  wildcard variation so caches cannot reuse negotiated or uncacheable responses.
- Keep fediverse gateway warnings and transport exceptions free of raw upstream
  error details, retaining route/category diagnostics and admin-mail suppression.

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
