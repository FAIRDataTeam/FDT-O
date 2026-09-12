#!/usr/bin/env python3
"""FDT-O v2 validation.

1. The v2 example instances conform to the v2 shapes.
2. Each invalid example fails on the rule it is meant to break (tests/expectations.json).
3. Cross-check: the fdt-commons probe examples (../fdt-commons/examples) conform to the FDT-O v2
   shapes — the "zero divergence" target of the 11 Sep 2026 amendment.

The merged ontology (ontology/fdt-o.ttl) is loaded into the shapes graph so its subclass
axioms (Train ⊑ odrl:Asset, HostedDataset ⊑ dcat:Dataset, LinkageStation ⊑ DataStation, …)
are honoured. Requires pySHACL and rdflib; there is no subset-validator fallback, because
the one the probe used accepted Turtle no conformant parser accepts (fdt-commons
FINDINGS.md, finding 12).
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

def run_pyshacl(data_files, shape_files):
    from rdflib import Graph
    from pyshacl import validate
    d, s = Graph(), Graph()
    for f in data_files: d.parse(f, format="turtle")
    for f in shape_files: s.parse(f, format="turtle")
    conforms, _, text = validate(d, shacl_graph=s, inference="rdfs", advanced=True)
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


def main():
    ok_all = True
    with open(os.path.join(HERE, "expectations.json")) as f: expect = json.load(f)

    conforms, text, tool = validate(VALID, SHAPES)
    print(f"[{tool}] v2 example instances ({len(VALID)} files): {'conforms' if conforms else 'NON-CONFORMING'}")
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
        print(f"[{tool}] fdt-commons probe examples ({len(COMMONS_EXAMPLES)} files) against FDT-O v2 shapes: "
              f"{'conforms — zero divergence' if conforms else 'DIVERGENCE'}")
        if not conforms: print(text); ok_all = False
    else:
        print("fdt-commons examples not found next to this folder — cross-check skipped")

    ok_all &= check_shape_terms_are_declared()

    print("\nALL AS EXPECTED" if ok_all else "\nFAILURES ABOVE")
    sys.exit(0 if ok_all else 1)

if __name__ == "__main__":
    main()
