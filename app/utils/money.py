"""
Money / currency formatting helpers.

The game stores all fees as integers in a base unit (GBP for the legacy
budgets, but practically interchangeable across clubs since we don't
model FX). For display we want:
  * a currency symbol that matches the club's home league when known
  * thousands separators that read well at a glance — use a non-breaking
    space (\u00a0) so they don't break across lines

Examples:
  format_money(14_798_095)              -> "€14 798 095"
  format_money(14_798_095, "GBP")       -> "£14 798 095"
  format_money(14_798_095, "USD")       -> "$14 798 095"
  format_money(0)                       -> "€0"
  format_money(None)                    -> ""
"""
from __future__ import annotations

# Map of currency code → symbol shown in the UI. Anything missing here
# falls back to the EUR symbol since most clubs in our world play in
# Europe.
_SYMBOLS: dict[str, str] = {
    "EUR": "€",
    "GBP": "£",
    "USD": "$",
    "BRL": "R$",
    "SAR": "SAR ",
    "RUB": "₽",
}

# League name (case-insensitive) -> currency code. Used by callers that
# only have the club name, not the league. Optional.
_LEAGUE_TO_CCY: dict[str, str] = {
    "premier league": "GBP",
    "epl": "GBP",
    "english premier league": "GBP",
    "championship": "GBP",
    "mls": "USD",
    "major league soccer": "USD",
    "brasileirao": "BRL",
    "serie a brazil": "BRL",
    "saudi pro league": "SAR",
}


def format_money(amount: int | float | None, currency: str = "EUR",
                 *, compact: bool = True) -> str:
    """Format an integer amount with a currency symbol.

    By default uses *compact* notation: 12_817_205 → "€12.8M",
    540_000 → "€540k", 1_500 → "€1.5k".  Set ``compact=False`` to
    get the long form ("€12 817 205") with a non-breaking-space
    thousands separator.
    """
    if amount is None:
        return ""
    try:
        n = int(amount)
    except (TypeError, ValueError):
        return ""
    sym = _SYMBOLS.get((currency or "EUR").upper(), "€")

    if compact:
        sign = "-" if n < 0 else ""
        v = abs(n)
        if v >= 1_000_000_000:
            txt = f"{v / 1_000_000_000:.1f}B"
        elif v >= 1_000_000:
            txt = f"{v / 1_000_000:.1f}M"
        elif v >= 1_000:
            txt = f"{v / 1_000:.1f}k"
        else:
            txt = f"{v}"
        # strip trailing ".0" so we get "12M" not "12.0M".
        if txt.endswith(".0M") or txt.endswith(".0k") or txt.endswith(".0B"):
            txt = txt[:-3] + txt[-1]
        return f"{sign}{sym}{txt}"

    # Long form.
    if n < 0:
        body = f"-{abs(n):,}".replace(",", "\u00a0")
    else:
        body = f"{n:,}".replace(",", "\u00a0")
    return f"{sym}{body}"


def currency_for_league(league_name: str | None) -> str:
    """Best-effort league name → ISO currency code lookup."""
    if not league_name:
        return "EUR"
    key = league_name.strip().lower()
    return _LEAGUE_TO_CCY.get(key, "EUR")
