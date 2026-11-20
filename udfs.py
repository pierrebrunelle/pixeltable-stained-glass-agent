"""UDFs and agent tools (pure Python, no table imports)."""

from __future__ import annotations

import asyncio
import colorsys
import PIL.Image
import pixeltable as pxt

AGENT_MODEL = 'gpt-4o-mini'
VISION_MODEL = 'gpt-4o-mini'

SYSTEM_PROMPT = (
    'You are the studio assistant of a stained-glass workshop. Answer commission questions in at most '
    'three sentences. Use the tools for prices and glass stock, and look at the attached image of the window.'
)

# Studio price list (EUR): per square decimetre plus a fee per cut piece.
PRICE_PER_DM2 = 11.5
FEE_PER_PIECE = 2.2

# Sheets in stock per glass colour (the async stock tool reads this).
STOCK = {'cobalt': 14, 'amber': 6, 'ruby': 0, 'emerald': 9, 'opal white': 22, 'violet': 3}


def hue_name(hue: float) -> str:
    """Name of a hue given in turns (0..1)."""
    for limit, name in [(0.04, 'ruby'), (0.11, 'amber'), (0.2, 'amber'), (0.45, 'emerald'), (0.72, 'cobalt'), (0.9, 'violet')]:
        if hue < limit:
            return name
    return 'ruby'


@pxt.udf
def dominant_glass(img: PIL.Image.Image) -> str:
    """Name of the glass colour that covers the most of the picture (coarse hue buckets)."""
    small = img.convert('RGB').resize((48, 48))
    counts: dict[str, int] = {}
    for r, g, b in small.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if v < 0.25:
            continue  # lead lines
        name = 'opal white' if s < 0.15 else hue_name(h)
        counts[name] = counts.get(name, 0) + 1
    return max(counts, key=lambda k: counts[k]) if counts else 'opal white'


@pxt.udf
def brightness(img: PIL.Image.Image) -> float:
    """Mean brightness 0-255 of a picture."""
    return round(sum(img.convert('L').resize((32, 32)).getdata()) / 1024, 1)


@pxt.udf
def quote_panel(width_cm: float, height_cm: float, pieces: int) -> dict:
    """Price quote for one stained-glass panel.

    Args:
        width_cm: Panel width in centimetres.
        height_cm: Panel height in centimetres.
        pieces: Number of cut glass pieces in the design.
    """
    area_dm2 = width_cm * height_cm / 100.0
    total = area_dm2 * PRICE_PER_DM2 + pieces * FEE_PER_PIECE
    return {'area_dm2': round(area_dm2, 1), 'pieces': pieces, 'total_eur': round(total, 2)}


@pxt.udf
async def glass_stock(color: str) -> str:
    """Sheets of a glass colour currently in stock (async lookup).

    Args:
        color: Glass colour such as cobalt, amber, ruby, emerald, violet or opal white.
    """
    await asyncio.sleep(0.05)  # stands in for a supplier API call
    n = STOCK.get(color.strip().lower())
    if n is None:
        return f'{color}: not a stocked colour'
    return f'{color}: {n} sheets in stock' if n else f'{color}: out of stock, 3 week lead time'


@pxt.udf
def final_answer(content: str | None, tool_results: dict | None) -> str:
    """The model's text, or the raw tool results when the model only called tools."""
    if content:
        return content
    if not tool_results:
        return ''
    return '; '.join(f'{name}: {res}' for name, res in tool_results.items() if res is not None)


@pxt.udf
def pack_notes(question: str, notes: list[str]) -> str:
    """Question preceded by the stored session notes of this commission."""
    if not notes:
        return question
    lines = '\n'.join(f'- {n}' for n in notes)
    return f'Session notes so far:\n{lines}\n\nQuestion: {question}'
