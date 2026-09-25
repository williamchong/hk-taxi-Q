class_name Locale
extends RefCounted
## Which language the HUD's names are read in (`Q142`, the user's calls): one
## at a time, never both on a row — the callout and the street plate alike.
##
## Four readers in order, and the first that knows wins: the `--lang=` flag,
## the option the start menu saved (`Settings`, `P6-1`), the system's own
## language (the user's ask: a fresh install opens in the phone's language,
## menu and game alike), then the default. The flag stays in front of all of
## them so a scripted run reads the same language on every machine whatever
## the menu saved or the OS says — `drive.sh`'s frames are compared across
## runs (`Q27`), and it appends `--lang=zh` for that reason. Everything asks
## through `language()`, so the menu replaced the read below and nothing else.

const LANG_ARG: String = "--lang="
const ENGLISH: String = "en"
const CHINESE: String = "zh"
## Chinese, the user's call: the city is Hong Kong's.
const DEFAULT: String = CHINESE


## "en" or "zh". Anything else, or nothing, falls through to the next reader.
static func language() -> String:
	var flag: String = Cmdline.value(LANG_ARG).to_lower()
	if known(flag):
		return flag
	var saved: String = Settings.language()
	if known(saved):
		return saved
	var system: String = of_system(OS.get_locale_language())
	if known(system):
		return system
	return DEFAULT


## The game's code for an OS language tag, or "" for one it does not speak.
## `OS.get_locale_language()` is the language alone — `zh` for `zh_Hant_HK`
## and for `zh_CN` alike, which is right: there is one Chinese here, the
## city's, and a Mandarin phone still reads it.
static func of_system(tag: String) -> String:
	var code: String = tag.to_lower().get_slice("_", 0).get_slice("-", 0)
	return code if known(code) else ""


## Whether `code` is a language this game speaks.
static func known(code: String) -> bool:
	return code == ENGLISH or code == CHINESE
