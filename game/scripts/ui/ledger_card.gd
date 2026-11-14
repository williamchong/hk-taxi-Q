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
## The bonuses carry a fourth column, the most of that skill one style combo
## held (`P3-2b`, `Q205`), and the bests a fifth line, the biggest combo's
## total. A combo is never money, so the column has no sum.
##
## Four ranks of type, so the eye lands in order (the user's ask 2026-11-15):
## the total, then a block's title, then its rows, then the column heads. A row
## nothing happened on is set in the muted ink, never dropped, and the total
## closes on the books' double rule. Amber is left to the page's heading: a
## subtotal is restated in the sums, so it is ink. On a phone the sums come
## first, since the answer was four screens down the scroll.
##
## Every row's name is its `Fare.Skill` key and every value cell is named, so
## `verify_menu` reads what the player reads. A row in use or not always shows:
## a ledger's lines do not come and go.

## A value this page has none of yet.
const NONE: String = "—"

## The ranks of type, smallest first: a column head, a row, a block's title
## and the total (`_type_px`).
enum Rank { HEAD, BODY, TITLE, TOTAL }

var _text: MenuText = null
var _profile: MenuProfile = null
var _style: HudStyle = null
var _language: String = Locale.DEFAULT
var _font_zh: Font = null
## The phone's one column (`Q206`): the pairs stacked, and type, rows and
## number columns at `MenuProfile.ledger_scaled`.
var _stacked: bool = false


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
	font_zh: Font,
	stacked: bool = false
) -> void:
	_text = text
	_profile = profile
	_style = style
	_language = language
	_font_zh = font_zh
	_stacked = stacked
	add_theme_constant_override(&"separation", profile.ledger_gap_px)
	var tables: BoxContainer = _pair_of_columns("Tables")
	_table(tables, "Bonus", "sheet_bonus", SessionTally.BONUSES, tally, style.plate_ink, true)
	_table(tables, "Penalty", "sheet_penalty", SessionTally.PENALTIES, tally, style.accent_negative)
	var books: BoxContainer = _pair_of_columns("Books")
	if _stacked:
		# The answer first in the phone's column, then the bests, then what made
		# them: under the tables the total was four screens down the scroll.
		_sums(books, tally)
		_bests(books, tally)
		move_child(books, 0)
	else:
		_bests(books, tally)
		_sums(books, tally)


## Two blocks side by side, or one over the other in the phone's column (`Q206`):
## the same nodes by the same names either way, so a reader finds both.
func _pair_of_columns(node_name: String) -> BoxContainer:
	var pair := BoxContainer.new()
	pair.name = node_name
	pair.vertical = _stacked
	pair.add_theme_constant_override(&"separation", _profile.ledger_gutter_px)
	add_child(pair)
	return pair


## "×10", or none: a combo's count as the sheet shows it.
static func times(count: int) -> String:
	return "×%d" % count if count > 0 else NONE


## One table: its title, the column heads, a row per skill and the subtotal,
## and with `combo` each skill's best style combo after its money.
func _table(
	parent: Control,
	node_name: String,
	title_key: String,
	skills: Array[Fare.Skill],
	tally: SessionTally,
	ink: Color,
	combo: bool = false
) -> void:
	var column: VBoxContainer = _block(parent, node_name)
	var head: HBoxContainer = _title(column, title_key, ink)
	_cell(
		head,
		"Count",
		_text.say("sheet_count", _language),
		_style.chip_muted,
		_px(_profile.ledger_count_px),
		Rank.HEAD
	)
	_cell(head, "Money", "HK$", _style.chip_muted, _px(_profile.ledger_money_px), Rank.HEAD)
	if combo:
		_cell(
			head,
			"Combo",
			_text.say("sheet_combo", _language),
			_style.chip_muted,
			_px(_profile.ledger_count_px),
			Rank.HEAD
		)
	_rule(column)
	var count: int = 0
	var sum: float = 0.0
	for skill: Fare.Skill in skills:
		var row: HBoxContainer = _row(column, ExamSheet.key_of(skill))
		var live: bool = tally.counts[skill] > 0
		var row_ink: Color = _ink_of(live, _style.plate_ink)
		_cell(row, "Name", ExamSheet.shared().item_name(skill, _language), row_ink)
		_cell(row, "Count", str(tally.counts[skill]), row_ink, _px(_profile.ledger_count_px))
		_cell(
			row,
			"Money",
			signed(tally.banked[skill]),
			_ink_of(live, ink),
			_px(_profile.ledger_money_px)
		)
		if combo:
			_cell(
				row, "Combo", times(tally.combo_best[skill]), row_ink, _px(_profile.ledger_count_px)
			)
		count += tally.counts[skill]
		sum += tally.banked[skill]
	_rule(column)
	# The label muted and the numbers in the table's ink: the sums restate it.
	var subtotal: HBoxContainer = _row(column, "Subtotal")
	_cell(subtotal, "Name", _text.say("sheet_subtotal", _language), _style.chip_muted)
	var any: bool = count > 0
	_cell(
		subtotal, "Count", str(count), _ink_of(any, _style.plate_ink), _px(_profile.ledger_count_px)
	)
	_cell(subtotal, "Money", signed(sum), _ink_of(any, ink), _px(_profile.ledger_money_px))
	if combo:
		# No sum: a combo is a count of one run, and the best total is a best.
		_cell(subtotal, "Combo", "", ink, _px(_profile.ledger_count_px))


