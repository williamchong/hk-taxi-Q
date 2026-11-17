// A traffic car fading in where it was placed in view, or out where it leaves
// in view (`Q214`): `INSTANCE_CUSTOM.a`'s bits from 64 up, how far out it is in
// sevenths — 0 drawn whole, so a parked vehicle and a tram, which write none,
// are whole. Must match `FADE_BIT` and `FADE_STEPS` in `vehicle_body_batch.gd`.
// ⚠️ **Dithered, never blended**: the car stays an opaque draw — no sort, no
// second pass on the Mobile renderer — and a pixel is dropped against a 4×4
// ordered pattern. Only the batch has the `discard`; the player's car never
// fades and keeps early depth.
// Shared by `vehicle_body.gdshader` and `vehicle_outline.gdshader` (`Q248`), so
// a car's line leaves on the same pixels as the car.
const float FADE_BIT = 64.0;
const float FADE_STEPS = 7.0;
const float FADE_PATTERN[16] = float[](
	0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0
);
varying flat float faded;

// How far out `INSTANCE_CUSTOM.a`'s rounded `bits` say the car is, 0 to 1.
float fade_of(float bits) {
	return mod(floor(bits / FADE_BIT), FADE_STEPS + 1.0) / FADE_STEPS;
}

// Whether the fade drops the pixel at `at` (`FRAGCOORD.xy`).
bool fade_drops(float fade, vec2 at) {
	ivec2 cell = ivec2(at) % 4;
	return fade > 0.0 && (FADE_PATTERN[cell.y * 4 + cell.x] + 0.5) / 16.0 < fade;
}
