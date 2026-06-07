from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

SCALE_BITS = 64
SCALE = 1 << SCALE_BITS

# Signed 128-bit raw bounds for deterministic overflow discipline.
RAW_MIN = -(1 << 127)
RAW_MAX = (1 << 127) - 1


class FixedMathError(Exception):
    pass


class FixedOverflowError(FixedMathError):
    pass


class FixedParseError(FixedMathError):
    pass


def _check_raw(raw: int) -> int:
    if raw < RAW_MIN or raw > RAW_MAX:
        raise FixedOverflowError(f"fixed64 overflow: {raw}")
    return raw


def _round_div_half_even(numerator: int, denominator: int) -> int:
    """Deterministic banker rounding for signed integer division."""

    if denominator == 0:
        raise ZeroDivisionError("division by zero")

    if denominator < 0:
        numerator = -numerator
        denominator = -denominator

    sign = -1 if numerator < 0 else 1
    n = abs(numerator)

    quotient, remainder = divmod(n, denominator)
    doubled = remainder * 2

    if doubled > denominator:
        quotient += 1
    elif doubled == denominator and (quotient % 2 == 1):
        quotient += 1

    return sign * quotient


@dataclass(frozen=True, order=True)
class Fixed64:
    raw: int

    def __post_init__(self) -> None:
        _check_raw(self.raw)

    @classmethod
    def zero(cls) -> "Fixed64":
        return cls(0)

    @classmethod
    def one(cls) -> "Fixed64":
        return cls(SCALE)

    @classmethod
    def from_raw(cls, raw: int) -> "Fixed64":
        if not isinstance(raw, int):
            raise TypeError("raw must be int")
        return cls(_check_raw(raw))

    @classmethod
    def from_int(cls, value: int) -> "Fixed64":
        if not isinstance(value, int):
            raise TypeError("value must be int")
        return cls.from_raw(_check_raw(value * SCALE))

    @classmethod
    def from_ratio(cls, numerator: int, denominator: int) -> "Fixed64":
        if not isinstance(numerator, int) or not isinstance(denominator, int):
            raise TypeError("numerator/denominator must be int")
        raw = _round_div_half_even(numerator * SCALE, denominator)
        return cls.from_raw(raw)

    @classmethod
    def from_str(cls, value: str) -> "Fixed64":
        if not isinstance(value, str):
            raise TypeError("value must be str")

        text = value.strip()
        if not text:
            raise FixedParseError("empty fixed-point string")

        sign = 1
        if text[0] in {"+", "-"}:
            if text[0] == "-":
                sign = -1
            text = text[1:]

        if not text:
            raise FixedParseError("invalid fixed-point string")

        # Accept scientific notation at module boundaries and normalize it to
        # plain decimal so fixed parsing remains deterministic.
        if "e" in text.lower():
            try:
                text = format(Decimal(text), "f")
            except InvalidOperation as exc:
                raise FixedParseError(f"invalid fixed-point string: {value}") from exc
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            if text in {"", "-0"}:
                text = "0"

        if text.count(".") > 1:
            raise FixedParseError(f"invalid fixed-point string: {value}")

        if "." in text:
            int_part, frac_part = text.split(".", 1)
        else:
            int_part, frac_part = text, ""

        if int_part == "":
            int_part = "0"

        if not int_part.isdigit() or (frac_part and not frac_part.isdigit()):
            raise FixedParseError(f"invalid fixed-point string: {value}")

        int_raw = int(int_part) * SCALE

        frac_raw = 0
        if frac_part:
            frac_num = int(frac_part)
            frac_den = 10 ** len(frac_part)
            frac_raw = _round_div_half_even(frac_num * SCALE, frac_den)

        raw = int_raw + frac_raw
        if sign < 0:
            raw = -raw
        return cls.from_raw(raw)

    def to_raw(self) -> int:
        return self.raw

    def to_int_floor(self) -> int:
        return self.raw // SCALE

    def to_str(self, precision: int = 18) -> str:
        if precision < 0:
            raise ValueError("precision must be >= 0")

        sign = "-" if self.raw < 0 else ""
        abs_raw = abs(self.raw)

        integer = abs_raw // SCALE
        fraction_raw = abs_raw % SCALE

        if precision == 0:
            return f"{sign}{integer}"

        den = 10 ** precision
        fraction_scaled = _round_div_half_even(fraction_raw * den, SCALE)

        if fraction_scaled >= den:
            integer += 1
            fraction_scaled -= den

        return f"{sign}{integer}.{fraction_scaled:0{precision}d}"

    def __str__(self) -> str:
        return self.to_str(18)

    def _coerce(self, other: object) -> "Fixed64":
        if isinstance(other, Fixed64):
            return other
        if isinstance(other, int):
            return Fixed64.from_int(other)
        if isinstance(other, str):
            return Fixed64.from_str(other)
        raise TypeError(f"unsupported operand type: {type(other)!r}")

    def __add__(self, other: object) -> "Fixed64":
        rhs = self._coerce(other)
        return Fixed64.from_raw(_check_raw(self.raw + rhs.raw))

    def __sub__(self, other: object) -> "Fixed64":
        rhs = self._coerce(other)
        return Fixed64.from_raw(_check_raw(self.raw - rhs.raw))

    def __mul__(self, other: object) -> "Fixed64":
        rhs = self._coerce(other)
        raw = _round_div_half_even(self.raw * rhs.raw, SCALE)
        return Fixed64.from_raw(_check_raw(raw))

    def __truediv__(self, other: object) -> "Fixed64":
        rhs = self._coerce(other)
        raw = _round_div_half_even(self.raw * SCALE, rhs.raw)
        return Fixed64.from_raw(_check_raw(raw))

    def __neg__(self) -> "Fixed64":
        return Fixed64.from_raw(_check_raw(-self.raw))

    def __abs__(self) -> "Fixed64":
        if self.raw >= 0:
            return self
        return -self
