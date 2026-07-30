## Where the ETL's tile output lives, and how to list it.
##
## One definition, because two things read it for different reasons — the
## preview scene draws them, `tools/verify_tiles.gd` checks them — and a moved
## directory that only half the callers learn about fails silently in the one
## that draws.
##
## Editor-only: an exported build cannot list `res://`. `CityStreamer` (`P2-1`)
## will read tile paths from `city.json` instead, which is the shipping route.
extends RefCounted

const DIR: String = "res://assets/generated/tiles"


## Tile files whose name ends with `suffix`, sorted. `_lod0.glb` picks a tier.
static func files(suffix: String = ".glb") -> PackedStringArray:
	var found: PackedStringArray = []
	for file_name: String in DirAccess.get_files_at(DIR):
		if file_name.ends_with(suffix):
			found.append(DIR.path_join(file_name))
	found.sort()
	return found


## The tile at `path`, or null if it is not a loadable scene.
static func load_tile(path: String) -> PackedScene:
	return load(path) as PackedScene


## Message for the case that reads as "the city is empty" rather than as an error.
static func missing_hint() -> String:
	return (
		"No tiles in %s. Run the ETL and copy its output there:\n" % DIR
		+ "  python -m pipeline.buildings --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/tiles/*.glb game/assets/generated/tiles/"
	)
