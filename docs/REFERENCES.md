# References

External literature, product documentation and field footage that
informs the mix presets, supplier catalog and process choices in The
Mix Sheet. Curated, not exhaustive — entries earn their place by
having shaped a concrete decision in the codebase or roadmap.

## Datasheets

Vendor product datasheets live under
[`datasheets/`](datasheets/), grouped by material role.

| Path | Product | Role |
|------|---------|------|
| [`datasheets/uhpc/datasheet_moertelshop_cement.pdf`](datasheets/uhpc/datasheet_moertelshop_cement.pdf) | Mörtelshop Nanodur-based premix cement | UHPC binder |
| [`datasheets/uhpc/datasheet_moertelshop_pce_375.pdf`](datasheets/uhpc/datasheet_moertelshop_pce_375.pdf) | Mörtelshop PCE 375 superplasticizer | UHPC flow / w/c reduction |
| [`datasheets/uhpc/datasheet_dyckerhoff_nanodur_compound_5941.pdf`](datasheets/uhpc/datasheet_dyckerhoff_nanodur_compound_5941.pdf) | Dyckerhoff Nanodur Compound 5941 | Binder spec sheet (manufacturer source) |
| [`datasheets/uhpc/guide_dyckerhoff_nanodur_instructions.pdf`](datasheets/uhpc/guide_dyckerhoff_nanodur_instructions.pdf) | Dyckerhoff Nanodur Instructions (EN) | Lab + production mixing, working time, casting protocol |
| [`datasheets/uhpc/guide_dyckerhoff_uhpc_machinebau.pdf`](datasheets/uhpc/guide_dyckerhoff_uhpc_machinebau.pdf) | Dyckerhoff — UHPC in Bautechnik und Maschinenbau (BWI 1/2012, DE) | Case studies for machine frames in UHPC |
| [`datasheets/aggregates/datasheet_moertelshop_durigid.pdf`](datasheets/aggregates/datasheet_moertelshop_durigid.pdf) | Mörtelshop Durigid | Hard aggregate (UHPC / mortar) |
| [`datasheets/aggregates/datasheet_moertelshop_aeropor.pdf`](datasheets/aggregates/datasheet_moertelshop_aeropor.pdf) | Mörtelshop Aeropor | Lightweight aggregate |
| [`datasheets/epoxy/datasheet_rg_epoxy_l_hardener_gl2.pdf`](datasheets/epoxy/datasheet_rg_epoxy_l_hardener_gl2.pdf) | R&G Epoxy L + Hardener GL2 | Epoxy matrix (epoxy granite, top layer) |

Datasheets are reproduced for engineering reference. Authoritative
versions remain on the suppliers' sites.

## Papers and theses

Local copies live under [`papers/`](papers/).

- **Sagmeister, B. — Habilitationsschrift on UHPC (RPTU Kaiserslautern, KLUEDO).**
  Local: [`papers/sagmeister_habilitation_uhpc.pdf`](papers/sagmeister_habilitation_uhpc.pdf) ·
  Source: [KLUEDO](https://kluedo.ub.rptu.de/frontdoor/deliver/index/docId/5877/file/_Habilitationsschrift_Sagmeister_KLUEDO.pdf).
  Reference work on Nanodur-based UHPC mix design, rheology and
  mechanical properties. Used to sanity-check mix ratios and curing
  assumptions.
- **MDPI *Materials* 14(15):4260 — UHPC study.**
  Local: [`papers/mdpi_materials_14_4260.pdf`](papers/mdpi_materials_14_4260.pdf) ·
  Source: [mdpi.com/1996-1944/14/15/4260](https://www.mdpi.com/1996-1944/14/15/4260).
  Open-access study on UHPC formulation and performance. Cross-reference
  for aggregate gradation and superplasticizer dosing.

## Manufacturer technical literature

- **Dyckerhoff Nanodur — product family hub.**
  [dyckerhoff.com/en/nanodur](https://www.dyckerhoff.com/en/nanodur).
  Source of record for the Nanodur compound binder underlying the
  Mörtelshop UHPC premix. The three practical PDFs (compound spec,
  mixing instructions, machine-frame applications) are mirrored under
  [`datasheets/uhpc/`](datasheets/uhpc/); additional theoretical and
  historical papers remain on the Dyckerhoff site.

## Video

- **Durcrete YouTube channel.**
  [@durcrete](https://www.youtube.com/@durcrete/videos). UHPC casting,
  mold making and finishing footage from a working UHPC fabricator.
  - **UHPC mold making — specific reference.**
    [`watch?v=nDnFl_TwbCU`](https://www.youtube.com/watch?v=nDnFl_TwbCU).
    Mold construction and surface treatment for UHPC pours. Informs
    the experiment plan for adhesion testing.
- **CNC machine frame — UHPC build walkthrough.**
  [`youtu.be/NxnTf3VPXkI`](https://youtu.be/NxnTf3VPXkI?si=ovQVJkrKsUj9NnVa).
  End-to-end frame casting in UHPC. Process reference for the target
  application of the calculator.
- **CNC machine frame — epoxy granite build.**
  [`watch?v=ZuQmm2X9wd4`](https://www.youtube.com/watch?v=ZuQmm2X9wd4).
  Comparable build using epoxy granite. Useful for contrasting the two
  matrix systems supported by Mix Sheet.
