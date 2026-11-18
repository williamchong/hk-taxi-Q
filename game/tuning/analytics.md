# analytics.tres

Rationale for `game/tuning/analytics.tres` (`Q119`).

The PostHog client's config (`Q256`), a `PostHogConfig` from the vendored `addons/posthog/`
(0.1.4). Only `Analytics` (`scripts/core/analytics.gd`) loads it, and only on a player's run.
It is NOT `posthog/config` in `project.godot`: that setting makes the SDK set itself up in its
own `_ready`, before `Main` can say whether the run is a player's.

Every key not listed is the SDK's default, which the writer leaves out (`docs/configuration.md`
in the addon has the table).

- `api_key`: the project token of PostHog project `hk-taxi-Q`. Write-only and meant to ship in a
  client; it cannot read data back. The worst a copy can do is send fake events.
- `host`: the default, `https://us.i.posthog.com`. The project was created in the US region and a
  token only works on its own region's host; moving to EU means a new EU project and token.
- `person_profiles` = `NEVER` (2): anonymous events only. `identify` and `alias` are turned off,
  so no event can ever be tied to a person.
- `preload_feature_flags`, `send_feature_flag_event`, `send_default_person_properties_for_flags` =
  false: no flags are used, so no flag request is ever made and no device properties are sent for
  one. Turn them back on only with a flag or an experiment to read.
- `capture_exceptions`, `capture_exceptions_in_editor` = false: a Godot error's text can carry a
  file path, which on a desktop holds the OS user name. Revisit with a `before_send` that strips
  paths if crash reports are wanted.
- Kept at default and relied on: `capture_application_lifecycle_events` (installs, opens and
  backgrounding give sessions and retention), `persistence` (events queue under
  `user://posthog` offline and survive a force-kill), `flush_at` 20 / `flush_interval_seconds` 30
  (batched), `flush_on_quit` (the SDK owns the window close for a 3 s flush; `Main` still saves
  the run on the same notification first). The SDK also flushes when the app is backgrounded.

Server side, in the PostHog project settings: "Discard client IP data" (`anonymize_ips`) is on.
