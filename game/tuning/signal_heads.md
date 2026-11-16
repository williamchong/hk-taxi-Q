# signal_heads.tres

The signal heads' material (`P3-3e`, `Q173`): `MATERIAL` in `tools/make_signal_heads.py`,
dispatched by `tools/generated_scene_import.gd` onto the authored `heads.glb`.
`signal_head.gdshader` reads the lit aspect from `INSTANCE_CUSTOM` (written by `SignalHeads` from
`SignalController.light_at`) against the lens id on `UV.x`. Never `COLOR_0` alpha, which the
Compatibility renderer reads as 0. Housing and unlit glass colours are on the vertex.

- A head left on its imported `BaseMaterial3D` draws every lens dark, so `verify_signals.gd` checks
  the dispatch by `resource_path`.
- Lit by day: the emission does not multiply `night_lights`; the night only raises it.
- `body_roughness = 0.7`: a painted cast housing, duller than a sign plate's 0.55.
- `lamp_red`, `lamp_amber`, `lamp_green`: saturated lamp colours, an art call (nothing published
  states an emitted colour). Green leans blue-green like an LED aspect.
- `lamp_emission = 3.0`: reads against the noon sky at a stop line's distance without blooming
  over the housing. The shader default is zero, so a material that forgets it shows a dark head.
- `lamp_night_gain = 2.0`: the night doubles the day's emission.
