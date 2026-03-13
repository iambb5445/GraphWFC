import ast, types

ALLOWED_NODES = {
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Attribute,
    ast.Call,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
}

def extract_vars(tree: ast.Expression) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

def validate_expr(tree: ast.Expression):
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            raise Exception(f"Expression type not allowed: {type(node).__name__}")
        
def compile_expr(expr: str) -> tuple[types.CodeType, list[str]]:
    tree = ast.parse(expr, mode="eval")
    validate_expr(tree)
    var_names = extract_vars(tree)
    code = compile(tree, "<expr_eval>", "eval")
    return code, list(var_names)

def evaluate_expr(code: types.CodeType, env: dict):
    globals = {
        '__builtins__': {},
        'min': min,
        'max': max,
        'abs': abs,
    }
    return eval(code, globals, env)

# unsafe
# def evaluate_expr(s: str, globals: dict) -> bool:
    # return eval(s, globals)