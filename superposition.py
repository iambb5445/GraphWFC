from __future__ import annotations
from enum import StrEnum
from typing import Union, Sequence, TypeVar, Type, Generic
from abc import ABC, abstractmethod
from random import Random
from utility import get_random_str, uniform
    
E = TypeVar("E")
class SuperPosition(ABC, Generic[E]):
    def __init__(self) -> None:
        self.value: E|None = None
        self.is_collapsed: bool = False

    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @abstractmethod
    def collapse(self, rnd: Random) -> None:
        pass

    def get(self) -> E|None:
        return self.value

class SuperList(SuperPosition[E]):
    def __init__(self, values: list[E]) -> None:
        super().__init__()
        self.values: list[E] = values
        self.possible: list[bool] = [True for _ in self.values]
        self.weights: list[float] = [1 for _ in self.values]
    
    def is_valid(self) -> bool:
        return sum(self._get_prob()) > 0

    def _get_prob(self) -> list[float]:
        return uniform([w if p else 0 for p, w in zip(self.possible, self.weights)])
    
    def collapse(self, rnd: Random) -> None:
        if self.is_collapsed:
            return
        self.is_collapsed = True
        self.value = rnd.choices(self.values, weights=self._get_prob())[0] if self.is_valid() else None
    
    def remove(self, value: E):
        assert value in self.values
        self.possible[self.values.index(value)] = False
    
    def __str__(self) -> str:
        if self.is_collapsed:
            return f"{self.get()}"
        return f"<{', '.join([f'{val}' for val in self.values])}>"

class SuperRange(SuperPosition[int]):
    def __init__(self, min: int, max: int) -> None:
        super().__init__()
        self.min: int = min
        self.max: int = max
        # no need to keep track of initial range
        # self.true_min: int = min
        # self.true_max: int = max
    
    def is_valid(self) -> bool:
        return self.min <= self.max
    
    def collapse(self, rnd: Random) -> None:
        if self.is_collapsed:
            return
        self.is_collapsed = True
        self.value = rnd.randint(self.min, self.max) if self.is_valid() else None
        if self.value is not None:
            self.min = self.value
            self.max = self.value
    
    def smaller_than(self, value: int):
        self.max = min(self.max, value)

    def bigger_than(self, value: int):
        self.min = max(self.min, value)
    
    def __str__(self) -> str:
        if self.is_collapsed:
            return f"{self.get()}"
        return f"<{self.min}...{self.max}>"

class SuperStr(SuperPosition[str]):
    def is_valid(self) -> bool:
        return True
    
    def collapse(self, rnd: Random) -> None:
        self.is_collapsed = True
        self.value = get_random_str(rnd)
    
    def __str__(self) -> str:
        if self.is_collapsed:
            return f"{self.get()}"
        return "<str>"