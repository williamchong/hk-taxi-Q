## Reading a versioned JSON document the ETL wrote.
##
## Shared by the `generated_*.gd` locators, which otherwise carried this
## twenty-line body verbatim apiece. What differs between them — the path, the
## schema version it was written against, and what to say when the file is not
## there — is the reason each locator exists; the parse, the type check and the
## version check are not.
##
## The schema mismatch message matters most. It is the one a stale copy
## produces, it is the one a developer actually reads, and `P1-6` adds a fourth
## caller for `city.json`.
extends RefCounted


## The parsed document, or an empty dictionary with a pushed message.
##
## Empty rather than null so callers can use `is_empty()` without a type check,
## and so a missing file and a malformed one lead to the same early return.
static func load_object(path: String, schema_version: int, missing_hint: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		# A warning, not an error: `assets/generated/` is gitignored build
		# output, so a fresh clone has none of it and that is expected.
		push_warning(missing_hint)
		return {}

	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("%s is not a JSON object" % path)
		return {}

	var document: Dictionary = parsed
	var version: int = int(document.get("schema_version", -1))
	if version != schema_version:
		# The data contract is versioned and the ETL bumps it on any change, so
		# a mismatch is a stale copy rather than something to parse optimistically.
		push_error(
			(
				"%s declares schema_version %d, this build reads %d. Re-run the ETL and re-copy."
				% [path, version, schema_version]
			)
		)
		return {}
	return document
