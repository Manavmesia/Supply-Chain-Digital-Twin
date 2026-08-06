"""app/graph/__init__.py"""
from app.graph.state import SupplyChainState

def build_workflow(*args, **kwargs):
    from app.graph.workflow import build_workflow as _build
    return _build(*args, **kwargs)

def compile_workflow(*args, **kwargs):
    from app.graph.workflow import compile_workflow as _compile
    return _compile(*args, **kwargs)

__all__ = ["SupplyChainState", "build_workflow", "compile_workflow"]
