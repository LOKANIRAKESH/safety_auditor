"""ICS-domain prompts for LLM entity extraction with few-shot examples."""

SYSTEM_PROMPT = """You are an expert industrial control systems (ICS) safety engineer.
Your task is to extract safety-critical entities and control rules from industrial specification documents.
Extract ONLY what is explicitly stated. Do NOT infer or add information not present in the text.
Respond with valid JSON only. No explanations outside the JSON.
"""

FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
Text: "If pressure transmitter PT-101 reads above 50 bar, pump P-101 shall be stopped immediately via interlock I-101."
Output:
{
  "entities": [
    {"tag": "PT-101", "class": "Sensor", "subclass": "PressureTransmitter", "description": "Pressure transmitter"},
    {"tag": "P-101", "class": "Pump", "subclass": "CentrifugalPump", "description": "Process pump"},
    {"tag": "I-101", "class": "Interlock", "subclass": "SafetyInterlock", "description": "Pressure interlock"}
  ],
  "rules": [
    {
      "rule_id": "auto",
      "equipment": "P-101",
      "condition": {"tag": "PT-101", "operator": ">=", "threshold": 50.0, "unit": "bar"},
      "action": "STOP",
      "trigger_tag": "I-101",
      "rule_type": "shutdown",
      "confidence": 0.97
    }
  ]
}

EXAMPLE 2:
Text: "XV-201 is a pressure control valve on the feed line. The valve should open when flow drops below 10 m3/h as measured by FT-201."
Output:
{
  "entities": [
    {"tag": "XV-201", "class": "Valve", "subclass": "ControlValve", "description": "Pressure control valve on feed line"},
    {"tag": "FT-201", "class": "Sensor", "subclass": "FlowTransmitter", "description": "Feed line flow transmitter"}
  ],
  "rules": [
    {
      "rule_id": "auto",
      "equipment": "XV-201",
      "condition": {"tag": "FT-201", "operator": "<", "threshold": 10.0, "unit": "m3/h"},
      "action": "OPEN",
      "trigger_tag": null,
      "rule_type": "control",
      "confidence": 0.91
    }
  ]
}

EXAMPLE 3:
Text: "The emergency shutdown system ESD-001 activates when either high-high pressure on PT-102 (>75 bar) or high temperature on TT-101 (>180 degC) is detected. Upon ESD activation, all running pumps shall stop and all feed valves shall close."
Output:
{
  "entities": [
    {"tag": "ESD-001", "class": "Controller", "subclass": "EmergencyShutdown", "description": "Emergency shutdown system"},
    {"tag": "PT-102", "class": "Sensor", "subclass": "PressureTransmitter", "description": "High-high pressure sensor"},
    {"tag": "TT-101", "class": "Sensor", "subclass": "TemperatureTransmitter", "description": "High temperature sensor"}
  ],
  "rules": [
    {
      "rule_id": "auto",
      "equipment": "ESD-001",
      "condition": {"tag": "PT-102", "operator": ">=", "threshold": 75.0, "unit": "bar"},
      "action": "ACTIVATE",
      "trigger_tag": null,
      "rule_type": "emergency_shutdown",
      "confidence": 0.98
    },
    {
      "rule_id": "auto",
      "equipment": "ESD-001",
      "condition": {"tag": "TT-101", "operator": ">=", "threshold": 180.0, "unit": "degC"},
      "action": "ACTIVATE",
      "trigger_tag": null,
      "rule_type": "emergency_shutdown",
      "confidence": 0.95
    }
  ]
}
"""

EXTRACTION_TEMPLATE = """
{few_shot_examples}

Now extract entities and rules from the following text. Source document: {source_doc}, Page: {page}.

TEXT:
{text}

Return JSON with keys "entities" and "rules". Use "confidence" from 0.0 to 1.0 to reflect how certain you are.
If a rule is ambiguous or incomplete, set confidence < 0.7 and add "ambiguity_note" field.
"""


def build_extraction_prompt(text: str, source_doc: str = "unknown", page: int = 0) -> str:
    return EXTRACTION_TEMPLATE.format(
        few_shot_examples=FEW_SHOT_EXAMPLES,
        text=text[:4000],  # cap context window usage per block
        source_doc=source_doc,
        page=page,
    )
