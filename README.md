# FDT-O — the FAIR Data Train Ontology

This ontology describes the elements of the FAIR Data Train (FDT) and their relations. It
serves as a reference model to annotate the metadata content of the FDTs.

**Version 3.0.0** (13 September 2026) renames the Train Garage to the Train Depot, makes
`fdt-o:Train` abstract and drops `fdt-o:Train ⊑ odrl:Asset` (ADR-029). It is breaking, and
deliberately so: no `w3id.org` redirect publishes these IRIs yet, so the rename will never be
cheaper. No aliases are kept — a graph written against v2 must be rewritten.
Version 2.0.0 (12 September 2026) merged the FDT-O v2 delta and settled the namespace.
The structural vocabulary lives here; the data-space layer on top of it — the ODRL profile,
the run-description vocabulary, the network vocabulary, the visit protocol — lives in
[`fdt-commons`](https://github.com/FAIRDataTeam/fdt-commons).

## Layout

| Path | What it holds |
|---|---|
| `ontology/fdt-o.ttl` | **the ontology** — v3, in one namespace |
| `ontology/fdt-o-v2-delta.ttl` | the v2 delta on its own, historical; nothing validates against it |
| `shapes/` | SHACL shapes: `TrainShape`, `PayloadShape`, `DatastationShape`, `HostedDatasetAndCatalogShapes`, `MetadataRecordShape`, and two illustrative example shapes |
| `example-instances/` | valid instances, and `invalid/` counter-examples that must fail |
| `tests/validate.py` | the checker (pySHACL) |
| `legacy/` | the v0.3 prototype: `fdt-ontology.owl` and the `fdp-api` sidecar, superseded by `ontology/fdt-o.ttl` |

## The namespace

FDT-O's terms are in **`https://w3id.org/fdt/fdt-o#`**, where the prototype declared them.
The ontology IRI is `https://w3id.org/fdt/fdt-o` and its version IRI
`https://w3id.org/fdt/fdt-o/3.0.0`, so the term namespace is the ontology IRI plus `#` — what
a dereferencing consumer expects.

This needed settling. The prototype declared its 54 terms here, while **every** SHACL shape
and example instance — in this repository, in the v2 delta and in `fdt-commons` — used
`https://w3id.org/fdt#`. The two namespaces had no term in common, so the shapes constrained
terms the ontology did not declare, and no validator could report it: a `sh:targetClass`
naming an undeclared class simply selects no focus nodes, and SHACL answers "conforms"
because it has nothing to look at. This was finding 1 of the `fdt-commons` probe, which
understated it as "two namespaces".

Settled on 12 September 2026 by keeping the ontology's own namespace and rebinding the
shapes, examples, vocabularies and contexts to it. `https://w3id.org/fdt#` was used for
nothing but the `fdt-o:` prefix, so every expanded term IRI changed in the same way and
nothing needed deprecating: the prototype has no real consumers, so the terms moved under the
namespace rather than the namespace moving to meet them. No equivalence bridges are required.

`tests/validate.py` now compares the two vocabularies directly — every `fdt-o:` term the
shapes reference must be declared by the ontology — so this cannot recur silently. It reports
42 referenced, 71 declared, 0 undeclared; before the merge the overlap was **zero**.

## What v3 changes

ADR-029.

- **The Train Garage is the Train Depot**, in the ontology and not only in the product name.
  `fdt-o:GarageCatalog` → `fdt-o:DepotCatalog`. `fdt-commons` follows with
  `fdt-p:trainGarage` → `fdt-p:trainDepot` and `fdt-net:GarageRole` → `fdt-net:DepotRole`.
- **`fdt-o:Train` is abstract.** A train is typed by the class that says what it is —
  `fdt-o:SPARQLTrain`, `fdt-o:DockerTrain`, `fdt-o:FHIRTrain` — and `fdt-o:Train` is entailed,
  never asserted alongside. OWL has no abstract classes, so the ontology states the intent
  with `dash:abstract true` and a scope note, and `:TrainShape` is what enforces it: a node
  whose only train type is `fdt-o:Train` is rejected.
- **A train is not a subclass of `odrl:Asset`; it plays that role.** `odrl:target` has range
  `odrl:Asset`, so being the target of an offer, request or agreement gives a train the role
  exactly where access conditions apply. ADR-020 is unchanged in substance and more precise
  about how a train is an asset.
- **The fixtures got shorter.** `a fdt-o:Train, fdt-o:SPARQLTrain, odrl:Asset` is now
  `a fdt-o:SPARQLTrain`: the other two are entailed.

Removing that redundant `a fdt-o:Train` is what exposed **`fdt-commons` finding 49**. SHACL
resolves `sh:targetClass` and `sh:class` through `rdfs:subClassOf*` **in the data graph**, and
this checker had been loading the ontology into the *shapes* graph. Every train shape had been
selecting its focus nodes purely by the explicit type, and with that gone they selected
nothing and reported `conforms` — a train missing its payload, title, output and theme
validated clean. `tests/validate.py` now mixes the named-class subclass hierarchy into the
data graph, and `invalid/concrete-train-without-payload.ttl` fails if that regresses.

**Finding 50** came out of the same pass: `tests/validate.py` now also counts the focus nodes
each FDT shape selects and fails when one selects none. `:LinkageStationShape` had never had
an instance to check, and `example-instances/linkage-station.ttl` is the one it was missing.

## What v2 changed

Driven by findings 1–5 of `fdt-commons/FINDINGS.md` and by ADR-011, ADR-013, ADR-017,
ADR-020 (as amended), ADR-022 and ADR-024.

- **Trains are executable assets, never datasets** (ADR-020 as amended).
  `fdt-o:Train ⊑ dcat:Resource` and `owl:disjointWith dcat:Dataset` (v2 also declared
  `⊑ odrl:Asset`; v3 drops it, below).
  `TrainShape` no longer closes the `rdf:type` list — it requires at least one concrete
  train class and forbids `dcat:Dataset` and `dcat:distribution`. `fdt-o:hasPayload` is
  required: a train without an artefact cannot be run. `fdt-o:supportsCoordination` is new,
  and query and API trains may not be `Choreographed` (ADR-013).
- **`dcat:Dataset` no longer does several jobs.** `fdt-o:HostedDataset ⊑ dcat:Dataset` for
  data a station hosts, with `fdt-o:StationCatalog` and `fdt-o:DepotCatalog ⊑ dcat:Catalog` (v2 called the
  latter `GarageCatalog`).
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
- **`fdt-o:capacityClass` and the three capacity individuals are declared** (`fdt-commons`
  finding 16). `StationSelfDescriptionShape` restricted `fdt-o:capacityClass` to
  `sh:in (CapacityS CapacityM CapacityL)` and a fixture used it, but neither the property
  nor the individuals existed anywhere: `sh:in` enumerates permitted values and never asks
  whether they are declared.
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
