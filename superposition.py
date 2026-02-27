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
        self.values = [value for value in values]
        self.possible: dict[E, bool] = dict([(value, True) for value in self.values])
        self.weights: dict[E, float] = dict([(value, 1.0) for value in self.values])
        self.type: Type[E] = type(values[0])
    
    def is_valid(self) -> bool:
        return sum(self._get_prob()) > 0

    def _get_prob(self) -> list[float]:
        return uniform([self.weights[value] if self.possible[value] else 0 for value in self.values])
    
    def collapse(self, rnd: Random) -> None:
        if self.is_collapsed:
            return
        self.is_collapsed = True
        self.value = rnd.choices(self.values, weights=self._get_prob())[0] if self.is_valid() else None
    
    def remove(self, value: E):
        assert value in self.values
        self.possible[self.values.index(value)] = False

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SuperList) and self.type == other.type:
            if self.is_collapsed and other.is_collapsed:
                return self.value == other.value and self.value is not None
            if self.is_collapsed:
                return other.possible.get(self.value, False)
            if other.is_collapsed and isinstance(other.value, self.type): # the isinstance is redundant, but will show type errors if removed
                return self.possible.get(other.value, False)
            for value in self.values:
                if other.possible.get(value, False):
                    return True
            return False
        if isinstance(other, self.type):
            if self.is_collapsed:
                return self.value == other
            return self.possible.get(other, False)
        return False

    
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

    def __gt__(self, other: SuperRange|int) -> bool:
        if isinstance(other, SuperRange):
            return self.max > other.min
        if isinstance(other, int):
            return self.max > other
        raise Exception(f"Cannot compare SuperRange with type {type(other)}")
    
    def __lt__(self, other: SuperRange|int) -> bool:
        if isinstance(other, SuperRange):
            return self.min < other.max
        if isinstance(other, int):
            return self.min < other
        raise Exception(f"Cannot compare SuperRange with type {type(other)}")
    
    def __ge__(self, other: SuperRange|int) -> bool:
        if isinstance(other, SuperRange):
            return self.max >= other.min
        if isinstance(other, int):
            return self.max >= other
        raise Exception(f"Cannot compare SuperRange with type {type(other)}")
    
    def __le__(self, other: SuperRange|int) -> bool:
        if isinstance(other, SuperRange):
            return self.min <= other.max
        if isinstance(other, int):
            return self.min <= other
        raise Exception(f"Cannot compare SuperRange with type {type(other)}")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SuperRange):
            return other.min <= self.max and other.max >= self.min
        if isinstance(other, int):
            return other >= self.min and other <= self.max
        raise Exception(f"Cannot compare SuperRange with type {type(other)}")

    def __add__(self, other: int|SuperRange) -> SuperRange:
        if isinstance(other, SuperRange):
            return SuperRange(self.min + other.min, self.max + other.max)
        elif isinstance(other, int):
            return SuperRange(self.min + other, self.max + other)
        raise Exception(f"Cannot add SuperRange to type {type(other)}")

    def __radd__(self, other: int|SuperRange) -> SuperRange:
        return self.__add__(other)
    
    def __mul__(self, other: int) -> SuperRange:
        if isinstance(other, int):
            return SuperRange(self.min * other, self.max * other)
        raise Exception(f"Cannot mult SuperRange by type {type(other)}")

    def __rmul__(self, other: int) -> SuperRange:
        return self.__mul__(other)
    
    # TODO __sub__, __rsub__, __truediv__, __rtruediv__
    
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