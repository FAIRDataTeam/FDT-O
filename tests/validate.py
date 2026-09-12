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

    print("\nALL AS EXPECTED" if ok_all else "\nFAILURES ABOVE")
    sys.exit(0 if ok_all else 1)

if __name__ == "__main__":
    main()
