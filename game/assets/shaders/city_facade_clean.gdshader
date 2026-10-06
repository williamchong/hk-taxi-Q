// The city's massing in a clean high-key idiom, drawn procedurally.
//
// A variant of `city_facade.gdshader`, reading the **same** `TEXCOORD_0` payload
// and the same surface markers — so it is a look change, not a data change, and
// swapping between the two is one `ext_resource` line in `tuning/city_facade.tres`
// with no rebuild. The measured shader is kept beside this one for that reason.
//
// ⚠️ **The complaint this answers was "the repeating window looks dull", and the
// fault was scale rather than colour.** `city_facade` draws at the *measured*
// pitch — 2.8 m storeys by 2.4 m columns — which is honest and, at 30 m from a
// moving car, about four pixels across. Too fine to read as architecture and too
// regular to read as material, so it becomes noise that the 90 m fade then
// deletes. Everything here is drawn an order of magnitude larger: a glazing
// ribbon spans a group of storeys, a bay is ~9 m, and the unit of variation is
// the **building**, not the window.
//
// The three renderer tricks doing the work, none of which needs a texture:
//
//   1. **Per-building treatment.** `fract(UV.y)` is already a stable seed
//      quantised to 1/256 by the ETL. Hashed, it picks whether a building is a
//      solid white mass, a glazed curtain wall, or an accent-banded one. Two in
//      five buildings therefore repeat *nothing*, which is what stops a block
//      reading as one wallpapered surface.
//   2. **Fresnel sky reflection.** `pow(1 - dot(NORMAL, VIEW), p)` mixed toward a
//      sky colour is a mirrored tower for a few ALU instructions — no reflection
//      probe, which `ART_DESIGN.md` lists as an anti-goal, and no cubemap.
//   3. **Grazing sky bounce on white walls.** The same term at low strength on
//      solid walls is what keeps a white city from reading as grey cardboard,
//      and it cools the shadowed faces the way the reference art does.
//
// The inputs are `city_facade`'s, unchanged and documented there in full.
// Since `P5-11` (schema 28) they arrive on two channels:
//
//   UV.x   metres along the wall — the ETL's `along_m`, the rule this shader's
//          vertex stage used to compute from world position, transcribed
//   UV.y   metres above this object's own base
//   UV2.x  `floor()` is the surface marker, `fract()` is a per-object phase
//   UV2.y  the object's row in the tile's `extras` table — unread here
//
// ⚠️ `TEXCOORD_0` is a real planar UV now, and that is the point (`Q121`): an
// artist can put a texture on it, and nothing this shader reads sits where an
// unwrap or a decal would land. `UV2` carried a packed facade-survey state
// until schema 20 (`Q102`) — a glazed verdict, a glass-tint bin and a grammar,
// each field 0 = refused → the hash — whose one producer, the vision reader,
// was withdrawn on cost; every building takes the hashed treatment that was
// always the fallback. The four grammars below are unaffected: the seed picked
// them before the survey existed.
//
// ⚠️ Like its sibling, this replaces a `BaseMaterial3D` that had
// `vertex_color_use_as_albedo` set at import, so it must apply `COLOR` itself.
//
// ⚠️ **The defaults below are this shader's first pass, not what ships**, and
// several were corrected after they were judged on real geometry — the bay is
// 5.5 m rather than 9, the glazing spans one storey rather than two, and the
// fade ends inside the LOD1 switch. `tuning/city_facade.tres` is what the city
// actually loads and is where retuning belongs (CLAUDE.md hard rule 4); these
// exist so the shader is usable on its own. Read a number here as the argument
// that produced it, and the `.tres` as the verdict.

shader_type spatial;

render_mode cull_back;

// The body (`P3-64`): shared with `city_facade_cel.gdshader`, which draws the
// same surface under a banded sun.
#include "res://assets/shaders/city_facade_clean.gdshaderinc"
