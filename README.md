# FDT-O — the FAIR Data Train Ontology

This ontology describes the elements of the FAIR Data Train (FDT) and their relations. It
serves as a reference model to annotate the metadata content of the FDTs.

**Version 2.0.0** (12 September 2026) merges the FDT-O v2 delta and settles the namespace.
The structural vocabulary lives here; the data-space layer on top of it — the ODRL profile,
the run-description vocabulary, the network vocabulary, the visit protocol — lives in
[`fdt-commons`](https://github.com/FAIRDataTeam/fdt-commons).

## Layout

| Path | What it holds |
|---|---|
| `ontology/fdt-o.ttl` | **the ontology** — the merged v2, in one namespace |
| `ontology/fdt-o-v2-delta.ttl` | the v2 delta on its own, kept for traceability |
| `shapes/` | SHACL shapes: `TrainShape`, `PayloadShape`, `DatastationShape`, `HostedDatasetAndCatalogShapes`, `MetadataRecordShape`, and two illustrative example shapes |
| `example-instances/` | valid instances, and `invalid/` counter-examples that must fail |
| `tests/validate.py` | the checker (pySHACL) |
| `legacy/` | the v0.3 prototype: `fdt-ontology.owl` and the `fdp-api` sidecar, superseded by `ontology/fdt-o.ttl` |

## The namespace, and why it changed

The prototype declared its terms under `https://w3id.org/fdt/fdt-o#`, while **every** SHACL
shape and example instance — in this repository, in the v2 delta and in `fdt-commons` — used
`https://w3id.org/fdt#`. The two namespaces had no term in common, so the shapes constrained
terms the ontology did not declare, and no validator could notice: they simply found nothing
to check. This was finding 1 of the `fdt-commons` probe.

v2 settles on **`https://w3id.org/fdt#`**, the namespace already in use. All 54 prototype
terms (40 classes, 14 properties) are declared there. The retired IRIs are kept as
`owl:equivalentClass` / `owl:equivalentProperty` bridges marked `owl:deprecated`, each with
a `skos:historyNote`, so data written against the prototype keeps its meaning and resolves
to the current term. Nothing published against the old namespace breaks.

## What v2 changes

Driven by findings 1–5 of `fdt-commons/FINDINGS.md` and by ADR-011, ADR-013, ADR-017,
ADR-020 (as amended), ADR-022 and ADR-024.

- **Trains are executable assets, never datasets** (ADR-020 as amended).
  `fdt-o:Train ⊑ odrl:Asset, dcat:Resource` and `owl:disjointWith dcat:Dataset`.
  `TrainShape` no longer closes the `rdf:type` list — it requires at least one concrete
  train class and forbids `dcat:Dataset` and `dcat:distribution`. `fdt-o:hasPayload` is
  required: a train without an artefact cannot be run. `fdt-o:supportsCoordination` is new,
  and query and API trains may not be `Choreographed` (ADR-013).
- **`dcat:Dataset` no longer does several jobs.** `fdt-o:HostedDataset ⊑ dcat:Dataset` for
  data a station hosts, with `fdt-o:StationCatalog` and `fdt-o:GarageCatalog ⊑ dcat:Catalog`.
  A train's declared inputs and outputs stay plain `dcat:Dataset` descriptions, so hosted-data
  rules no longer fire on them.
- **Controllers have a term.** `fdt-o:DataController ⊑ foaf:Agent` (organisation or natural
  person, ADR-011) and `fdt-o:hasDataController` on hosted datasets. `fdt-o:isControlledBy`
  keeps its prototype meaning — station owner, train owner.
- **Station types.** `fdt-o:LinkageStation` and `fdt-o:AlignmentStation ⊑ fdt-o:DataStation`;
  `fdt-o:JoinKey`, `fdt-o:joinKey`, `fdt-o:pseudonymSpace`. A station is typed with its
  class rather than carrying a `stationType` property.
- **Two interaction mechanisms**, `fdt-inst:IdentifierTranslation` (ADR-022) and
  `fdt-inst:VocabularyAlignment` (ADR-024), each with the same-named class under
  `fdt-o:InteractionMechanism` that FDT-O's mechanism individuals use.
- **`PayloadShape` is valid SHACL again.** The `sh:or` of "download URL or inline content"
  sat inside a `sh:property` with no `sh:path`, which conformant processors reject; it now
  sits on the node shape. `fdt-o:payloadMediaType` is declared and required, and
  `fdt-o:artifactDigest` (`sha256:<64 hex>`) is added.
- Shape IRIs moved from `http://fairdatapoint.org/` — a copy-paste leftover from the FDP
  shapes — to `https://w3id.org/fdt/shapes#`.
- `shapes/exampleDataRequirementShape.ttl` and `shapes/exampleDatasetOutputShape.ttl` were
  not parseable: `@prefix` directives without their terminating `.`. Fixed.
- `example-instances/sparql-train-payload.ttl` carried a GitHub access token in the query
  string of its download URL. Removed. The token is a long-expired `GHSAT0` App token, but
  it remains in this repository's history.

## Validating

```sh
pip install -r requirements.txt
python3 tests/validate.py
```

Three passes: the example instances conform to the shapes; each `example-instances/invalid/`
file fails on the rule it was written to break; and the `fdt-commons` fixtures conform to
these shapes with zero divergence — the cross-check that keeps the two repositories honest.
The last pass needs a `fdt-commons` checkout beside this one.

## Licence

MIT for the repository (`LICENSE`); the ontology itself is CC BY 4.0, as its
`dct:license` states.
