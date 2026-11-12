from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def number(value, label, positive=False):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{label}: ingresa un número válido.") from None
    if not result.is_finite() or result > 100000000 or result < 0 or (positive and not result):
        raise ValueError(f"{label}: valor fuera de rango.")
    return result


def whole(value, label, positive=False):
    result = number(value, label, positive)
    if result != result.to_integral_value():
        raise ValueError(f"{label}: ingresa un número entero.")
    return int(result)


def required(value, label):
    result = str(value).strip() if value is not None else ""
    if not result or len(result) > 150:
        raise ValueError(f"{label}: ingresa entre 1 y 150 caracteres.")
    return result


def money(value):
    return str(value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
