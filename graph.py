from __future__ import annotations
from typing import Callable
from types import SimpleNamespace
from random import Random
from superposition import SuperPosition, SuperRange, SuperList
from cond import Condition
from enum import Enum

NodeSchema = dict[str, Callable[[], SuperPosition]]

class Node:
    def __init__(self, node_type: str, schema: NodeSchema, index: int, graph: Graph):
        self.properties: dict[str, SuperPosition] = {}
        for name, factory in schema.items():
            self.properties[name] = factory()
        self.type = node_type
        self.index = index
        self.graph = graph
    
    def get_degrees(self):
        degrees: dict[str, SimpleNamespace] = {}
        for edge_type, schema in self.graph.edge_schema.items():
            em = self.graph.edge_matrix[edge_type]
            if schema.from_type == self.type:
                obj = degrees.setdefault(edge_type, SimpleNamespace())
                min_degree = len([1 for val in em[self.index] if val == 1])
                max_degree = len([1 for val in em[self.index] if val != -1])
                obj.from_degree = SuperRange(min_degree, max_degree)
            if schema.to_type == self.type:
                obj = degrees.setdefault(edge_type, SimpleNamespace())
                min_degree = len([1 for row in em if row[self.index] == 1])
                max_degree = len([1 for row in em if row[self.index] != -1])
                obj.to_degree = SuperRange(min_degree, max_degree)
        return degrees
    
    def is_collapsed(self):
        return all(val.is_collapsed for val in self.properties.values())
    
    def collapse_once(self, rnd: Random) -> bool:
        not_collapsed = [val for val in self.properties.values() if not val.is_collapsed]
        if len(not_collapsed) == 0:
            return False
        rnd.choice(not_collapsed).collapse(rnd)
        return True
    
    def collapse_all(self, rnd: Random, shuffle: bool):
        not_collapsed = [val for val in self.properties.values() if not val.is_collapsed]
        if shuffle:
            rnd.shuffle(not_collapsed)
        for prop in not_collapsed:
            prop.collapse(rnd)
    
    def test_list_prop(self, prop_name: str, from_node: Node, to_node: Node, edge_schema: EdgeSchema) -> bool:
        changed = False
        prop = self.properties[prop_name]
        assert isinstance(prop, SuperList)
        self.properties[prop_name] = prop.copy()
        for val in prop.values:
            if prop.possible[val]:
                self.properties[prop_name].collapse_to(val)
                if not edge_schema.condition.check(from_node, to_node):
                    prop.possible[val] = False
                    changed = True
        self.properties[prop_name] = prop
        return changed
    
    def test_range_prop(self, prop_name: str, from_node: Node, to_node: Node, edge_schema: EdgeSchema) -> bool:
        changed = False
        prop = self.properties[prop_name]
        assert isinstance(prop, SuperRange)
        self.properties[prop_name] = prop.copy()
        valid = False
        # TODO we can use binary search here, assuming that range conditions always result in range
        for val in range(prop.min, prop.max+1):
            self.properties[prop_name].collapse_to(val)
            good = edge_schema.condition.check(from_node, to_node)
            if valid == False and good:
                if prop.min != val:
                    changed = True
                prop.min = val
                valid = True
            elif valid == True and not good:
                prop.max = val - 1
                changed = True
                break
        if not valid:
            prop.min = prop.max + 1
        self.properties[prop_name] = prop
        return changed

    def update(self, from_node: Node, to_node: Node, edge_schema: EdgeSchema):
        changed = False
        for prop_name, prop in self.properties.items():
            if prop_name in edge_schema.condition_str and not prop.is_collapsed:
                if isinstance(prop, SuperList):
                    changed = changed or self.test_list_prop(prop_name, from_node, to_node, edge_schema)
                elif isinstance(prop, SuperRange):
                    changed = changed or self.test_range_prop(prop_name, from_node, to_node, edge_schema)
        return changed

    def __str__(self) -> str:
        new_line = "\n\t"
        return f"Node[{self.index}](\n\t{new_line.join([f'{prop}: {value}' for prop, value in self.properties.items()])}\n)"

class EdgeSchema:
    def __init__(self, to_type: str, from_type: str, condition: EdgeCondition, bidirectional: bool, loops_allowed: bool, condition_str: str) -> None:
        self.to_type = to_type
        self.from_type = from_type
        self.condition = condition
        self.bidirectional = bidirectional
        self.loops_allowed = loops_allowed
        self.condition_str = condition_str

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

