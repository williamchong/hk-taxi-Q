class_name TuningTable
extends RefCounted
## The one check every tuning table gets at the door (`Q119`, `fares.md`): a
## `.tres` field that reads zero is a key missing from the file, since no
## profile script declares a default, and the system that needed it becomes
## INERT with the file and the field named — never one running on a literal.
##
## `FareMeter`, `SkillTracker` and `FareSystem` each carried this loop; the
## message is the same shape in all three, and a fourth copy is what this file
## exists to stop. Pure and static, so a verify tool can drive it without a
## scene.


## Whether any of `fields` is at or under zero, pushing an error that names
## `who` is refusing, which file and field, and what `consequence` follows.
static func any_zero(
	table: Resource, fields: Dictionary[String, float], who: String, consequence: String
) -> bool:
	for key: String in fields:
		if fields[key] <= 0.0:
			push_error("%s: %s has no %s; %s." % [who, table.resource_path, key, consequence])
			return true
	return false
