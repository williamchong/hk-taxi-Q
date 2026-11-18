// Drawing past the camera's far plane (`P3-100`, `Q249`): a region's far
// version is what the camera sees of it past the street's far plane, 400 m,
// which traffic, the parked cars and every prop cell are tuned to. Raising the
// plane to reach Kowloon was measured and refused: +70% primitives and +120
// draws a frame.
//
// So a far-shore vertex is squeezed along its own sight line into the last
// `pin_band_m` short of the plane. The squeeze is `1/z' = 1/far + c/z`, which
// is a projective map: it is one linear step on the homogeneous view position,
// so a plane stays a plane, what hid what still does, a triangle that runs
// behind the camera still clips, and every varying still interpolates as it
// would have. Only the depth written is new; fog and lighting read the true
// view position, which the engine carries on its own.
//
// ⚠️ **The whole shore shares the depth the street spends on its last
// `pin_band_m`.** A float depth buffer has room to spare there. A 24-bit one
// (the Compatibility renderer) does not: at a kilometre it cannot order two
// walls under about 35 m apart.
//
// ⚠️ `street_far_m` is the drive camera's `far` (`city_drive.tscn`), restated
// because a shader cannot read it; `verify_backdrop.gd` holds the two together,
// and holds every material that includes this to the same three numbers.

group_uniforms far_shore;
// The camera's far plane, in metres.
uniform float street_far_m = 400.0;
// How much of the street's depth, short of the plane, the far shore is drawn in.
uniform float pin_band_m = 8.0;
// The true distance that lands on the near edge of the band. Anything nearer
// lands in front of it.
uniform float pin_from_m = 500.0;

// True nearer than the street's far plane, where a region's own tiles stand:
// the far version is skipped there, so its simplified blocks never show round
// the real ones. Measured from the eye, as the streamer measures a tile, not
// along the view: off the axis a tile past the plane's reach is unloaded and
// the far version stands in for it.
bool far_shore_near(vec3 view_position) {
	return length(view_position) < street_far_m;
}

vec4 far_shore_clip(mat4 projection, vec3 view_position) {
	float c_far = pin_from_m * (street_far_m / (street_far_m - pin_band_m) - 1.0);
	return projection * vec4(view_position * street_far_m, c_far - view_position.z);
}
