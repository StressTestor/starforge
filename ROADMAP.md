# roadmap

where starforge could go after v7. honest about what's a clean win and what's a research detour.

## shipped in v7

- **the selection studio** (`--studio`): an offline `studio.html` with a Pareto frontier, per-subject de-biased ranking, exposed metrics, a raw-vs-de-biased toggle, and pin/export. read-only over the rendered artifacts, so determinism is untouched.
- **why it mattered:** a test confirmed the real bottleneck was selection, not pixels. the v6 scalar is a contrast meter, so cross-subject ranking buried every soft subject (all four black holes ranked 1-4, all five galaxies last). per-subject normalization fixes it; the frontier surfaces what no scalar can.

## shipped in v6

- **neutron-star / pulsar** and **wormhole** subjects, both reusing the single-center lensing, each on its own rng stream so the locked black-hole genome never moves.
- **studio curator** (`--curator studio`): a deterministic, offline ranker that picks for a clear focal subject over raw contrast.
- **cross-subject collection** (`--cross-subject`): the batch sweep ranks a mixed gallery across every subject; a single-subject sweep stays byte-identical.

what's left is the genuinely hard stuff below.

## the one decision that gates half of this

the seamless loop is starforge's identity. every animating term is `phase * tau`, so frame N meets frame 0, and the gif/mp4/webm all loop. anything with a beginning, middle, and end (a merger, a flythrough) is a different product. before building any motion feature, pick one: loops, films, or both. that fork decides whether the timeline ideas below are even compatible with the export and curator pipeline. it stays open on purpose.

## v8 candidates, by payoff

### the pixel floor (a deliberate, separate decision)

this is the one that changes pixels and re-blesses the golden, so it is its own call, not bundled under a feature flag:

- **dither + 16-bit intermediate.** the one real residual fidelity gap is 8-bit banding in smooth low-gradient regions. deterministic ordered/blue-noise dither over a 16-bit intermediate fixes it. it would be the first deliberate pixel change since v4, so it supersedes the v4-v7 byte-identity rather than preserving it — worth doing, but only as an explicit version boundary.
- **blackbody spectral pass.** map temperature -> Planck spectrum -> sRGB, scoped to the subjects where it is physically apt (black-hole disk, neutron-star hotspots), not the galaxy/wormhole skies. ~50 lines on `_temperature_shift`, frame-invariant, zero genome fields.

### tractable, on-architecture

- **magnetar / flaring loops**: the pulsar surface plus animated magnetic-field arcs. loop-safe on `phase`, same separate-stream pattern.
- **learned curator.** the `Curator` interface has two members (`heuristic`, `studio`); a learned or CLIP aesthetic ranker still drops in without touching reproducibility. it stays out of the offline core only because it needs model weights, so it would ship as an optional extra. the studio is the honest stepping stone — it makes the case for a better ranker inspectable.

### needs the loop-vs-film decision first

- **timeline / merger.** inspiral -> merger -> ringdown. only coherent as a *film*: a non-looping export mode with the loop exporters left untouched, the contact sheet becoming a storyboard, and the curator scoped to non-timeline subjects (it ranks one coherent composition, not a narrative). real work, and it's gated on the decision above.

### research detour (isolate or skip)

- **binary-merger subject.** the honest version needs true two-center lensing, where each hole bends the other's disk. there's no closed-form fold map for that, and ray-marching breaks the deterministic precompute architecture. a quick two-LUT fake renders two unrelated holes with no tidal bridge between them, which is exactly the hand-faked look this whole project exists to avoid. only worth doing behind a separate ray-tracing backend that never touches the LUT/fold code, and not at the cost of the tractable wins above.

## non-negotiables for anything new

- determinism stays byte-identical and the RNG-order lock stays green. any new genome field draws AFTER the existing sequence, never inside it.
- every new subject ships with determinism, finiteness, and frame-stability tests, and the black-hole path stays untouched.
