#!/usr/bin/env bash
# Build the iOS app onto a handset, or up to TestFlight.
#
#   IOS_TEAM_ID=<team> tools/ios.sh device [<device name or UDID>]
#   IOS_TEAM_ID=<team> tools/ios.sh testflight [<build number>]
#
# Both export an Xcode project into build/ios/app/ and let xcodebuild sign it.
# The Team ID comes from the environment and never lives in export_presets.cfg
# (docs/ARCHITECTURE.md): the preset is edited for the length of the export and
# put back, whatever happens.
#
# The export opens a window. A --headless one has no GPU, skips the shader
# baker without a word, and ships a PCK the phone spends minutes compiling
# (Q207) — so the PCK is checked for its Metal caches, not the exit code.
#
# device      builds Release, installs it and launches it. With no argument it
#             takes $IOS_DEVICE, else the one physical device devicectl knows.
# testflight  archives and uploads to App Store Connect, signed by the Apple ID
#             signed in to Xcode. The build number defaults to a UTC timestamp,
#             which only ever rises; the version is the project's. An upload
#             is tagged testflight/<version>-<build> on the commit the export
#             began from, and the tag pushed; `fastlane tag_released` tags a
#             published version v<version> on its build's commit.

set -euo pipefail

GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
PRESETS="$ROOT/game/export_presets.cfg"
OUT="$ROOT/build/ios/app"
PROJECT="$OUT/hk-taxi-Q.xcodeproj"
SCHEME="hk-taxi-Q"

usage() {
	sed -n '2,6p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' >&2
	exit 1
}

MODE="${1:-}"
case "$MODE" in
	device | testflight) ;;
	*) usage ;;
esac
if [[ -z "${IOS_TEAM_ID:-}" ]]; then
	echo "IOS_TEAM_ID is not set: the Apple Developer Team ID that signs the build" >&2
	exit 1
fi

BACKUP=""
restore_presets() {
	if [[ -n "$BACKUP" ]]; then
		cp "$BACKUP" "$PRESETS"
		rm -f "$BACKUP"
		BACKUP=""
	fi
}
trap restore_presets EXIT
trap 'exit 130' INT TERM

# Run a command into a log; on failure show its errors and where the rest is.
run_logged() {
	local log="$1"
	shift
	if ! "$@" >"$log" 2>&1; then
		grep -E "error:" "$log" >&2 || true
		echo "$1 failed; see $log" >&2
		exit 1
	fi
}

export_project() {
	echo "==> export the Xcode project"
	BACKUP="$(mktemp)"
	cp "$PRESETS" "$BACKUP"
	sed -i '' \
		-e "s|^application/app_store_team_id=\"\"|application/app_store_team_id=\"$IOS_TEAM_ID\"|" \
		-e 's|^application/export_project_only=false|application/export_project_only=true|' \
		"$PRESETS"
	if ! grep -q "^application/app_store_team_id=\"$IOS_TEAM_ID\"" "$PRESETS" ||
		! grep -q '^application/export_project_only=true' "$PRESETS"; then
		echo "the iOS preset no longer has the two lines this script sets" >&2
		exit 1
	fi

	rm -rf "$OUT"
	mkdir -p "$OUT"
	"$GODOT" --path "$ROOT/game" --export-release "iOS" "$OUT/hk-taxi-Q.ipa" >"$OUT/export.log" 2>&1 || true
	restore_presets

	# Godot exits 0 on an export that wrote nothing.
	if [[ ! -d "$PROJECT" ]]; then
		echo "no Xcode project was written; see $OUT/export.log" >&2
		exit 1
	fi
	local baked
	baked="$(LC_ALL=C grep -a -o 'metal\.cache' "$OUT/hk-taxi-Q.pck" | wc -l | tr -d ' ')"
	if [[ "$baked" -eq 0 ]]; then
		echo "the PCK holds no baked Metal shaders; see $OUT/export.log" >&2
		echo "(the Metal toolchain: xcodebuild -downloadComponent MetalToolchain)" >&2
		exit 1
	fi
	echo "    $baked baked shader caches in the PCK"
}

# The exported project pins an Apple Distribution identity, which automatic
# signing refuses; the archive is re-signed for distribution at upload.
build() {
	run_logged "$OUT/xcodebuild-$1.log" \
		xcodebuild -project "$PROJECT" -scheme "$SCHEME" -configuration Release \
		-derivedDataPath "$OUT/dd" -allowProvisioningUpdates \
		DEVELOPMENT_TEAM="$IOS_TEAM_ID" CODE_SIGN_STYLE=Automatic \
		CODE_SIGN_IDENTITY="Apple Development" "${@:2}"
}

