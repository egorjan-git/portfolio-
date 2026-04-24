from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime


class CarType(str, Enum):
    SPORT = "sport"
    TRUCK = "truck"
    CLASSIC = "classic"
    SUV = "suv"
    OTHER = "other"


def _validate_non_empty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _validate_year(year: int) -> int:
    if not isinstance(year, int):
        raise ValueError("year must be int")
    current = datetime.now().year + 1
    if year < 1886 or year > current:
        raise ValueError("year out of range")
    return year


def _validate_scale(scale: str) -> str:
    s = _validate_non_empty("scale", scale)
    if ":" not in s:
        raise ValueError("scale must look like '1:64'")
    left, right = s.split(":", 1)
    if left.strip() != "1":
        raise ValueError("scale must start with '1:'")
    if not right.strip().isdigit() or int(right.strip()) <= 0:
        raise ValueError("scale denominator must be positive integer")
    return f"1:{int(right.strip())}"


def _validate_price(price: Optional[float]) -> Optional[float]:
    if price is None:
        return None
    if not isinstance(price, (int, float)):
        raise ValueError("price must be number")
    if price < 0:
        raise ValueError("price must be >= 0")
    return float(price)


class CarBase(ABC):
    def __init__(
        self,
        car_id: int,
        brand: str,
        model: str,
        year: int,
        scale: str,
        condition: str = "unknown",
        price: Optional[float] = None,
        notes: str = "",
    ) -> None:
        self._id = self._validate_id(car_id)
        self.brand = brand
        self.model = model
        self.year = year
        self.scale = scale
        self.condition = condition
        self.price = price
        self.notes = notes

    @staticmethod
    def _validate_id(car_id: int) -> int:
        if not isinstance(car_id, int) or car_id <= 0:
            raise ValueError("id must be positive int")
        return car_id

    @property
    def id(self) -> int:
        return self._id

    @property
    def brand(self) -> str:
        return self._brand

    @brand.setter
    def brand(self, value: str) -> None:
        self._brand = _validate_non_empty("brand", value)

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = _validate_non_empty("model", value)

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, value: int) -> None:
        self._year = _validate_year(value)

    @property
    def scale(self) -> str:
        return self._scale

    @scale.setter
    def scale(self, value: str) -> None:
        self._scale = _validate_scale(value)

    @property
    def condition(self) -> str:
        return self._condition

    @condition.setter
    def condition(self, value: str) -> None:
        self._condition = _validate_non_empty("condition", value)

    @property
    def price(self) -> Optional[float]:
        return self._price

    @price.setter
    def price(self, value: Optional[float]) -> None:
        self._price = _validate_price(value)

    @property
    def notes(self) -> str:
        return self._notes

    @notes.setter
    def notes(self, value: str) -> None:
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError("notes must be string")
        self._notes = value.strip()

    def copy(self) -> "CarBase":
        return self.from_car(self)

    @classmethod
    def from_car(cls, other: "CarBase") -> "CarBase":
        return cls(
            car_id=other.id,
            brand=other.brand,
            model=other.model,
            year=other.year,
            scale=other.scale,
            condition=other.condition,
            price=other.price,
            notes=other.notes,
        )

    @property
    @abstractmethod
    def car_type(self) -> CarType:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "scale": self.scale,
            "condition": self.condition,
            "price": self.price,
            "notes": self.notes,
            "type": self.car_type.value,
        }

    @staticmethod
    def _type_from_str(s: str) -> CarType:
        try:
            return CarType(s)
        except Exception:
            return CarType.OTHER

    @staticmethod
    def from_dict(d: dict) -> "CarBase":
        if not isinstance(d, dict):
            raise ValueError("invalid car dict")
        ctype = CarBase._type_from_str(str(d.get("type", "other")))
        cls_map = {
            CarType.SPORT: SportsCar,
            CarType.TRUCK: Truck,
            CarType.CLASSIC: ClassicCar,
            CarType.SUV: SuvCar,
            CarType.OTHER: OtherCar,
        }
        cls = cls_map.get(ctype, OtherCar)
        return cls(
            car_id=int(d["id"]),
            brand=str(d["brand"]),
            model=str(d["model"]),
            year=int(d["year"]),
            scale=str(d["scale"]),
            condition=str(d.get("condition", "unknown")),
            price=d.get("price", None),
            notes=str(d.get("notes", "")),
        )

    def __str__(self) -> str:
        p = "-" if self.price is None else f"{self.price:.2f}"
        return f"[{self.id}] {self.brand} {self.model} ({self.year}), {self.scale}, {self.car_type.value}, price={p}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_dict()!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CarBase):
            return False
        return self.to_dict() == other.to_dict()

    def __lt__(self, other: "CarBase") -> bool:
        if self.year != other.year:
            return self.year < other.year
        return self.id < other.id


class SportsCar(CarBase):
    @property
    def car_type(self) -> CarType:
        return CarType.SPORT


class Truck(CarBase):
    @property
    def car_type(self) -> CarType:
        return CarType.TRUCK


class ClassicCar(CarBase):
    @property
    def car_type(self) -> CarType:
        return CarType.CLASSIC


class SuvCar(CarBase):
    @property
    def car_type(self) -> CarType:
        return CarType.SUV


class OtherCar(CarBase):
    @property
    def car_type(self) -> CarType:
        return CarType.OTHER
