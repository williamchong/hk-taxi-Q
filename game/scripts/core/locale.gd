class_name Locale
extends RefCounted
## Which language the HUD's names are read in (`Q142`, the user's calls): one
## at a time, never both on a row — the callout and the street plate alike.
##
## ⚠️ **A stand-in for the options menu.** `--lang=` through `Cmdline` is what
## a drive can set today; the menu that will own this (`P3-5b`) replaces the
## read below and nothing else, because everything asks through `language()`.

const LANG_ARG: String = "--lang="
const ENGLISH: String = "en"
const CHINESE: String = "zh"
## Chinese, the user's call: the city is Hong Kong's.
const DEFAULT: String = CHINESE


## "en" or "zh". Anything else, or nothing, is the default.
static func language() -> String:
	return ENGLISH if Cmdline.value(LANG_ARG).to_lower() == ENGLISH else DEFAULT
