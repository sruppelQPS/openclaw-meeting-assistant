# {{title}}

**Datum:** {{date}}  
**Zeit:** {{start_time}} - {{end_time}}  
**Ort:** {{location}}  
**Protokoll:** KI-gestützt (OpenClaw Meeting Assistant)

---

## Teilnehmer

{% for participant in participants %}
- {{participant.name}}{% if participant.role %} ({{participant.role}}){% endif %} {% if participant.present %}✅{% else %}❌{% endif %}
{% endfor %}

---

## Zusammenfassung

{{summary}}

---

## Besprochene Themen

{% for topic in topics %}
### {{loop.index}}. {{topic.title}}

{{topic.content}}

{% if topic.decisions %}
**Entscheidungen:**
{% for decision in topic.decisions %}
- ✅ {{decision.description}}{% if decision.decided_by %} ({{decision.decided_by | join(', ')}}){% endif %}
{% endfor %}
{% endif %}

{% endfor %}

---

## Action Items

| # | Aufgabe | Verantwortlich | Deadline | Priorität | Status |
|---|---------|----------------|----------|-----------|--------|
{% for item in action_items %}
| {{loop.index}} | {{item.description}} | {{item.assignee}} | {{item.deadline}} | {{item.priority}} | {{item.status | default('offen')}} |
{% endfor %}

{% if not action_items %}
_Keine Action Items identifiziert._
{% endif %}

---

## Entscheidungen

{% for decision in decisions %}
- ✅ **{{decision.description}}**
  - Entschieden von: {{decision.decided_by | join(', ')}}
  - Kontext: "{{decision.context}}"
{% endfor %}

{% if not decisions %}
_Keine Entscheidungen getroffen._
{% endif %}

---

## Offene Fragen

{% for question in open_questions %}
- ❓ {{question.question}}
  - Aufgeworfen von: {{question.raised_by}}
  {% if question.assigned_to %}- Zugewiesen an: {{question.assigned_to}}{% endif %}
{% endfor %}

{% if not open_questions %}
_Keine offenen Fragen._
{% endif %}

---

## Nächste Schritte

{% if next_steps %}
{{next_steps}}
{% else %}
_Werden im nächsten Meeting besprochen._
{% endif %}

---

**Protokoll erstellt:** {{created_at}}  
**Tool:** OpenClaw Meeting Assistant v{{version}}  
**Geprüft von:** {{reviewed_by | default('Ausstehend')}}
