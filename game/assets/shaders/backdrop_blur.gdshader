// The menu's backdrop (`Q163`, the user's ask: "background blur/shadowing in the
// menu so that the texts are more readable"): the frame behind the rect, read
// back blurred from the screen's mipmaps and tinted toward `tint`, so bare
// lettering sits on a soft dark field rather than on the city's hard edges.
// `fade_from` fades it out toward the rect's right edge — HOME's side panel —
// and 1.0 leaves it whole, for a sheet over the full screen.
//
// A mip read, not a kernel: one sample a pixel, which a phone can afford over
// the whole screen. A renderer with no screen mips reads the sharp frame and
// the tint alone does the work.
shader_type canvas_item;

uniform sampler2D screen : hint_screen_texture, filter_linear_mipmap;
// The mip level the frame is read at: each level halves the resolution.
uniform float blur_lod = 3.5;
// The colour the blurred frame is pulled toward, by its alpha.
uniform vec4 tint : source_color = vec4(0.0, 0.0, 0.0, 0.6);
// Where along `UV.x` the backdrop starts to fade out; 1.0 is no fade.
uniform float fade_from = 1.0;

void fragment() {
	vec3 behind = textureLod(screen, SCREEN_UV, blur_lod).rgb;
	// Guarded: `smoothstep` with equal edges is undefined in GLSL.
	float shown = fade_from < 1.0 ? 1.0 - smoothstep(fade_from, 1.0, UV.x) : 1.0;
	COLOR = vec4(mix(behind, tint.rgb, tint.a), shown);
}
