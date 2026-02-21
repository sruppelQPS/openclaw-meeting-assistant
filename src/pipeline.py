#!/usr/bin/env python3
"""
Complete meeting processing pipeline with Human-in-the-Loop review.

Flow:
  Audio → Transcribe → Analyze → Review → Export

This is the central orchestrator that ties all modules together.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from transcription.whisper_transcriber import WhisperTranscriber
from analysis.claude_analyzer import ClaudeAnalyzer
from protocol.generator import ProtocolGenerator
from integrations.odoo_connector import OdooConnector
from integrations.m365_calendar import M365CalendarContext
from integrations.memory_store import MemoryStore
from review.review_manager import ReviewSession


class MeetingPipeline:
    """
    Orchestriert den gesamten Meeting-Verarbeitungs-Workflow.

    Usage:
        pipeline = MeetingPipeline(config)
        session = pipeline.process('meeting.mp3', title='Budget Q2')
        # → Review über Telegram oder CLI
        pipeline.export(session)
    """

    def __init__(self, config: Dict):
        self.config = config
        self.output_base = Path(config.get('output_dir', './meetings'))
        self.output_base.mkdir(parents=True, exist_ok=True)

        # Lazy init: Komponenten werden bei Bedarf erstellt
        self._transcriber = None
        self._analyzer = None
        self._generator = None
        self._odoo = None
        self._calendar = None
        self._memory = None

    # ── Lazy Component Init ──────────────────────────────

    @property
    def transcriber(self) -> WhisperTranscriber:
        if not self._transcriber:
            self._transcriber = WhisperTranscriber(self.config.get('transcription', {}))
        return self._transcriber

    @property
    def analyzer(self) -> ClaudeAnalyzer:
        if not self._analyzer:
            self._analyzer = ClaudeAnalyzer(self.config.get('analysis', {}))
        return self._analyzer

    @property
    def generator(self) -> ProtocolGenerator:
        if not self._generator:
            self._generator = ProtocolGenerator(self.config.get('protocol', {}))
        return self._generator

    @property
    def odoo(self) -> Optional[OdooConnector]:
        if self._odoo is None:
            odoo_cfg = self.config.get('odoo', {})
            if odoo_cfg.get('config_path'):
                try:
                    self._odoo = OdooConnector(odoo_cfg)
                except Exception as e:
                    print(f"⚠️  Odoo nicht verfügbar: {e}")
                    self._odoo = False  # sentinel: tried & failed
        return self._odoo if self._odoo is not False else None

    @property
    def calendar(self) -> Optional[M365CalendarContext]:
        if self._calendar is None:
            cal_cfg = self.config.get('m365', {})
            if cal_cfg.get('enabled', True):
                try:
                    self._calendar = M365CalendarContext(cal_cfg)
                except Exception as e:
                    print(f"⚠️  Kalender nicht verfügbar: {e}")
                    self._calendar = False
        return self._calendar if self._calendar is not False else None

    @property
    def memory(self) -> Optional[MemoryStore]:
        if self._memory is None:
            mem_cfg = self.config.get('memory', {})
            if mem_cfg.get('index_enabled', True):
                self._memory = MemoryStore(mem_cfg)
        return self._memory

    # ── Main Pipeline ────────────────────────────────────

    def process(self,
                audio_path: str,
                title: str = None,
                attendees: list = None,
                meeting_type: str = 'team') -> ReviewSession:
        """
        Verarbeite Meeting-Audio komplett bis zum Review.

        Returns:
            ReviewSession – bereit für Human Review
        """
        audio = Path(audio_path)
        if not audio.exists():
            raise FileNotFoundError(f"Audio nicht gefunden: {audio_path}")

        meeting_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_dir = self.output_base / meeting_id
        output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print("🎙️  OpenClaw Meeting Assistant")
        print("=" * 60)

        # ── 1. Kalender-Context ──────────────────────────
        cal_context = {}
        if self.calendar:
            print("\n📅 Suche Meeting im Kalender...")
            cal_context = self.calendar.find_meeting_by_time(datetime.now()) or {}
            if cal_context:
                print(f"   Gefunden: {cal_context.get('title')}")
                if not title:
                    title = cal_context.get('title', 'Meeting')
                if not attendees and cal_context.get('attendees'):
                    attendees = [a['name'] for a in cal_context['attendees']]

        title = title or 'Meeting'

        # ── 2. Transkription ─────────────────────────────
        print(f"\n📝 Schritt 1/4: Transkription")
        transcript = self.transcriber.transcribe(str(audio))
        self.transcriber.save_transcript(transcript, str(output_dir / 'transcript.json'))

        # ── 3. KI-Analyse ────────────────────────────────
        print(f"\n🧠 Schritt 2/4: KI-Analyse")
        context = {
            'title': title,
            'date': datetime.now().strftime('%d.%m.%Y'),
            'attendees': attendees or [],
        }
        analysis = self.analyzer.analyze(transcript['text'], context)
        self.analyzer.save_analysis(analysis, str(output_dir / 'analysis.json'))

        # ── 4. Speaker Matching ──────────────────────────
        participants = []
        if self.odoo and attendees:
            print(f"\n👥 Schritt 3/4: Speaker Matching")
            matched = self.odoo.match_participants(attendees)
            for m in matched:
                participants.append({
                    'name': m.get('matched_name') or m['original_name'],
                    'email': m.get('email'),
                    'odoo_id': m.get('odoo_id'),
                    'present': True,
                })
        else:
            participants = [{'name': n, 'present': True} for n in (attendees or [])]

        # ── 5. Protokoll-Entwurf ─────────────────────────
        print(f"\n📋 Schritt 4/4: Protokoll-Entwurf")
        metadata = {
            'title': title,
            'date': context['date'],
            'start_time': cal_context.get('start_time', ''),
            'end_time': cal_context.get('end_time', ''),
            'location': cal_context.get('location', 'Online'),
            'participants': participants,
        }

        protocol = self.generator.generate(transcript, analysis, metadata)
        self.generator.save_markdown(protocol, str(output_dir / 'protocol_draft.md'))

        # ── 6. Review-Session erstellen ──────────────────
        session = ReviewSession(meeting_id, title)
        session.add_from_analysis(analysis)
        session.save(output_dir / 'review_state.json')

        # Speichere Metadaten für späteren Export
        meta_path = output_dir / 'metadata.json'
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'meeting_id': meeting_id,
                'title': title,
                'metadata': metadata,
                'transcript_path': str(output_dir / 'transcript.json'),
                'analysis_path': str(output_dir / 'analysis.json'),
                'protocol_draft_path': str(output_dir / 'protocol_draft.md'),
                'audio_path': str(audio),
                'cost': {
                    'transcription': self.transcriber.estimate_cost(transcript.get('duration', 0)),
                    'analysis_tokens': analysis.get('tokens_used', 0),
                },
            }, f, indent=2, ensure_ascii=False)

        # ── Summary ──────────────────────────────────────
        p = session.progress
        print("\n" + "=" * 60)
        print("✅ VERARBEITUNG ABGESCHLOSSEN")
        print("=" * 60)
        print(f"   Meeting: {title}")
        print(f"   Dauer: {transcript.get('duration', 0):.0f}s")
        print(f"   Action Items: {len(analysis.get('action_items', []))}")
        print(f"   Entscheidungen: {len(analysis.get('decisions', []))}")
        print(f"   Offene Fragen: {len(analysis.get('open_questions', []))}")
        print(f"\n   ⏳ {p['total']} Elemente warten auf Review")
        print(f"   📁 Output: {output_dir}")

        return session

    # ── Export (nach Review) ─────────────────────────────

    def export(self, session: ReviewSession, output_dir: Path = None):
        """
        Exportiere freigegebene Elemente.
        Darf NUR aufgerufen werden wenn session.is_complete == True.
        """
        if not session.is_complete:
            pending = session.progress['pending']
            raise RuntimeError(
                f"Review nicht abgeschlossen! Noch {pending} Elemente offen."
            )

        if output_dir is None:
            output_dir = self.output_base / session.meeting_id

        print("\n📤 Exportiere freigegebene Elemente...")

        # 1. Odoo Tasks (nur freigegebene Action Items)
        approved_actions = session.get_approved_action_items()
        if approved_actions and self.odoo:
            print(f"\n📌 Erstelle {len(approved_actions)} Odoo Tasks...")
            for ai in approved_actions:
                try:
                    task_id = self.odoo.create_task(ai)
                    ai['odoo_task_id'] = task_id
                except Exception as e:
                    print(f"   ⚠️  Task-Erstellung fehlgeschlagen: {e}")

        # 2. Finales Protokoll (mit Review-Status)
        final_protocol_path = output_dir / 'protocol_final.md'
        # Rebuild protocol with approved data only
        print(f"\n📋 Erstelle finales Protokoll...")
        # (In production würde man das Protokoll mit den approved_data neu generieren)
        if (output_dir / 'protocol_draft.md').exists():
            draft = (output_dir / 'protocol_draft.md').read_text(encoding='utf-8')
            reviewed_by = set()
            for item in session.get_approved():
                if item.reviewed_by:
                    reviewed_by.add(item.reviewed_by)

            final = draft.replace(
                'Ausstehend',
                ', '.join(reviewed_by) or 'Automatisch'
            )
            final_protocol_path.write_text(final, encoding='utf-8')
            print(f"   💾 {final_protocol_path}")

        # 3. Memory (Wissensbasis)
        if self.memory:
            print(f"\n🧠 Speichere in Wissensbasis...")
            meta_path = output_dir / 'metadata.json'
            metadata = {}
            if meta_path.exists():
                metadata = json.loads(meta_path.read_text())
                metadata = metadata.get('metadata', {})

            analysis_approved = {
                'summary': session.get_approved_summary() or '',
                'action_items': approved_actions,
                'decisions': session.get_approved_decisions(),
                'open_questions': [i.data for i in session.get_by_kind('open_question')
                                   if i.status == 'approved'],
                'key_topics': [],
            }
            mem_path = self.memory.save_meeting(
                final_protocol_path.read_text(encoding='utf-8') if final_protocol_path.exists() else '',
                analysis_approved,
                metadata,
            )
            print(f"   💾 {mem_path}")

        # 4. Zusammenfassung
        p = session.progress
        print(f"\n✅ Export abgeschlossen!")
        print(f"   ✅ {p['approved']} Elemente exportiert")
        print(f"   ❌ {p['rejected']} Elemente abgelehnt (übersprungen)")


def load_config(config_path: str = None) -> Dict:
    """Lade Konfiguration"""
    if config_path:
        path = Path(config_path)
    else:
        path = Path(__file__).parent.parent / 'config.json'
        if not path.exists():
            path = Path(__file__).parent.parent / 'config.json.example'

    with open(path, 'r') as f:
        return json.load(f)
