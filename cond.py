from __future__ import annotations
from abc import ABC
from typing import Callable, ParamSpec, Generic, Self

P = ParamSpec("P")

class Condition(ABC, Generic[P]):
    def __init__(self, check: Callable[P, bool]) -> None:
        self.check = check
    
    @classmethod
    def merge(cls, *conds: Self) -> Self:
        def func(*args: P.args, **kwargs: P.kwargs):
            for cond in conds:
                if not cond.check(*args, **kwargs):
                    return False
            return True
        return cls(func)