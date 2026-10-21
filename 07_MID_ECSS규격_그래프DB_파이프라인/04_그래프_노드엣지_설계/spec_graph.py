"""규격 그래프 노드·엣지 설계와 질의 예제 (인메모리 그래프).

실제 적재 대상은 PostgreSQL + Apache AGE이며, README에 같은 질의의 Cypher를 함께 적었다.
노드·관계 데이터는 예시다.
"""

from collections import defaultdict, deque

NODE_TYPES = {"Specification", "Requirement", "ComponentFamily", "TestMethod",
              "Qualification", "ProjectClass", "PADSection", "DocumentRevision"}
EDGE_TYPES = {"REFERENCES", "APPLIES_TO", "REQUIRES", "SUPERSEDES",
              "RELATED_TO", "USED_FOR_PAD", "VALID_FOR_CLASS"}


class Graph:
    def __init__(self):
        self.nodes: dict[str, str] = {}
        self.out: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.inc: dict[str, list[tuple[str, str]]] = defaultdict(list)

    def node(self, nid: str, ntype: str) -> None:
        assert ntype in NODE_TYPES, ntype
        self.nodes[nid] = ntype

    def edge(self, src: str, etype: str, dst: str) -> None:
        assert etype in EDGE_TYPES and src in self.nodes and dst in self.nodes, (src, etype, dst)
        self.out[src].append((etype, dst))
        self.inc[dst].append((etype, src))

    def neighbors(self, nid: str, etype: str, reverse: bool = False) -> list[str]:
        edges = self.inc[nid] if reverse else self.out[nid]
        return [n for t, n in edges if t == etype]


def build() -> Graph:
    g = Graph()
    for nid, t in [
        ("ESCC-3009", "Specification"), ("ESCC-3009-001", "Specification"),
        ("ESCC-2269000", "Specification"), ("ESCC-22900", "Specification"),
        ("ESCC-3009@4", "DocumentRevision"), ("ESCC-3009@5", "DocumentRevision"),
        ("ESCC-22900@5", "DocumentRevision"),
        ("Capacitor", "ComponentFamily"), ("TID", "TestMethod"),
        ("Evaluation", "Qualification"), ("Class1", "ProjectClass"),
        ("PAD-5-Testing", "PADSection"), ("REQ-3009-4.3", "Requirement"),
    ]:
        g.node(nid, t)
    for s, e, d in [
        ("ESCC-3009", "APPLIES_TO", "Capacitor"),
        ("ESCC-3009-001", "APPLIES_TO", "Capacitor"),
        ("ESCC-3009-001", "REFERENCES", "ESCC-3009"),
        ("ESCC-3009", "REFERENCES", "ESCC-2269000"),
        ("ESCC-2269000", "REFERENCES", "ESCC-22900"),
        ("ESCC-3009@4", "RELATED_TO", "ESCC-3009"), ("ESCC-3009@5", "RELATED_TO", "ESCC-3009"),
        ("ESCC-3009@5", "SUPERSEDES", "ESCC-3009@4"),
        ("ESCC-22900@5", "RELATED_TO", "ESCC-22900"),
        ("ESCC-3009", "VALID_FOR_CLASS", "Class1"),
        ("REQ-3009-4.3", "RELATED_TO", "ESCC-3009"),
        ("REQ-3009-4.3", "REQUIRES", "Evaluation"),
        ("ESCC-22900", "RELATED_TO", "TID"),
        ("ESCC-3009", "USED_FOR_PAD", "PAD-5-Testing"),
        ("ESCC-22900", "USED_FOR_PAD", "PAD-5-Testing"),
    ]:
        g.edge(s, e, d)
    return g


def latest_revision(g: Graph, spec: str) -> str | None:
    revs = [n for n in g.neighbors(spec, "RELATED_TO", reverse=True) if g.nodes[n] == "DocumentRevision"]
    superseded = {d for r in revs for d in g.neighbors(r, "SUPERSEDES")}
    latest = [r for r in revs if r not in superseded]
    return latest[0] if len(latest) == 1 else None  # 0개 또는 여러 개면 판단 불가 → 사람 검토


def reference_chain(g: Graph, start: str) -> list[list[str]]:
    """REFERENCES를 따라가며 참조 경로를 모두 나열 (BFS, 순환 방지)."""
    paths, q = [], deque([[start]])
    while q:
        path = q.popleft()
        nxt = [n for n in g.neighbors(path[-1], "REFERENCES") if n not in path]
        if not nxt and len(path) > 1:
            paths.append(path)
        q.extend(path + [n] for n in nxt)
    return paths


def main() -> None:
    g = build()
    print(f"노드 {len(g.nodes)}개 / 엣지 {sum(map(len, g.out.values()))}개\n")

    print("Q1. Capacitor 부품군에 적용되는 규격과 최신 Revision은?")
    for spec in g.neighbors("Capacitor", "APPLIES_TO", reverse=True):
        print(f"   {spec:<15} 최신: {latest_revision(g, spec) or '등록된 Revision 없음 → 사람 검토'}")

    print("\nQ2. ESCC-3009-001을 따를 때 함께 봐야 하는 문서 (참조 체인)")
    for path in reference_chain(g, "ESCC-3009-001"):
        print("   " + " → ".join(path))

    print("\nQ3. PAD '5. 시험' 섹션 작성에 쓰이는 규격과 관련 시험 방법")
    for spec in g.neighbors("PAD-5-Testing", "USED_FOR_PAD", reverse=True):
        methods = [n for n in g.neighbors(spec, "RELATED_TO") if g.nodes[n] == "TestMethod"]
        classes = g.neighbors(spec, "VALID_FOR_CLASS")
        print(f"   {spec:<15} 시험방법 {methods or '-'}  유효 Class {classes or '미지정'}")


if __name__ == "__main__":
    main()
