"""Analyze workflow DAG for inefficiencies.

Generic version — works with any workflow engine that exposes nodes and edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorkflowNode:
    id: str
    type: str  # e.g. "llm", "tool", "if-else", "code", "http", "transform"
    title: str = ""
    upstream: list[str] = field(default_factory=list)
    downstream: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class WorkflowDAG:
    """Directed acyclic graph representing a workflow.

    Can be constructed from any engine's JSON via ``from_dict`` by adapting
    the node/edge field mappings, or built programmatically.
    """

    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    entry_node: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: dict) -> "WorkflowDAG":
        """Build a DAG from a generic workflow JSON.

        Expects ``graph.nodes`` and ``graph.edges``, or a flat structure
        with ``nodes`` / ``edges`` at the top level.  Each node should have
        ``id`` and ``data.type`` (or just ``type``).  Each edge should have
        ``sourceId``/``targetId`` or ``source``/``target``.
        """
        dag = cls()
        graph = raw.get("graph", raw)
        nodes_list = graph.get("nodes", [])
        edges = graph.get("edges", [])

        node_map: dict[str, WorkflowNode] = {}
        for n in nodes_list:
            node = WorkflowNode(
                id=n["id"],
                type=n.get("data", {}).get("type", n.get("type", "unknown")),
                title=n.get("data", {}).get("title", n.get("title", "")),
                data=n.get("data", {}),
            )
            node_map[node.id] = node

        for edge in edges:
            src = edge.get("sourceId") or edge.get("source")
            tgt = edge.get("targetId") or edge.get("target")
            if src in node_map and tgt in node_map:
                node_map[src].downstream.append(tgt)
                node_map[tgt].upstream.append(src)

        dag.nodes = node_map
        entries = [nid for nid, n in node_map.items() if not n.upstream]
        dag.entry_node = entries[0] if entries else None
        return dag

    def llm_nodes(self) -> list[WorkflowNode]:
        """Return all nodes whose type indicates LLM usage."""
        return [n for n in self.nodes.values() if n.type in ("llm", "llm-chain", "chat-model")]

    def redundant_llm_calls(self) -> list[tuple[WorkflowNode, WorkflowNode]]:
        """Detect LLM nodes that appear to do the same work.

        Heuristic: same model provider/name and same upstream source.
        """
        llms = self.llm_nodes()
        redundant: list[tuple[WorkflowNode, WorkflowNode]] = []
        for i, a in enumerate(llms):
            for b in llms[i + 1:]:
                if (
                    a.data.get("model", {}).get("provider") == b.data.get("model", {}).get("provider")
                    and a.data.get("model", {}).get("name") == b.data.get("model", {}).get("name")
                    and set(a.upstream) == set(b.upstream)
                ):
                    redundant.append((a, b))
        return redundant

    def dead_branches(self) -> list[list[str]]:
        """Return paths that can never execute.

        A node is unreachable if it cannot be reached by walking forward from
        the workflow's entry node. Each unreachable node is returned as a
        single-node path for reporting.
        """
        if not self.entry_node or self.entry_node not in self.nodes:
            return []

        reachable: set[str] = set()
        stack = [self.entry_node]
        while stack:
            current = stack.pop()
            if current in reachable or current not in self.nodes:
                continue
            reachable.add(current)
            stack.extend(self.nodes[current].downstream)

        return [[nid] for nid in self.nodes if nid not in reachable]
