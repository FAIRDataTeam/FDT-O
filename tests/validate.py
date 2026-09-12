#!/usr/bin/env python3
"""FDT-O v3 validation.

1. The example instances conform to the shapes.
2. Each invalid example fails on the rule it is meant to break (tests/expectations.json).
3. Cross-check: the fdt-commons examples (../fdt-commons/examples) conform to the FDT-O
   shapes — the "zero divergence" target of the 11 Sep 2026 amendment.
4. Every FDT shape selects at least one focus node somewhere in the corpus — a shape that
   validates nothing reports "conforms" forever (check_every_shape_is_exercised).

The class hierarchy goes into the DATA graph, which is where SHACL evaluates it. sh:targetClass
selects the SHACL instances of a class — `rdf:type/rdfs:subClassOf*` — and sh:class tests the
same path, and both are read from the data graph, never from the shapes graph. FDT-O v2 loaded
the ontology into the *shapes* graph instead, and got away with it only because every fixture
asserted `a fdt-o:Train` alongside its concrete type. Making fdt-o:Train abstract (ADR-029)
removed that assertion and exposed the consequence: :TrainShape selected nothing, and a train
with no payload, no title and no output validated cleanly. invalid/concrete-train-without-payload.ttl
is the fixture that fails if this regresses.

Only `?c rdfs:subClassOf ?d` between named classes is mixed in — not the whole ontology. The
ontology's own metadata is not instance data (mixing it in put :AgentShape onto the ontology's
three authors), and RDFS inference over its owl:Restriction superclasses injects blank nodes as
rdf:type values, which then fail the `sh:nodeKind sh:IRI` on :TrainShape's rdf:type constraint.
The subclass skeleton is exactly what the two SHACL constructs need and nothing else.

Requires pySHACL and rdflib; there is no subset-validator fallback, because the one the probe
used accepted Turtle no conformant parser accepts (fdt-commons FINDINGS.md, finding 12).
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMMONS = os.path.join(os.path.dirname(ROOT), "fdt-commons")
ONTOLOGY = os.path.join(ROOT, "ontology", "fdt-o.ttl")
SHAPES = sorted(glob.glob(os.path.join(ROOT, "shapes", "*.ttl"))) + [ONTOLOGY]
VALID = sorted(glob.glob(os.path.join(ROOT, "example-instances", "*.ttl")))
INVALID = sorted(glob.glob(os.path.join(ROOT, "example-instances", "invalid", "*.ttl")))
COMMONS_EXAMPLES = sorted(glob.glob(os.path.join(COMMONS, "examples", "*.ttl")))

def class_hierarchy():
    """`?sub rdfs:subClassOf ?super` between named classes — the path SHACL walks.

    Blank-node superclasses (the ontology's owl:Restriction axioms) are deliberately left
    out: see the module docstring.
    """
    from rdflib import Graph, URIRef
    from rdflib.namespace import RDFS

    onto, skeleton = Graph(), Graph()
    onto.parse(ONTOLOGY, format="turtle")
    for sub, sup in onto.subject_objects(RDFS.subClassOf):
        if isinstance(sub, URIRef) and isinstance(sup, URIRef):
            skeleton.add((sub, RDFS.subClassOf, sup))
    if not skeleton:
        sys.exit("ERROR: the ontology yielded no class hierarchy; every shape would select "
                 "nothing and every fixture would 'conform'.")
    return skeleton


def run_pyshacl(data_files, shape_files):
    from rdflib import Graph
    from pyshacl import validate
    d, s = Graph(), Graph()
    for f in data_files: d.parse(f, format="turtle")
    for f in shape_files: s.parse(f, format="turtle")
    conforms, _, text = validate(
        d, shacl_graph=s, ont_graph=class_hierarchy(), inference="rdfs", advanced=True)
    return conforms, text, "pySHACL"

def validate(data_files, shape_files):
    try:
        import pyshacl, rdflib  # noqa
    except ImportError as e:
        sys.exit(f"ERROR: {e}. Install the checker: pip install -r requirements.txt")
    return run_pyshacl(data_files, shape_files)


FDT_O_NS = "https://w3id.org/fdt/fdt-o#"


def check_shape_terms_are_declared():
    """Every fdt-o: term the shapes constrain must be declared by the ontology.

    This is the check that would have caught finding 1. The ontology declared its terms under
    https://w3id.org/fdt/fdt-o# while every shape used https://w3id.org/fdt# -- no term in
    common -- and SHACL reported "conforms" throughout, because a sh:targetClass naming an
    undeclared class simply selects no focus nodes. A validator cannot notice that it has
    nothing to validate; this compares the two vocabularies directly.
    """
    from rdflib import Graph
    from rdflib.namespace import OWL, RDF

    onto = Graph()
    onto.parse(ONTOLOGY, format="turtle")
    declared = {
        str(s)
        for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
                     OWL.AnnotationProperty, OWL.NamedIndividual)
        for s in onto.subjects(RDF.type, kind)
        if str(s).startswith(FDT_O_NS)
    }

    shapes = Graph()
    for f in sorted(glob.glob(os.path.join(ROOT, "shapes", "*.ttl"))):
        shapes.parse(f, format="turtle")
    for f in sorted(glob.glob(os.path.join(COMMONS, "shapes", "*.ttl"))):
        if os.path.exists(f):
            shapes.parse(f, format="turtle")

    used = {str(o) for o in shapes.objects() if str(o).startswith(FDT_O_NS)}
    used |= {str(p) for p in shapes.predicates() if str(p).startswith(FDT_O_NS)}

    missing = sorted(used - declared)
    print(f"[terms] shapes reference {len(used)} fdt-o: terms; "
          f"ontology declares {len(declared)}; undeclared: {len(missing)}")
    for m in missing:
        print(f"    UNDECLARED: {m}")
    return not missing


FDT_SHAPES_NS = "https://w3id.org/fdt/shapes#"


def check_every_shape_is_exercised():
    """Every FDT shape must select at least one focus node somewhere in the corpus.

    A SHACL shape whose target selects nothing reports "conforms" and always will. That is
    how finding 1 hid (the shapes and the ontology used different namespaces, so no
    sh:targetClass matched anything), and it is how the v2 validator hid the missing class
    hierarchy: :TrainShape was live in the sense that it existed, and dead in the sense that
    it judged nothing.

    check_shape_terms_are_declared() compares the two vocabularies and so catches a shape
    naming a class that does not exist. It cannot catch a class that exists and has no
    instances — a shape can be perfectly spelled and still be exercised by nothing at all.
    This counts focus nodes instead, over the valid and the invalid fixtures together.

    Shapes outside the FDT namespace are not counted: shapes/exampleDatasetOutputShape.ttl
    ships a shape in http://example.com/ as an illustration of what a train's declared output
    shape looks like, and it is not FDT-O's to exercise.
    """
    from rdflib import Graph
    from rdflib.namespace import RDF, RDFS, SH

    hierarchy = class_hierarchy()
    shapes = Graph()
    for f in sorted(glob.glob(os.path.join(ROOT, "shapes", "*.ttl"))):
        shapes.parse(f, format="turtle")
    data = Graph()
    for f in VALID + INVALID:
        data.parse(f, format="turtle")
    data += hierarchy

    selected = {}
    for shape, cls in shapes.subject_objects(SH.targetClass):
        if not str(shape).startswith(FDT_SHAPES_NS):
            continue
        classes = {cls} | set(hierarchy.transitive_subjects(RDFS.subClassOf, cls))
        nodes = {n for c in classes for n in data.subjects(RDF.type, c)}
        selected.setdefault(str(shape), set()).update(nodes)

    dead = sorted(name for name, nodes in selected.items() if not nodes)
    print(f"[targets] {len(selected)} FDT shapes; "
          f"focus nodes in the corpus: {sum(len(n) for n in selected.values())}; "
          f"shapes selecting nothing: {len(dead)}")
    for name in dead:
        print(f"    EXERCISED BY NOTHING: {name}")
    return not dead


def main():
    ok_all = True
    with open(os.path.join(HERE, "expectations.json")) as f: expect = json.load(f)

    conforms, text, tool = validate(VALID, SHAPES)
    print(f"[{tool}] example instances ({len(VALID)} files): {'conforms' if conforms else 'NON-CONFORMING'}")
    if not conforms: print(text); ok_all = False

    for f in INVALID:
        name = os.path.basename(f)
        conforms, text, tool = validate([f], SHAPES)
        wanted = expect.get(name, [])
        hit = all(w in text for w in wanted)
        status = "non-conforming — as expected" if (not conforms and hit) else ("CONFORMS (should fail)" if conforms else "fails, but not on the expected rule")
        print(f"[{tool}] invalid/{name}: {status}")
        if conforms or not hit: print(text); ok_all = False

    if COMMONS_EXAMPLES:
        conforms, text, tool = validate(COMMONS_EXAMPLES, SHAPES)
        print(f"[{tool}] fdt-commons probe examples ({len(COMMONS_EXAMPLES)} files) against the FDT-O shapes: "
              f"{'conforms — zero divergence' if conforms else 'DIVERGENCE'}")
        if not conforms: print(text); ok_all = False
    else:
        print("fdt-commons examples not found next to this folder — cross-check skipped")

    ok_all &= check_shape_terms_are_declared()
    ok_all &= check_every_shape_is_exercised()

    print("\nALL AS EXPECTED" if ok_all else "\nFAILURES ABOVE")
    sys.exit(0 if ok_all else 1)

if __name__ == "__main__":
    main()