one_physical_device() {
	local list status=0
	list="$(mktemp)"
	xcrun devicectl list devices --json-output "$list" >/dev/null
	# The status is kept past the rm: a refusal must not read as an empty name.
	python3 - "$list" <<'EOF' || status=$?
import json, sys

devices = [
    d["hardwareProperties"]["udid"]
    for d in json.load(open(sys.argv[1]))["result"]["devices"]
    if d["hardwareProperties"].get("reality") == "physical"
]
if len(devices) != 1:
    sys.exit(f"{len(devices)} physical devices known; name one, or set IOS_DEVICE")
print(devices[0])
EOF
	rm -f "$list"
	return "$status"
}

# App Store Connect refuses an icon with an alpha channel, and the exported set
# keeps the rounded corners' transparency. Each is flattened onto its own
# background, in the build copy only.
flatten_icons() {
	"$PYTHON" - "$OUT/hk-taxi-Q/Images.xcassets/AppIcon.appiconset" <<'EOF'
import pathlib, sys

from PIL import Image

for path in pathlib.Path(sys.argv[1]).glob("*.png"):
    icon = Image.open(path).convert("RGBA")
    flat = Image.new("RGB", icon.size, icon.getpixel((icon.width // 2, 2))[:3])
    flat.paste(icon, mask=icon.getchannel("A"))
    flat.save(path)
EOF
}

case "$MODE" in
	device)
		DEVICE="${2:-${IOS_DEVICE:-}}"
		[[ -n "$DEVICE" ]] || DEVICE="$(one_physical_device)"
		BUNDLE_ID="$(sed -n 's|^application/bundle_identifier="\(.*\)"|\1|p' "$PRESETS" | tail -1)"
		export_project
		echo "==> build for $DEVICE"
		build device -destination "id=$DEVICE" build
		echo "==> install"
		xcrun devicectl device install app --device "$DEVICE" \
			"$OUT/dd/Build/Products/Release-iphoneos/$SCHEME.app" >/dev/null
		xcrun devicectl device process launch --device "$DEVICE" "$BUNDLE_ID" >/dev/null 2>&1 ||
			echo "    installed, not launched: unlock the phone and open it"
		;;
	testflight)
		BUILD_NUMBER="${2:-$(date -u +%y%m%d%H%M)}"
		# Taken before the export: a build runs for minutes and HEAD can move under it.
		HEAD_AT_START="$(git -C "$ROOT" rev-parse HEAD)"
		DIRTY_AT_START="$(git -C "$ROOT" status --porcelain --untracked-files=no | wc -l | tr -d ' ')"
		VERSION="$(sed -n 's|^config/version="\(.*\)"|\1|p' "$ROOT/game/project.godot")"
		if [[ -z "$VERSION" ]]; then
			echo "game/project.godot names no config/version" >&2
			exit 1
		fi
		export_project
		flatten_icons
		echo "==> archive build $BUILD_NUMBER"
		build archive -destination "generic/platform=iOS" \
			-archivePath "$OUT/$SCHEME.xcarchive" CURRENT_PROJECT_VERSION="$BUILD_NUMBER" archive
		cat >"$OUT/upload_options.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>method</key><string>app-store-connect</string>
	<key>destination</key><string>upload</string>
	<key>teamID</key><string>$IOS_TEAM_ID</string>
	<key>signingStyle</key><string>automatic</string>
	<key>manageAppVersionAndBuildNumber</key><false/>
</dict>
</plist>
EOF
		echo "==> upload"
		run_logged "$OUT/upload.log" \
			xcodebuild -exportArchive -archivePath "$OUT/$SCHEME.xcarchive" \
			-exportOptionsPlist "$OUT/upload_options.plist" -exportPath "$OUT/upload" \
			-allowProvisioningUpdates
		echo "    build $BUILD_NUMBER is with App Store Connect, processing"
		TAG="testflight/$VERSION-$BUILD_NUMBER"
		MESSAGE="TestFlight build $BUILD_NUMBER of $VERSION"
		if [[ "$DIRTY_AT_START" -gt 0 ]]; then
			MESSAGE+=$'\n\n'"Built with $DIRTY_AT_START tracked paths uncommitted."
		fi
		echo "==> tag $TAG"
		# The upload has gone through: a refused tag is reported, not fatal.
		if git -C "$ROOT" tag -a "$TAG" -m "$MESSAGE" "$HEAD_AT_START"; then
			git -C "$ROOT" push -q origin "refs/tags/$TAG" ||
				echo "    $TAG not pushed: git push origin refs/tags/$TAG" >&2
		else
			echo "    $TAG not made: tag $HEAD_AT_START by hand" >&2
		fi
		;;
esac
