class_name LedgerCard
extends VBoxContainer
## The 成績表 (`P3-76`, `Q169`; the user's call 2026-11-01): a driver's account
## sheet, two tables side by side — 加分 and 扣分, item, count and HK$ — with the
## bests and the sum under them. One form for REPORT, free mode's PAUSE and the
## lifetime RECORD, the same shape of numbers each time (`SessionTally`).
##
## 🚫 **No TD 553 tick-boxes and no section headings.** `Q169` planned both; a
## bonus is not a fault (its 2026-10-28 amendment), and the page is the driver's
## books, not the examiner's form. 🚫 No red-light row: `P3-3d` is undecided.
##
## Every row's name is its `Fare.Skill` key and every value cell is named, so
## `verify_menu` reads what the player reads. A row in use or not always shows:
## a ledger's lines do not come and go.

## A value this page has none of yet.
const NONE: String = "—"

var _text: MenuText = null
var _profile: MenuProfile = null
var _style: HudStyle = null
var _language: String = Locale.DEFAULT
var _font_zh: Font = null


## Money with its sign, "+41.0" or "−10.0", a proper minus; nothing is "0.0".
static func signed(hkd: float) -> String:
	if is_zero_approx(hkd):
		return FareFace.money(0.0)
	return ("+" if hkd > 0.0 else "−") + FareFace.money(absf(hkd))


## Build the page. The tables are handed in, as `StartMenu` holds them.
func build(
	tally: SessionTally,
	text: MenuText,
	profile: MenuProfile,
	style: HudStyle,
	language: String,
	font_zh: Font
) -> void:
	_text = text
	_profile = profile
	_style = style
	_language = language
	_font_zh = font_zh
	add_theme_constant_override(&"separation", profile.ledger_gap_px)
	var tables: HBoxContainer = _pair_of_columns("Tables")
	_table(tables, "Bonus", "sheet_bonus", SessionTally.BONUSES, tally, style.plate_ink)
	_table(tables, "Penalty", "sheet_penalty", SessionTally.PENALTIES, tally, style.accent_negative)
	var books: HBoxContainer = _pair_of_columns("Books")
	_bests(books, tally)
	_sums(books, tally)


func _pair_of_columns(node_name: String) -> HBoxContainer:
	var pair := HBoxContainer.new()
	pair.name = node_name
	pair.add_theme_constant_override(&"separation", _profile.ledger_gutter_px)
	add_child(pair)
	return pair


## One table: its title, the column heads, a row per skill and the subtotal.
func _table(
	parent: Control,
	node_name: String,
	title_key: String,
	skills: Array[Fare.Skill],
	tally: SessionTally,
	ink: Color
) -> void:
	var column: VBoxContainer = _block(parent, node_name)
	_line_of(
		column,
		"Head",
		_text.say(title_key, _language),
		ink,
		_text.say("sheet_count", _language),
		"HK$",
		_style.chip_muted
	)
	_rule(column)
	var count: int = 0
	var sum: float = 0.0
	for skill: Fare.Skill in skills:
		var row: HBoxContainer = _row(column, ExamSheet.key_of(skill))
		_cell(row, "Name", ExamSheet.shared().item_name(skill, _language), _style.plate_ink)
		_cell(row, "Count", str(tally.counts[skill]), _style.plate_ink, _profile.ledger_count_px)
		_cell(row, "Money", signed(tally.banked[skill]), ink, _profile.ledger_money_px)
		count += tally.counts[skill]
		sum += tally.banked[skill]
	_rule(column)
	_line_of(
		column,
		"Subtotal",
		_text.say("sheet_subtotal", _language),
		_style.dial_needle,
		str(count),
		signed(sum),
		_style.dial_needle
	)


## A row of the table's own three columns: a name, then a count and money.
func _line_of(
	parent: Control,
	node_name: String,
	label: String,
	ink: Color,
	count: String,
	money: String,
	number_ink: Color
) -> void:
	var row: HBoxContainer = _row(parent, node_name)
	_cell(row, "Name", label, ink)
	_cell(row, "Count", count, number_ink, _profile.ledger_count_px)
	_cell(row, "Money", money, number_ink, _profile.ledger_money_px)


