class_name Locale
extends RefCounted
## Which language the HUD's names are read in (`Q142`, the user's call): one
## at a time, never both on a row. A street plate is bilingual because the
## real one is; a callout is a message and reads in the player's language.
##
## ⚠️ **A stand-in for the options menu.** `--lang=` through `Cmdline` is what
## a drive can set today; the menu that will own this (`P3-5b`) replaces the
## read below and nothing else, because everything asks through `language()`.

const LANG_ARG: String = "--lang="
const ENGLISH: String = "en"
const CHINESE: String = "zh"
const DEFAULT: String = ENGLISH


## "en" or "zh". Anything else, or nothing, is the default.
static func language() -> String:
	return CHINESE if Cmdline.value(LANG_ARG).to_lower() == CHINESE else DEFAULT