## A block's first row, its title a rank over the rows, and the rule under it
## left to the caller: a table sets its column heads beside the title first.
func _title(column: Control, key: String, ink: Color) -> HBoxContainer:
	var row: HBoxContainer = _row(column, "Head")
	_cell(row, "Name", _text.say(key, _language), ink, 0, Rank.TITLE)
	return row


## The bests, left under the bonuses: four of the drive and the biggest combo.
func _bests(parent: Control, tally: SessionTally) -> void:
	var column: VBoxContainer = _block(parent, "Bests")
	_title(column, "sheet_bests", _style.plate_ink)
	_rule(column)
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
	_pair(column, "Combo", "sheet_best_combo", times(tally.combo_best_total), ink)


## The sum down to what banked, right under the penalties. The floor's line
## shows only where it moved the sum, and what walked stands under the total
## because it is in no line above it.
func _sums(parent: Control, tally: SessionTally) -> void:
	var column: VBoxContainer = _block(parent, "Sums")
	_title(column, "sheet_sums", _style.plate_ink)
	_rule(column)
	var ink: Color = _style.plate_ink
	_pair(column, "Meter", "sheet_meter", signed(tally.meter_hkd), ink)
	_pair(column, "Time", "sheet_time", signed(tally.time_hkd), ink)
	_pair(column, "Bonus", "sheet_bonus", signed(tally.bonus_hkd()), ink)
	_pair(column, "Penalty", "sheet_penalty", signed(tally.penalty_hkd()), _style.accent_negative)
	if tally.floored_hkd > 0.0:
		_pair(column, "Floored", "sheet_floored", signed(tally.floored_hkd), ink)
	_rule(column)
	# The line the sheet is for: a taller row, its label a title and its number
	# the largest type on the page, closed by the books' double rule.
	var total: HBoxContainer = _pair(
		column,
		"Total",
		"sheet_total",
		FareFace.money(tally.total_hkd()),
		_style.accent,
		Rank.TITLE,
		Rank.TOTAL
	)
	total.custom_minimum_size.y = _px(_profile.ledger_total_row_px)
	_rule(column)
	var gap := Control.new()
	gap.name = "RuleGap"
	gap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gap.custom_minimum_size.y = _profile.ledger_rule_px
	column.add_child(gap)
	_rule(column)
	if tally.forfeited_hkd > 0.0:
		# A footnote: it is in no line above, and it is not the player's money.
		_pair(
			column,
			"Walked",
			"sheet_walked",
			FareFace.money(tally.forfeited_hkd),
			_style.chip_muted,
			Rank.HEAD,
			Rank.HEAD
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
	row.custom_minimum_size.y = _px(_profile.ledger_row_px)
	parent.add_child(row)
	return row


## A label and a value on one row, each at its rank; a value there is none of
## is muted with its label.
func _pair(
	parent: Control,
	node_name: String,
	key: String,
	value: String,
	ink: Color,
	name_rank: Rank = Rank.BODY,
	value_rank: Rank = Rank.BODY
) -> HBoxContainer:
	var row: HBoxContainer = _row(parent, node_name)
	var row_ink: Color = _ink_of(value != NONE, ink)
	_cell(row, "Name", _text.say(key, _language), row_ink, 0, name_rank)
	_cell(row, "Value", value, row_ink, _px(_profile.ledger_money_px), value_rank)
	return row


## `ink`, or the muted ink on a line nothing happened on: the line stays.
func _ink_of(live: bool, ink: Color) -> Color:
	return ink if live else _style.chip_muted


## One cell: with no `width_px` it takes the row's slack on the left, else a
## right-aligned number in its own column, so a table's digits stand in line.
## Set at `rank`'s size.
func _cell(
	row: Control,
	node_name: String,
	said: String,
	ink: Color,
	width_px: int = 0,
	rank: Rank = Rank.BODY
) -> void:
	var label := Label.new()
	label.name = node_name
	label.text = said
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_color_override(&"font_color", ink)
	label.add_theme_font_size_override(&"font_size", _px(_type_px(rank)))
	if _language == Locale.CHINESE and _font_zh != null:
		label.add_theme_font_override(&"font", _font_zh)
	if width_px > 0:
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		label.custom_minimum_size.x = width_px
	else:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_style.shade(label))


## `rank`'s size in the sheet's language, at the desk's scale.
func _type_px(rank: Rank) -> int:
	match rank:
		Rank.HEAD:
			return Locale.pick(_profile.ledger_head_size_zh, _profile.ledger_head_size, _language)
		Rank.TITLE:
			return Locale.pick(_profile.ledger_title_size_zh, _profile.ledger_title_size, _language)
		Rank.TOTAL:
			return Locale.pick(_profile.ledger_total_size_zh, _profile.ledger_total_size, _language)
	return Locale.pick(_profile.body_size_zh, _profile.body_size, _language)


## `px` at this sheet's scale.
func _px(px: int) -> int:
	return _profile.ledger_scaled(px, _stacked)


## A ruled line: what makes it a sheet.
func _rule(parent: Control) -> void:
	var rule := ColorRect.new()
	rule.name = "Rule"
	rule.color = _style.frame_ink
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rule.custom_minimum_size.y = _profile.ledger_rule_px
	parent.add_child(rule)