## The four bests, left under the bonuses.
func _bests(parent: Control, tally: SessionTally) -> void:
	var column: VBoxContainer = _block(parent, "Bests")
	var ink: Color = _style.plate_ink
	var slide: float = tally.longest_slide_s
	var flight: float = tally.longest_flight_s
	var closest: float = tally.closest_pass_m
	var speed: float = tally.top_speed_kph
	_pair(column, "Slide", "sheet_best_slide", "%.2f s" % slide if slide > 0.0 else NONE, ink)
	_pair(column, "Flight", "sheet_best_flight", "%.2f s" % flight if flight > 0.0 else NONE, ink)
	_pair(
		column, "Pass", "sheet_best_pass", "%.2f m" % closest if not is_inf(closest) else NONE, ink
	)
	_pair(
		column, "Speed", "sheet_best_speed", "%d km/h" % roundi(speed) if speed > 0.0 else NONE, ink
	)


## The sum down to what banked, right under the penalties. The floor's line
## shows only where it moved the sum, and what walked stands under the total
## because it is in no line above it.
func _sums(parent: Control, tally: SessionTally) -> void:
	var column: VBoxContainer = _block(parent, "Sums")
	var ink: Color = _style.plate_ink
	_pair(column, "Meter", "sheet_meter", signed(tally.meter_hkd), ink)
	_pair(column, "Time", "sheet_time", signed(tally.time_hkd), ink)
	_pair(column, "Bonus", "sheet_bonus", signed(tally.bonus_hkd()), ink)
	_pair(column, "Penalty", "sheet_penalty", signed(tally.penalty_hkd()), _style.accent_negative)
	if tally.floored_hkd > 0.0:
		_pair(column, "Floored", "sheet_floored", signed(tally.floored_hkd), ink)
	_rule(column)
	_pair(column, "Total", "sheet_total", FareFace.money(tally.total_hkd()), _style.accent)
	if tally.forfeited_hkd > 0.0:
		_pair(
			column, "Walked", "sheet_walked", FareFace.money(tally.forfeited_hkd), _style.chip_muted
		)


func _block(parent: Control, node_name: String) -> VBoxContainer:
	var column := VBoxContainer.new()
	column.name = node_name
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_theme_constant_override(&"separation", 0)
	parent.add_child(column)
	return column


func _row(parent: Control, node_name: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.name = node_name
	row.custom_minimum_size.y = _profile.ledger_row_px
	parent.add_child(row)
	return row


## A label and a value on one row.
func _pair(parent: Control, node_name: String, key: String, value: String, ink: Color) -> void:
	var row: HBoxContainer = _row(parent, node_name)
	_cell(row, "Name", _text.say(key, _language), ink)
	_cell(row, "Value", value, ink, _profile.ledger_money_px)


## One cell: with no `width_px` it takes the row's slack on the left, else a
## right-aligned number in its own column, so a table's digits stand in line.
func _cell(row: Control, node_name: String, said: String, ink: Color, width_px: int = 0) -> void:
	var label := Label.new()
	label.name = node_name
	label.text = said
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_color_override(&"font_color", ink)
	label.add_theme_font_size_override(
		&"font_size", Locale.pick(_profile.body_size_zh, _profile.body_size, _language)
	)
	if _language == Locale.CHINESE and _font_zh != null:
		label.add_theme_font_override(&"font", _font_zh)
	if width_px > 0:
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		label.custom_minimum_size.x = width_px
	else:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_style.shade(label))


## A ruled line: what makes it a sheet.
func _rule(parent: Control) -> void:
	var rule := ColorRect.new()
	rule.name = "Rule"
	rule.color = _style.frame_ink
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rule.custom_minimum_size.y = _profile.ledger_rule_px
	parent.add_child(rule)
