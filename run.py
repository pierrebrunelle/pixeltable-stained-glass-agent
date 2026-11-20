"""Seed the workshop and ask the agent questions (python run.py seed | ask <id> "<question>")."""

import os
import sys
from pathlib import Path

import pixeltable as pxt
from pydantic import BaseModel

D = Path(__file__).parent / 'data'
NS = os.environ.get('GLASS_NS', 'glass')  # e.g. pxt://<org>:<db>/glass for a hosted database


class NewCommission(BaseModel):
    commission_id: str
    client: str
    brief: str
    width_cm: float
    height_cm: float
    reference: str
    walkthrough: str | None = None


def seed() -> None:
    commissions = pxt.get_table(f'{NS}/commissions')
    rows = [
        NewCommission(commission_id='C-101', client='Harbor Chapel', brief='Cobalt window for the south nave', width_cm=60, height_cm=90, reference=str(D / 'reference/C-101.png'), walkthrough=str(D / 'walkthrough/C-101.mp4')),
        NewCommission(commission_id='C-102', client='Mrs. Okafor', brief='Amber front-door panel', width_cm=40, height_cm=120, reference=str(D / 'reference/C-102.png'), walkthrough=str(D / 'walkthrough/C-102.mp4')),
        NewCommission(commission_id='C-103', client='Linden Cafe', brief='Emerald transom', width_cm=100, height_cm=35, reference=str(D / 'reference/C-103.png'), walkthrough=str(D / 'walkthrough/C-103.mp4')),
        NewCommission(commission_id='C-104', client='Rosa Vetter', brief='Violet rose window, no video yet', width_cm=70, height_cm=70, reference=str(D / 'reference/C-104.png')),
    ]
    print(commissions.insert(rows))
    notes = pxt.get_table(f'{NS}/notes')
    notes.insert([
        {'commission_id': 'C-101', 'note': 'Client wants the cobalt panel leaded with 40 pieces.'},
        {'commission_id': 'C-102', 'note': 'Door is 40 x 120 cm; privacy glass preferred.'},
    ])


def ask(cid: str, question: str) -> None:
    turns = pxt.get_table(f'{NS}/turns')
    status = turns.insert([{'commission_id': cid, 'question': question, 'attachment': str(D / 'site-photo.png')}])
    print(status)
    row = turns.where(turns.question == question).select(turns.answer, turns.tool_results).collect()[-1]
    print(row)


if __name__ == '__main__':
    if sys.argv[1] == 'seed':
        seed()
    else:
        ask(sys.argv[2], sys.argv[3])
