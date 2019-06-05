import inspect
from .core import taichi_lang_core
from .transformer import ASTTransformer
from .expr import Expr
from .snode import SNode
import ast
import astpretty
import astor

def expr_init(rhs):
  return Expr(taichi_lang_core.expr_var(Expr(rhs).ptr))

def make_expr_group(*exprs):
  expr_group = taichi_lang_core.ExprGroup()
  for i in exprs:
    expr_group.push_back(Expr(i).ptr)
  return expr_group


def subscript(value, *indices):
  expr_group = taichi_lang_core.ExprGroup()
  for i in indices:
    expr_group.push_back(Expr(i).ptr)
  return Expr(taichi_lang_core.subscript(value.ptr, expr_group))

class PyTaichi:
  def __init__(self):
    self.materialized = False
    self.prog = None
    self.layout_functions = []
    self.compiled_functions = {}
    self.scope_stack = []
    Expr.materialize_layout_callback = self.materialize

  def materialize(self):
    assert self.materialized == False
    Expr.layout_materialized = True
    self.prog = taichi_lang_core.Program()
    def layout():
      for func in self.layout_functions:
        func()
    taichi_lang_core.layout(layout)
    self.materialized = True

pytaichi = PyTaichi()


def kernel(foo):
  def ret():
    compiled_functions = pytaichi.compiled_functions
    if not pytaichi.materialized:
      pytaichi.materialize()
    if foo not in compiled_functions:
      src = inspect.getsource(foo)
      tree = ast.parse(src)
      # print(astor.to_source(tree.body[0]))

      func_body = tree.body[0]
      func_body.decorator_list = []

      visitor = ASTTransformer()
      visitor.visit(tree)
      ast.fix_missing_locations(tree)

      # astpretty.pprint(func_body)
      print(astor.to_source(tree.body[0]))

      ast.increment_lineno(tree, inspect.getsourcelines(foo)[1] - 1)

      exec(compile(tree, filename=inspect.getsourcefile(foo), mode='exec'), inspect.currentframe().f_back.f_globals, locals())
      compiled = locals()[foo.__name__]

      t_kernel = taichi_lang_core.create_kernel("test")
      t_kernel = t_kernel.define(lambda: compiled())
      compiled_functions[foo] = lambda: t_kernel()
    compiled_functions[foo]()
  return ret

def global_var(dt):
  x = Expr(taichi_lang_core.make_id_expr(""))
  x.ptr = taichi_lang_core.global_new(x.ptr, dt)
  return x

root = SNode(taichi_lang_core.get_root())

def layout(func):
  assert not pytaichi.materialized, "All layout must be specified before the first kernel launch / data access."
  pytaichi.layout_functions.append(func)

float32 = taichi_lang_core.DataType.float32
f32 = float32
int32 = taichi_lang_core.DataType.int32
i32 = int32

def tprint(var):
  code = inspect.getframeinfo(inspect.currentframe().f_back).code_context[0]
  arg_name = code[code.index('(') + 1 : code.index(')')]
  taichi_lang_core.print_(Expr(var).ptr, arg_name)


def index(x):
  return [taichi_lang_core.Index(x)]

def indices(*x):
  return [taichi_lang_core.Index(i) for i in x]
