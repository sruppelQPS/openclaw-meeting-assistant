#!/usr/bin/env python3
"""
M365 Calendar integration
Pulls meeting metadata from Outlook Calendar to auto-fill context.
Reuses existing OpenClaw m365-calendar credentials.
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List


class M365CalendarContext:
    """Enrich meeting metadata from M365 Calendar"""

    def __init__(self, config: Dict):
        self.profile = config.get('profile', 'work')
        self.script_dir = Path('~/.openclaw/workspace/skills/m365-calendar/scripts').expanduser()

    def find_meeting_by_time(self, meeting_time: datetime, tolerance_minutes: int = 30) -> Optional[Dict]:
        """
        Suche Meeting in Outlook Calendar das zur angegebenen Zeit passt

        Args:
            meeting_time: Wann das Meeting stattfand
            tolerance_minutes: Wie viel Abweichung erlaubt (Standard 30 Min)

        Returns:
            Meeting-Dict oder None
        """
        try:
            result = subprocess.run(
                [
                    'node', str(self.script_dir / 'list-events.mjs'),
                    '--profile', self.profile,
                    '--days', '1',
                    '--top', '20',
                    '--json',
                ],
                capture_output=True, text=True, timeout=30,
            )

            if result.returncode != 0:
                print(f"⚠️  Kalender-Abfrage fehlgeschlagen: {result.stderr[:200]}")
                return None

            events = json.loads(result.stdout)

            for event in events:
                event_start = datetime.fromisoformat(
                    event.get('start', {}).get('dateTime', '').replace('Z', '+00:00')
                )
                diff = abs((event_start - meeting_time).total_seconds()) / 60

                if diff <= tolerance_minutes:
                    return self._parse_event(event)

        except FileNotFoundError:
            print("⚠️  m365-calendar Skill nicht gefunden")
        except json.JSONDecodeError:
            print("⚠️  Kalender-Antwort kein gültiges JSON")
        except subprocess.TimeoutExpired:
            print("⚠️  Kalender-Abfrage Timeout")
        except Exception as e:
            print(f"⚠️  Kalender-Fehler: {e}")

        return None

    def get_todays_meetings(self) -> List[Dict]:
        """Alle heutigen Meetings abrufen"""
        try:
            result = subprocess.run(
                [
                    'node', str(self.script_dir / 'list-events.mjs'),
                    '--profile', self.profile,
                    '--days', '1',
                    '--top', '20',
                    '--json',
                ],
                capture_output=True, text=True, timeout=30,
            )

            if result.returncode != 0:
                return []

            events = json.loads(result.stdout)
            return [self._parse_event(e) for e in events]

        except Exception as e:
            print(f"⚠️  Kalender-Fehler: {e}")
            return []

    def _parse_event(self, event: Dict) -> Dict:
        """Calendar-Event in Meeting-Metadata konvertieren"""
        start = event.get('start', {}).get('dateTime', '')
        end = event.get('end', {}).get('dateTime', '')

        attendees = []
        for a in event.get('attendees', []):
            email_addr = a.get('emailAddress', {})
            attendees.append({
                'name': email_addr.get('name', ''),
                'email': email_addr.get('address', ''),
                'response': a.get('status', {}).get('response', 'none'),
            })

        # Versuche Agenda aus Body zu extrahieren
        body = event.get('body', {}).get('content', '')
        agenda = self._extract_agenda(body)

        return {
            'title': event.get('subject', ''),
            'date': start[:10] if start else '',
            'start_time': start[11:16] if len(start) > 16 else '',
            'end_time': end[11:16] if len(end) > 16 else '',
            'location': event.get('location', {}).get('displayName', 'Online'),
            'organizer': event.get('organizer', {}).get('emailAddress', {}).get('name', ''),
            'attendees': attendees,
            'agenda': agenda,
            'body': body,
            'is_online': event.get('isOnlineMeeting', False),
            'online_url': event.get('onlineMeeting', {}).get('joinUrl', ''),
        }

    def _extract_agenda(self, body: str) -> List[str]:
        """Versuche Agenda-Punkte aus Meeting-Body zu extrahieren"""
        if not body:
            return []

        agenda = []
        lines = body.replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '')

        for line in lines.split('\n'):
            line = line.strip()
            # Erkenne nummerierte Listen, Bullet Points, Agenda-Formate
            if any(line.startswith(p) for p in ('1.', '2.', '3.', '4.', '5.', '-', '•', '*', '–')):
                clean = line.lstrip('0123456789.-•*– \t')
                if clean and len(clean) > 3:
                    agenda.append(clean)

        return agenda
