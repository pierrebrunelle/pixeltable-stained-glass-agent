"""Stained-glass commission agent built with Pixeltable.

A workshop keeps one row per commission: the brief, the window size, a reference
image of the design and an optional studio walkthrough video. Pixeltable names the
dominant glass colour, makes a thumbnail, asks gpt-4o-mini to describe the design,
and cuts every walkthrough into 2-second clips with video_splitter. `Notes` holds the
stored session: facts remembered about a commission. `Turns` is the agent: every
question is sent with its attached image and the session notes to gpt-4o-mini, which
may call two tools (a price quote and an async glass-stock lookup); the answer is
stored next to the raw tool results.

Layout: UDFs and tools live in udfs.py; this file holds table models and @pxt.query.

    python make_data.py
    pxt schema update app.py glass
    python run.py seed
"""

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import openai

from udfs import (
    AGENT_MODEL,
    SYSTEM_PROMPT,
    VISION_MODEL,
    brightness,
    dominant_glass,
    final_answer,
    glass_stock,
    pack_notes,
    quote_panel,
)

TableModel = pxt.model_base()


class Commissions(TableModel, name='commissions'):
    """One stained-glass commission with its reference image and optional walkthrough video."""

    commission_id = pxt.Column(type=pxt.String, primary_key=True)
    client: pxt.String
    brief: pxt.String
    width_cm: pxt.Float
    height_cm: pxt.Float
    reference: pxt.Image
    walkthrough: pxt.Video | None

    glass = dominant_glass(reference)
    thumb = reference.resize([160, 120])
    look = openai.vision('Describe this stained-glass design in one short sentence.', reference, model=VISION_MODEL)  # v2


class WalkthroughClips(
    TableModel,
    name='walkthrough_clips',
    base=Commissions,
    iterator=pxtf.video.video_splitter(Commissions.walkthrough, duration=2.0, min_segment_duration=0.5),
):
    """Fixed 2-second clips of every walkthrough video, each with a keyframe."""

    keyframe = pxtf.video.extract_frame(video_segment, timestamp=1.0)  # type: ignore[name-defined]  # noqa: F821
    glow = brightness(keyframe)  # v2


class Notes(TableModel, name='notes'):
    """Stored session: one fact remembered about a commission."""

    commission_id: pxt.String
    note: pxt.String
    note_id = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)


@pxt.query
def notes_for(commission_id: str):
    """Session notes of one commission, oldest first."""
    return Notes.where(Notes.commission_id == commission_id).order_by(Notes.note_id).select(Notes.note)


@pxt.query
def bright_clips(min_glow: float):
    """Walkthrough clips whose keyframe is at least min_glow bright, brightest first."""
    return (
        WalkthroughClips.where(WalkthroughClips.glow >= min_glow)
        .order_by(WalkthroughClips.glow, asc=False)
        .select(WalkthroughClips.commission_id, WalkthroughClips.segment_start, WalkthroughClips.glow)
    )


TOOLS = pxt.tools(quote_panel, glass_stock)


class Turns(TableModel, name='turns'):
    """One question to the workshop agent; the model call and the tool calls are computed on insert."""

    commission_id: pxt.String
    question: pxt.String
    attachment: pxt.Image
    turn_id = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)

    notes = notes_for(commission_id)
    prompt = pack_notes(question, notes)
    response = openai.chat_completions(
        [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {
                'role': 'user',
                'content': [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': attachment}],
            },
        ],
        model=AGENT_MODEL,
        tools=TOOLS,
        model_kwargs={'max_tokens': 200},
    )
    tool_results = openai.invoke_tools(TOOLS, response)
    answer = final_answer(response.choices[0].message.content.astype(pxt.String | None), tool_results)  # v2
