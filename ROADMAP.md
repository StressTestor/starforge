# roadmap

where starforge could go after v5. honest about what's a clean win and what's a research detour.

## the one decision that gates half of this

v5's identity is the seamless loop. every animating term is `phase * tau`, so frame N meets frame 0, and the gif/mp4/webm all loop. anything with a beginning, middle, and end (a merger, a flythrough) is a different product. before building any motion feature, pick one: loops, films, or both. that fork decides whether the timeline ideas below are even compatible with the export and curator pipeline. it stays open on purpose.

## v6 candidates, by payoff

### tractable, on-architecture (do these first)

the subject seam is in place and lensed-galaxy proved the pattern. more subjects that reuse the single-center lensing are cheap:

- **neutron star / pulsar**: no disk, a sharp hot surface, two magnetic-pole hotspots, a lighthouse beam that sweeps. loop-safe on `phase`.
- **wormhole**: the two-mouth look. gather a *different* background field through a stronger deflection so the throat shows somewhere else. reuses the existing gather, no new physics.

other clean wins:

- **smarter curator.** the `Curator` interface shipped in v4; only the heuristic exists. a learned or CLIP aesthetic ranker drops in without touching reproducibility, because generation stays the source of truth and the chosen seed still re-renders byte-identically. this is the honest way to make "the lab picks the best" mean the best, not the contrastiest.
- **cross-subject collection.** the batch sweep is single-subject. let it sweep subjects too and rank a mixed gallery.

### needs the loop-vs-film decision first

- **timeline / merger.** inspiral -> merger -> ringdown. only coherent as a *film*: a non-looping export mode with the loop exporters left untouched, the contact sheet becoming a storyboard, and the curator scoped to non-timeline subjects (it ranks one coherent composition, not a narrative). real work, and it's gated on the decision above.

### research detour (isolate or skip)

- **binary-merger subject.** the honest version needs true two-center lensing, where each hole bends the other's disk. there's no closed-form fold map for that, and ray-marching breaks the deterministic precompute architecture. a quick two-LUT fake renders two unrelated holes with no tidal bridge between them, which is exactly the hand-faked look this whole project exists to avoid. only worth doing behind a separate ray-tracing backend that never touches the v5 LUT/fold code, and not at the cost of the tractable wins above.

## non-negotiables for anything new

- determinism stays byte-identical and the RNG-order lock stays green. any new genome field draws AFTER the existing sequence, never inside it.
- every new subject ships with determinism, finiteness, and frame-stability tests, and the black-hole path stays untouched.
