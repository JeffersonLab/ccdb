"""Checks a unit string against UCUM, the Unified Code for Units of Measure (https://ucum.org), case-sensitive form.

    from ccdb.ucum import is_ucum
    is_ucum("MeV")        # True
    is_ucum("GeV/[c]")    # True: [c] is the speed of light
    is_ucum("{ADC}")      # True: an annotation, for a quantity without a unit
    is_ucum("Mev")        # False

The grammar is UCUM's: units joined by '.' (product) and '/' (quotient), each a prefixed or plain atom with an
optional integer exponent and an optional {annotation}, parentheses, integer factors and 10*N / 10^N. The atoms are
the base units, the SI and physics units an experiment's calibration tables use, and the common non-metric ones;
a unit outside the table is reported as not UCUM, so the table errs toward a warning. No network, no dependency.
mktbl warns on a unit this check refuses and stores it anyway (docs/cli.md, "Column units").
"""
import re

PREFIXES = ("Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da", "d", "c", "m", "u", "n", "p", "f", "a", "z", "y",
            "Ki", "Mi", "Gi", "Ti")

# Atoms that take a prefix (UCUM "metric" units)
METRIC_ATOMS = {
    # base units
    "m", "s", "g", "rad", "K", "C", "cd",
    # SI derived and accepted
    "mol", "sr", "Hz", "N", "Pa", "J", "W", "A", "V", "F", "Ohm", "S", "Wb", "Cel", "T", "H", "lm", "lx", "Bq", "Gy",
    "Sv", "l", "L", "ar", "t", "bar", "u", "eV", "pc", "B", "Np",
    # natural constants used as units
    "[c]", "[h]", "[k]", "[e]", "[m_e]", "[m_p]", "[eps_0]", "[mu_0]", "[G]",
    # CGS and legacy units still met in detector physics
    "G", "Mx", "Oe", "erg", "dyn", "P", "St", "Ci", "R", "RAD", "REM", "b", "Gal",
}

# Atoms that take no prefix
NON_METRIC_ATOMS = {
    "min", "h", "d", "wk", "mo", "a", "a_j", "a_t", "mo_j", "deg", "'", "''", "gon", "%", "[ppth]", "[ppm]", "[ppb]",
    "[pptr]", "[pi]", "[in_i]", "[ft_i]", "[mi_i]", "[lb_av]", "[degF]", "[psi]", "atm", "[iU]", "[IU]", "Ao", "AU",
    "[ly]", "circ", "sph", "[hp]", "10*", "10^",
}

_EXPONENT = re.compile(r"^(?P<unit>.*?)(?P<exponent>[+-]?[0-9]+)$")
_INTEGER = re.compile(r"^[0-9]+$")


def _simple_unit(text):
    """An atom, with a prefix when the atom is metric"""
    if text in METRIC_ATOMS or text in NON_METRIC_ATOMS:
        return True
    return any(text.startswith(prefix) and text[len(prefix):] in METRIC_ATOMS for prefix in PREFIXES)


def _annotatable(text):
    """A simple unit with an optional exponent: 'cm2', 's-1', '10*3'"""
    if _simple_unit(text):
        return True
    match = _EXPONENT.match(text)
    if not match or not match.group("unit"):
        return False
    unit = match.group("unit")
    # 10*3 and 10^-6 are the atom 10* or 10^ with an exponent
    return _simple_unit(unit)


class _Parser:
    """Recursive descent over a unit string: term := ['/'] component (('.' | '/') component)*"""

    def __init__(self, text):
        self.text = text
        self.at = 0

    def parse(self):
        if not self.text:
            return False
        ok = self.term()
        return ok and self.at == len(self.text)

    def peek(self):
        return self.text[self.at] if self.at < len(self.text) else ""

    def term(self):
        if self.peek() == "/":
            self.at += 1
        if not self.component():
            return False
        while self.peek() in (".", "/"):
            self.at += 1
            if not self.component():
                return False
        return True

    def annotation(self):
        end = self.text.find("}", self.at)
        if end == -1:
            return False
        body = self.text[self.at + 1:end]
        if "{" in body or any(ord(char) < 33 and char != " " or ord(char) > 126 for char in body):
            return False
        self.at = end + 1
        return True

    def component(self):
        char = self.peek()
        if char == "{":
            return self.annotation()
        if char == "(":
            self.at += 1
            if not self.term() or self.peek() != ")":
                return False
            self.at += 1
            return True
        # a unit runs to the next operator, parenthesis or annotation; brackets may hold any of those
        start, depth = self.at, 0
        while self.at < len(self.text):
            char = self.text[self.at]
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            elif depth == 0 and char in "./(){}":
                # '10*' and '10^' keep a sign in their exponent; '.' is never part of a unit
                break
            self.at += 1
        unit = self.text[start:self.at]
        if not unit:
            return False
        if not (_INTEGER.match(unit) or _annotatable(unit)):
            return False
        if self.peek() == "{":
            return self.annotation()
        return True


def is_ucum(units):
    """True when `units` is a UCUM expression this checker knows (see the module text); False for '' and None"""
    if not units or units != units.strip() or " " in units:
        return False
    return _Parser(units).parse()