class EdgeSuperPosition(Enum):
    present = 1
    absent = -1
    superpos = 0

class Graph:
    def __init__(self,
                 node_schema: dict[str, NodeSchema],
                 edge_schema: dict[str, EdgeSchema],
                 global_condition: GraphCondition):
        self.nodes: dict[str, list[Node]] = {}
        self.edges: dict[str, dict[Node, set[Node]]] = {}
        self.edge_matrix: dict[str, list[list[EdgeSuperPosition]]] = {}
        for name in node_schema.keys():
            self.nodes[name] = []
        for name in edge_schema.keys():
            self.edges[name] = {}
            self.edge_matrix[name] = []
        self.node_schema = node_schema
        self.edge_schema = edge_schema
        self.global_condition = global_condition
    
    def add_nodes(self, count: int, node_type: str):
        self.nodes[node_type] += [Node(node_type, self.node_schema[node_type], i+len(self.nodes[node_type]), self) for i in range(count)]
        for edge_name, schema in self.edge_schema.items():
            if schema.from_type == node_type:
                self.edge_matrix[edge_name] += [[] for _ in range(count)]
            if schema.to_type == node_type:
                for row in self.edge_matrix[edge_name]:
                    row += [EdgeSuperPosition.superpos for _ in range(count)]
    
    def select_node(self, rnd: Random, nodes: list[Node]) -> Node:
        return rnd.choice(nodes)
    
    def consider(self, edge_name: str, u: Node, v: Node, rnd: Random, prob: float):
        # TODO bidirectional, loop, etc.
        if u == v:
            self.edge_matrix[edge_name][u.index][v.index] = EdgeSuperPosition.absent
            return
        schema = self.edge_schema[edge_name]
        assert u.type == schema.from_type, v.type == schema.to_type
        if schema.condition.check(u, v) and self.global_condition.check(self) and rnd.random() < prob:
            self.edges[edge_name][u] = self.edges[edge_name].get(u, set())
            self.edges[edge_name][u].add(v)
            self.edge_matrix[edge_name][u.index][v.index] = EdgeSuperPosition.present
        else:
            self.edge_matrix[edge_name][u.index][v.index] = EdgeSuperPosition.absent
    
    def collapse_edges(self, node: Node, rnd: Random, prob: float=0.1): # TODO how should I handle probability?
        for edge_name, schema in self.edge_schema.items():
            if schema.from_type == node.type:
                for other in self.nodes[schema.to_type]:
                    self.consider(edge_name, node, other, rnd, prob)
            # if schema.to_type == node.type:
            #     for other in self.nodes[schema.from_type]:
            #         self.consider(edge_name, other, node, rnd, prob)
    
    def propagate(self, node: Node):
        # TODO should I only update connected nodes? can things like LCA affect further away nodes?
        # TODO should I only update nodes? what about possible edges?
        # TODO should I keep flag? Or readd things to queue if they keep on changing?
        # TODO should I update both from and to?
        q: list[Node] = [node]
        flag: set[Node] = set([node])
        while len(q) > 0:
            u = q.pop(0)
            for edge_type, edges in self.edges.items():
                for v in edges.get(u, set()):
                    if not v in flag and v.update(u, v, self.edge_schema[edge_type]):
                        q.append(v)
                        flag.add(v)
                        # u.update(u, v, self.edge_schema[edge_type])
    
    def collapse(self, rnd: Random, verbose: int):
        all_nodes = [node for nodes in self.nodes.values() for node in nodes]
        while len(all_nodes) > 0:
            node = self.select_node(rnd, all_nodes)
            node.collapse_all(rnd, False)
            self.collapse_edges(node, rnd)
            self.propagate(node)
            all_nodes.remove(node)
            if verbose > 0:
                print(self)
                print("********************")
    
    def __str__(self) -> str:
        return "\n".join(["\n".join([f"{name} {node}" for node in nodes]) for name, nodes in self.nodes.items()]) + "\n" + \
            "\n".join(["\n".join([f"{name} {node.index} [{', '.join([str(other.index) for other in others])}]" for node, others in edges.items()]) for name, edges in self.edges.items()])
    
class EdgeCondition(Condition[[Node, Node]]):
    pass

class GraphCondition(Condition[[Graph]]):
    pass