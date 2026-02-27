from __future__ import annotations
from typing import Callable
from superposition import SuperPosition

NodeSchema = dict[str, Callable[[], SuperPosition]]

class Node:
    def __init__(self, schema: NodeSchema):
        self.properties: dict[str, SuperPosition] = {}
        for name, factory in schema.items():
            self.properties[name] = factory()
    
    def get(self, property_name: str) -> SuperPosition:
        return self.properties[property_name]

    def __str__(self) -> str:
        new_line = "\n\t"
        return f"Node(\n\t{new_line.join([f'{prop}: {value}' for prop, value in self.properties.items()])}\n)"

EdgeSchema =  tuple[str, str, Callable[[Node, Node], bool], bool]

class Edge:
    def __init__(self, from_type: str, to_type: str, from_index: int, to_index: int, graph: Graph) -> None:
        self.from_type = from_type
        self.to_type = to_type
        self.from_index = from_index
        self.to_index = to_index
        self.graph = graph

    def get_from(self) -> Node:
        return self.graph.nodes[self.from_type][self.from_index]
    
    def get_to(self) -> Node:
        return self.graph.nodes[self.to_type][self.to_index]

class Graph:
    def __init__(self,
                 node_schema: dict[str, NodeSchema],
                 edge_schema: dict[str, EdgeSchema]):
        self.nodes: dict[str, list[Node]] = {}
        self.edges: dict[str, list[Edge]] = {}
        for name in node_schema.keys():
            self.nodes[name] = []
        for name in edge_schema.keys():
            self.edges[name] = []
        self.node_schema = node_schema
        self.edge_schema = edge_schema
    
    def add_nodes(self, count: int, node_type: str):
        self.nodes[node_type] += [Node(self.node_schema[node_type]) for _ in range(count)]
    
    def __str__(self) -> str:
        return "\n".join(["\n".join([f"{name} {node}" for node in nodes]) for name, nodes in self.nodes.items()])