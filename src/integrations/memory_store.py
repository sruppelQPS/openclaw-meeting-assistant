#!/usr/bin/env python3
"""
Memory integration for OpenClaw
Saves meeting protocols as searchable memory files.
Enables cross-meeting queries via memory_search.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class MemoryStore:
    """Speichert Meeting-Protokolle als OpenClaw Memory"""

    def __init__(self, config: Dict):
        self.storage_path = Path(
            config.get('storage_path', '~/.openclaw/workspace/memory/meetings')
        ).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_meeting(self, protocol_md: str, analysis: Dict, metadata: Dict) -> Path:
        """
        Speichere Meeting als Markdown-Datei im Memory-Verzeichnis

        Format: YYYY-MM-DD-{slugified-title}.md
        Wird automatisch von OpenClaw memory_search gefunden!
        """
        title = metadata.get('title', 'meeting')
        date = metadata.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Normalisiere Datum zu YYYY-MM-DD
        if '.' in date:
            parts = date.split('.')
            if len(parts) == 3:
                date = f"{parts[2]}-{parts[1]}-{parts[0]}"

        slug = self._slugify(title)
        filename = f"{date}-{slug}.md"
        filepath = self.storage_path / filename

        # Erstelle Meeting-Memory mit Metadaten-Header
        memory_content = self._build_memory_content(protocol_md, analysis, metadata)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(memory_content)

        print(f"💾 Meeting in Memory gespeichert: {filepath}")
        return filepath

    def _build_memory_content(self, protocol_md: str, analysis: Dict, metadata: Dict) -> str:
        """Erstelle Memory-Datei mit Metadaten für bessere Suche"""
        lines = [
            f"# Meeting: {metadata.get('title', 'Unbekannt')}",
            f"",
            f"**Datum:** {metadata.get('date', '')}",
            f"**Teilnehmer:** {', '.join(self._extract_names(metadata))}",
            f"**Themen:** {', '.join(analysis.get('key_topics', []))}",
            f"",
        ]

        # Zusammenfassung
        summary = analysis.get('summary', '')
        if summary:
            lines += [
                "## Zusammenfassung",
                "",
                summary,
                "",
            ]

        # Action Items (nur freigegebene falls Review stattfand)
        action_items = analysis.get('action_items', [])
        if action_items:
            lines += ["## Action Items", ""]
            for ai in action_items:
                assignee = ai.get('assignee', '?')
                desc = ai.get('description', '')
                deadline = ai.get('deadline', 'nicht definiert')
                lines.append(f"- [{assignee}] {desc} (bis {deadline})")
            lines.append("")

        # Entscheidungen
        decisions = analysis.get('decisions', [])
        if decisions:
            lines += ["## Entscheidungen", ""]
            for d in decisions:
                lines.append(f"- ✅ {d.get('description', '')}")
            lines.append("")

        # Offene Fragen
        questions = analysis.get('open_questions', [])
        if questions:
            lines += ["## Offene Fragen", ""]
            for q in questions:
                lines.append(f"- ❓ {q.get('question', '')}")
            lines.append("")

        return "\n".join(lines)

    def _extract_names(self, metadata: Dict) -> list:
        participants = metadata.get('participants', [])
        if isinstance(participants, list) and participants:
            if isinstance(participants[0], dict):
                return [p.get('name', '') for p in participants]
            return participants
        return []

    def list_meetings(self, limit: int = 20) -> list:
        """Liste alle gespeicherten Meetings"""
        files = sorted(self.storage_path.glob("*.md"), reverse=True)
        return files[:limit]

    def search_meetings(self, query: str) -> list:
        """Einfache Textsuche über alle Meeting-Dateien"""
        results = []
        query_lower = query.lower()

        for filepath in self.storage_path.glob("*.md"):
            content = filepath.read_text(encoding='utf-8')
            if query_lower in content.lower():
                # Finde relevante Zeilen
                matches = []
                for i, line in enumerate(content.split('\n')):
                    if query_lower in line.lower():
                        matches.append({'line': i + 1, 'text': line.strip()})

                results.append({
                    'file': str(filepath),
                    'name': filepath.stem,
                    'matches': matches[:5],
                })

        return results

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^a-z0-9äöüß\s-]', '', text)
        text = re.sub(r'[\s]+', '-', text)
        text = text.strip('-')
        return text[:60]
