from __future__ import annotations
import re
from typing import Callable
from graph import NodeSchema, EdgeSchema, Graph, Node, EdgeCondition, GraphCondition
from superposition import SuperList, SuperRange, SuperStr
from expr_eval import evaluate_expr, compile_expr
from itertools import product

class Parser:
    @staticmethod
    def parse_int(s: str) -> int:
        value = s.strip()
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def extract_consts(s: str):
        consts: dict[str, str] = {}
        VAR_PATTERN = re.compile(r'^\.\w+\s+.+$', re.MULTILINE)
        def extract_and_replace(match: re.Match[str]):
            line = match.group(0)
            name, value = line.split(maxsplit=1)
            consts[name[1:]] = value
            return ""
        cleaned_text = VAR_PATTERN.sub(extract_and_replace, s)
        return consts, cleaned_text
    
    @staticmethod
    def extract_blocks(s: str):
        blocks: dict[str, str] = {}
        to_remove: list[tuple[int, int]] = []
        HEADER_PATTERN = re.compile(r'(\w+)\s*\{')
        for match in HEADER_PATTERN.finditer(s):
            header = match.group(1)
            start = match.end()
            if len(to_remove) > 0 and to_remove[-1][1] > start:
                continue
            count = 1
            assert header not in blocks, f"Multiple definitions for {header}"
            blocks[header] = ""
            for i in range(start, len(s)):
                if s[i] == "{": count += 1
                if s[i] == "}": count -= 1
                if count == 0:
                    blocks[header] = s[start:i-1].strip()
                    to_remove.append((match.start(), i))
                    break
        for start, end in reversed(to_remove):
            s = s[:start] + s[end+1:]
        return blocks, s.strip()
    
    @staticmethod
    def extract_fors(s: str):
        fors: list[tuple[str, str]] = []
        to_remove: list[tuple[int, int]] = []
        FOR_PATTERN = re.compile(r'''
            for\s+every\s+
            (?P<decls>
                (?:[A-Za-z_][\w\.]*\s+[A-Za-z_]\w*
                (?:\s*,\s*[A-Za-z_][\w\.]*\s+[A-Za-z_]\w*)*)
            )
            \s*:\s*
            \{
                (?P<body>[^{}]*)
            \}
        ''', re.VERBOSE | re.DOTALL)
        for match in FOR_PATTERN.finditer(s):
            fors.append((match.group("decls").strip(), match.group("body").strip()))
            to_remove.append((match.start(), match.end()))
        for start, end in reversed(to_remove):
            s = s[:start] + s[end+1:]
        return fors, s.strip()
    
    @staticmethod
    def parse_nodes(s: str) -> dict[str, NodeSchema]:
        node_schemas: dict[str, NodeSchema] = {}
        node_types, s = Parser.extract_blocks(s)
        assert len(s) == 0, f"Unrecognizable text in node definitions: {s}"
        for node_name, prop_definitions in node_types.items():
            lines = [line.strip() for line in prop_definitions.splitlines()]
            schema: NodeSchema = {}
            node_schemas[node_name] = schema
            for line in lines:
                prop, prop_def = line.split(maxsplit=1)
                range_match = re.compile(r'^\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$').match(prop_def)
                if prop_def == '<str>':
                    schema[prop] = lambda: SuperStr()
                elif prop_def[0] == '[' and prop_def[-1] == ']':
                    values: list[str] = [value.strip() for value in prop_def[1:-1].split(',')]
                    schema[prop] = (lambda v: lambda: SuperList(v))(values) # pure magic
                    # schema[prop] = lambda v=values: SuperList(v) another possible solution
                elif range_match is not None:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2))
                    schema[prop] = lambda start=start, end=end: SuperRange(start, end)
                else:
                    raise Exception(f"ERROR: unknown property definition {prop_def}")
        return node_schemas

    @staticmethod
    def get_node_var(var_type: str, node: Node):
        return type(var_type, (), node.properties|node.get_degrees())

    @staticmethod
    def parse_condition(s: str, from_type: str, to_type: str, from_var: str, to_var: str) -> EdgeCondition:
        code, var_names = compile_expr(s)
        for var_name in var_names:
            assert var_name == from_var or var_name == to_var, f"Unknown variable {var_name} used in expression {s}"
        def cond(u: Node, v: Node):
            env = {
                from_var: Parser.get_node_var(from_type, u),
                to_var: Parser.get_node_var(to_type, v),
            }
            return evaluate_expr(code, env)
        return EdgeCondition(cond)

    @staticmethod
    def parse_for(iter: str, body: str) -> EdgeCondition:
        # print(iter, "-", body)
        # Parser.parse_condition(body)
        # TODO
        def cond(u: Node, v: Node):
            return True
        return EdgeCondition(cond)
    
    @staticmethod
    def parse_global_for(iters: str, body: str) -> GraphCondition:
        code, var_names = compile_expr(body)
        iter_list = iters.split(",")
        existing_var_names = [iter.split()[1] for iter in iter_list]
        for var_name in var_names:
            assert var_name in existing_var_names
        def cond(g: Graph):
            assigns: dict[str, list] = {}
            for iter in iter_list:
                var_type, var_name = iter.split()
                assert var_name not in assigns, f"Duplicate variable name {var_name} in for every {iters}"
                if var_type in g.nodes.keys():
                    assigns[var_name] = [Parser.get_node_var(var_type, node) for node in g.nodes[var_type]]
                else:
                    raise Exception(f"Unknown variable type {var_type} in for every {iters}")
            values = [assigns[var_name] for var_name in var_names]
            for assignment in product(*values):
                env = dict(zip(var_names, assignment))
                if not evaluate_expr(code, env):
                    return False
            return True
        return GraphCondition(cond)
    
    @staticmethod
    def parse_edges(s: str, node_names: list[str]) -> dict[str, EdgeSchema]:
        edge_schema: dict[str, EdgeSchema] = {}
        edge_types, s = Parser.extract_blocks(s)
        assert len(s) == 0, f"Unrecognizable text in edge definitions: {s}"
        for edge_name, definition in edge_types.items():
            var_def = definition.splitlines()[0].strip()
            from_type, from_var, to, to_type, to_var = var_def.split()
            assert to == "to", f"Unrecognizable edge definition for {edge_name}: {var_def}"
            assert from_type in node_names, f"Unrecognizable node type {from_type} in edge definition {edge_name}: {var_def}"
            assert to_type in node_names, f"Unrecognizable node type {to_type} in edge definition {edge_name}: {var_def}"
            bidirectional = False
            loops_allowed = False
            conds: list[EdgeCondition] = []
            fors, the_rest = Parser.extract_fors("\n".join(definition.splitlines()[1:]))
            for line in the_rest.splitlines():
                line = line.strip()
                if line == "bidirectional":
                    bidirectional = True
                if line == "loops_allowed":
                    loops_allowed = True
                else:
                    conds.append(Parser.parse_condition(line, from_type, to_type, from_var, to_var))
            for iter, body in fors:
                conds.append(Parser.parse_for(iter, body))
            edge_schema[edge_name] = EdgeSchema(from_type, to_type, EdgeCondition.merge(*conds), bidirectional, loops_allowed, definition)
        return edge_schema
    
    @staticmethod
    def parse_global_condition(s: str) -> GraphCondition:
        fors, the_rest = Parser.extract_fors(s)
        assert len(the_rest) == 0, f"Unrecognizable text in edge definitions: {the_rest}"
        conds: list[GraphCondition] = []
        for iter, body in fors:
            for line in body.splitlines():
                conds.append(Parser.parse_global_for(iter, line.strip()))
        return GraphCondition.merge(*conds)
    
    @staticmethod
    def parse(s: str):
        consts, s = Parser.extract_consts(s)
        for key, val in consts.items():
            s = s.replace(f".{key}", val)
        blocks, s = Parser.extract_blocks(s)
        node_schema = Parser.parse_nodes(blocks["nodes"])
        edge_schema = Parser.parse_edges(blocks["edges"], list(node_schema.keys()))
        global_condition = Parser.parse_global_condition(blocks["global"] if "global" in blocks else "")
        return Graph(node_schema, edge_schema, global_condition)
    
    @staticmethod
    def from_file(file_name: str):
        with open(file_name, "r") as f:
            return Parser.parse(f.read())

from random import Random
import os
g = Parser.from_file(os.path.join("gwfc_examples", "description_simplified.gwfc"))
g.add_nodes(7, "person")
g.add_nodes(4, "location")
g.collapse(Random(42), 0)
print(g)
for edge_name in g.edge_matrix:
    print(edge_name)
    for row in g.edge_matrix[edge_name]:
        print([val.value for val in row])