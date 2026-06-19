# roadmap

where starforge could go after v6. honest about what's a clean win and what's a research detour.

## shipped in v6

the whole tractable, on-architecture bucket landed:

- **neutron-star / pulsar** and **wormhole** subjects, both reusing the single-center lensing, each on its own rng stream so the locked black-hole genome never moves.
- **studio curator** (`--curator studio`): a second deterministic, offline ranker that picks for a clear focal subject over raw contrast. the learned/CLIP ranker is still the eventual goal, but it needs a model, so it stays out of the offline core.
- **cross-subject collection** (`--cross-subject`): the batch sweep now ranks a mixed gallery across every subject; a single-subject sweep stays byte-identical.

what's left is the genuinely hard stuff below.

## the one decision that gates half of this

the seamless loop is starforge's identity. every animating term is `phase * tau`, so frame N meets frame 0, and the gif/mp4/webm all loop. anything with a beginning, middle, and end (a merger, a flythrough) is a different product. before building any motion feature, pick one: loops, films, or both. that fork decides whether the timeline ideas below are even compatible with the export and curator pipeline. it stays open on purpose.

## v7 candidates, by payoff

### tractable, on-architecture

the subject seam keeps paying off. more subjects that reuse the single-center lensing are still cheap:

- **magnetar / flaring loops**: the pulsar surface plus animated magnetic-field arcs. loop-safe on `phase`, same separate-stream pattern.
- **learned curator.** the `Curator` interface has two members now (`heuristic`, `studio`); a learned or CLIP aesthetic ranker still drops in without touching reproducibility. it stays out of the offline core only because it needs model weights, so it would ship as an optional extra, not a core dependency.

### needs the loop-vs-film decision first

- **timeline / merger.** inspiral -> merger -> ringdown. only coherent as a *film*: a non-looping export mode with the loop exporters left untouched, the contact sheet becoming a storyboard, and the curator scoped to non-timeline subjects (it ranks one coherent composition, not a narrative). real work, and it's gated on the decision above.

### research detour (isolate or skip)

- **binary-merger subject.** the honest version needs true two-center lensing, where each hole bends the other's disk. there's no closed-form fold map for that, and ray-marching breaks the deterministic precompute architecture. a quick two-LUT fake renders two unrelated holes with no tidal bridge between them, which is exactly the hand-faked look this whole project exists to avoid. only worth doing behind a separate ray-tracing backend that never touches the LUT/fold code, and not at the cost of the tractable wins above.

## non-negotiables for anything new

- determinism stays byte-identical and the RNG-order lock stays green. any new genome field draws AFTER the existing sequence, never inside it.
- every new subject ships with determinism, finiteness, and frame-stability tests, and the black-hole path stays untouched.
