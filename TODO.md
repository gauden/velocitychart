# Velocity Chart TODO

## Phase 1 - Project Scaffold

- [x] Define client-side PyScript architecture
- [x] Add static app entrypoint
- [x] Add focused Python data/velocity helpers
- [x] Add first demo CSV from a public World Bank indicator

## Phase 2 - TDD Core Logic

- [x] Test wide CSV parsing
- [x] Test long CSV parsing
- [x] Test year-on-year velocity calculation
- [x] Test configurable country sorting

## Phase 3 - Product UI

- [x] Add CSV upload and demo loading
- [x] Add column/format controls
- [x] Add palette controls
- [x] Add sorting controls for name, start, end, and selected year
- [x] Add SVG velocity wheel rendering
- [x] Add exportable SVG output

## Phase 4 - Verification and Publishing

- [x] Run automated tests
- [x] Smoke-test static HTTP shell locally
- [ ] Full PyScript runtime smoke test in a regular browser
- [x] Create private GitHub repository
- [x] Push implementation and provide private GitHub link

## Phase 5 - Radial Series Redesign

- [x] Make each radial series represent one entity
- [x] Make time run from the center outward
- [x] Replace custom palettes with ColorBrewer diverging schemes
- [x] Add ColorBrewer attribution
- [x] Verify and publish redesign

## Phase 6 - Axis Gap Refinement

- [x] Reserve a top vertical spoke for year labels
- [x] Enlarge and bold entity labels
- [x] Remove circular tick guides
- [x] Verify and publish axis gap refinement

## Phase 7 - Label Controls and Legend Direction

- [x] Add center title text control
- [x] Add center subtitle text control
- [x] Add negative and positive legend endpoint labels
- [ ] Verify and publish label controls

## Phase 8 - Tablet Layout Repair

- [x] Lower responsive breakpoint below iPad landscape widths
- [x] Use percentage shell width instead of viewport-width shell sizing
- [x] Add dynamic viewport height fallback
- [x] Verify and publish tablet layout repair

## Phase 9 - Spoke Gap Slider

- [x] Replace numeric spoke gap input with range slider
- [x] Add live spoke gap value readout
- [x] Re-render chart while slider moves
- [ ] Verify and publish spoke gap slider
