#!/usr/bin/env python3
"""
Human-in-the-Loop Review Manager

Kernprinzip: NICHTS wird automatisch exportiert!
Jedes erkannte Element durchläuft den 3-Stufen-Zyklus:
  draft → approved/rejected

Der ReviewManager speichert den Status lokal als JSON.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Literal
from copy import deepcopy

ReviewStatus = Literal['draft', 'approved', 'rejected']


class ReviewableItem:
    """Ein Element das geprüft werden muss"""

    def __init__(self, kind: str, data: Dict):
        self.id = str(uuid.uuid4())[:8]
        self.kind = kind  # 'action_item', 'decision', 'open_question', 'summary'
        self.status: ReviewStatus = 'draft'
        self.original_data = deepcopy(data)
        self.approved_data: Optional[Dict] = None
        self.reviewed_by: Optional[str] = None
        self.reviewed_at: Optional[str] = None
        self.reject_reason: Optional[str] = None

    def approve(self, reviewer: str, changes: Dict = None):
        """Element freigeben, optional mit Änderungen"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now().isoformat()
        if changes:
            self.approved_data = {**self.original_data, **changes}
        else:
            self.approved_data = deepcopy(self.original_data)

    def reject(self, reviewer: str, reason: str = None):
        """Element ablehnen"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now().isoformat()
        self.reject_reason = reason

    @property
    def data(self) -> Dict:
        """Gibt freigegebene Daten zurück falls vorhanden, sonst Original"""
        return self.approved_data or self.original_data

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'kind': self.kind,
            'status': self.status,
            'original_data': self.original_data,
            'approved_data': self.approved_data,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at,
            'reject_reason': self.reject_reason,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'ReviewableItem':
        item = cls(d['kind'], d['original_data'])
        item.id = d['id']
        item.status = d['status']
        item.approved_data = d.get('approved_data')
        item.reviewed_by = d.get('reviewed_by')
        item.reviewed_at = d.get('reviewed_at')
        item.reject_reason = d.get('reject_reason')
        return item


class ReviewSession:
    """Eine komplette Review-Session für ein Meeting"""

    def __init__(self, meeting_id: str, title: str):
        self.meeting_id = meeting_id
        self.title = title
        self.created_at = datetime.now().isoformat()
        self.items: List[ReviewableItem] = []
        self.summary_item: Optional[ReviewableItem] = None
        self._state_path: Optional[Path] = None

    def add_from_analysis(self, analysis: Dict):
        """Erstelle ReviewableItems aus der KI-Analyse"""

        # Zusammenfassung
        if analysis.get('summary'):
            self.summary_item = ReviewableItem('summary', {
                'text': analysis['summary']
            })
            self.items.append(self.summary_item)

        # Action Items
        for ai in analysis.get('action_items', []):
            self.items.append(ReviewableItem('action_item', ai))

        # Entscheidungen
        for dec in analysis.get('decisions', []):
            self.items.append(ReviewableItem('decision', dec))

        # Offene Fragen
        for q in analysis.get('open_questions', []):
            self.items.append(ReviewableItem('open_question', q))

    # ── Zugriff ──────────────────────────────────────────

    def get_pending(self) -> List[ReviewableItem]:
        """Alle ungeprüften Elemente"""
        return [i for i in self.items if i.status == 'draft']

    def get_approved(self) -> List[ReviewableItem]:
        return [i for i in self.items if i.status == 'approved']

    def get_rejected(self) -> List[ReviewableItem]:
        return [i for i in self.items if i.status == 'rejected']

    def get_by_kind(self, kind: str) -> List[ReviewableItem]:
        return [i for i in self.items if i.kind == kind]

    def get_by_id(self, item_id: str) -> Optional[ReviewableItem]:
        for i in self.items:
            if i.id == item_id:
                return i
        return None

    @property
    def is_complete(self) -> bool:
        """Alle Elemente geprüft?"""
        return all(i.status != 'draft' for i in self.items)

    @property
    def progress(self) -> Dict:
        total = len(self.items)
        reviewed = sum(1 for i in self.items if i.status != 'draft')
        return {
            'total': total,
            'reviewed': reviewed,
            'pending': total - reviewed,
            'approved': sum(1 for i in self.items if i.status == 'approved'),
            'rejected': sum(1 for i in self.items if i.status == 'rejected'),
            'percent': int(reviewed / total * 100) if total else 100,
        }

    # ── Batch-Operationen ────────────────────────────────

    def approve_all(self, reviewer: str):
        """Alle Draft-Items freigeben (Schnell-Modus)"""
        for item in self.get_pending():
            item.approve(reviewer)

    def approve_item(self, item_id: str, reviewer: str, changes: Dict = None):
        item = self.get_by_id(item_id)
        if item:
            item.approve(reviewer, changes)

    def reject_item(self, item_id: str, reviewer: str, reason: str = None):
        item = self.get_by_id(item_id)
        if item:
            item.reject(reviewer, reason)

    # ── Export (nur freigegebene!) ────────────────────────

    def get_approved_action_items(self) -> List[Dict]:
        return [i.data for i in self.items
                if i.kind == 'action_item' and i.status == 'approved']

    def get_approved_decisions(self) -> List[Dict]:
        return [i.data for i in self.items
                if i.kind == 'decision' and i.status == 'approved']

    def get_approved_summary(self) -> Optional[str]:
        if self.summary_item and self.summary_item.status == 'approved':
            return self.summary_item.data.get('text')
        return None

    # ── Persistenz ───────────────────────────────────────

    def save(self, path: Path = None):
        """Speichere Review-State als JSON"""
        if path:
            self._state_path = path
        if not self._state_path:
            raise ValueError("Kein Speicherpfad definiert")

        self._state_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'meeting_id': self.meeting_id,
            'title': self.title,
            'created_at': self.created_at,
            'progress': self.progress,
            'items': [i.to_dict() for i in self.items],
        }

        with open(self._state_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> 'ReviewSession':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        session = cls(data['meeting_id'], data['title'])
        session.created_at = data['created_at']
        session._state_path = path

        for item_data in data.get('items', []):
            item = ReviewableItem.from_dict(item_data)
            session.items.append(item)
            if item.kind == 'summary':
                session.summary_item = item

        return session

    # ── Debug ────────────────────────────────────────────

    def print_status(self):
        p = self.progress
        print(f"\n📋 Review: {self.title}")
        print(f"   Geprüft: {p['reviewed']}/{p['total']} ({p['percent']}%)")
        print(f"   ✅ {p['approved']} freigegeben | ❌ {p['rejected']} abgelehnt | 🟡 {p['pending']} offen")

        for item in self.items:
            icon = {'draft': '🟡', 'approved': '✅', 'rejected': '❌'}[item.status]
            kind_label = {
                'summary': '📄 Zusammenfassung',
                'action_item': '📌 Action Item',
                'decision': '✅ Entscheidung',
                'open_question': '❓ Offene Frage',
            }.get(item.kind, item.kind)

            desc = ''
            if item.kind == 'action_item':
                desc = f"{item.data.get('description', '')} → {item.data.get('assignee', '?')}"
            elif item.kind == 'decision':
                desc = item.data.get('description', '')
            elif item.kind == 'open_question':
                desc = item.data.get('question', '')
            elif item.kind == 'summary':
                desc = item.data.get('text', '')[:60] + '...'

            print(f"   {icon} [{item.id}] {kind_label}: {desc}")
