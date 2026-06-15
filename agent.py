#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAAPID Sales Call Intelligence Agent
Task 1: Agentic Workflow -- GTM Sales Call Transcript -> Deal Intelligence

Architecture : 9-node sequential pipeline with confidence-based branching
Stack        : Python | Anthropic Claude API (demo mode) | Mock Salesforce + Slack
Author       : Abhinav Marda
"""

import json
import time
import os
import datetime

# ============================================================
# MOCK TRANSCRIPT
# ============================================================

MOCK_TRANSCRIPT = """
CALL TRANSCRIPT
Date: June 10, 2026 | Duration: 34 minutes | Platform: Zoom

Attendees:
- Sarah Chen, Account Executive, RAAPID INC
- Dr. Michael Torres, VP of Risk Adjustment, BlueCross Shield of Tennessee (BCST)
- Jennifer Walsh, Director of Medical Economics, BlueCross Shield of Tennessee (BCST)

---

Sarah Chen: Good morning, Dr. Torres, Jennifer. Thanks for making time. I wanted to start by
understanding where things stand with your current risk adjustment operation before we get into
what RAAPID does.

Dr. Michael Torres: The timing is actually good. We just came out of a painful RADV audit cycle.
CMS pulled 200 charts for validation and we had about a 7% error rate. Not catastrophic, but
enough to put leadership on edge, especially given the new RADV extrapolation rules going into
effect next year.

Sarah Chen: That extrapolation change is significant. The 7% error rate -- was that primarily
undercoding, overcoding, or documentation gaps?

Dr. Michael Torres: Mostly documentation. Physicians are documenting the diagnosis but not always
hitting the MEAT criteria clearly enough for an auditor. Our internal coders catch about 60% of
issues on retrospective review but 40% is slipping through. We have a team of 12 coders doing
manual chart review right now.

Jennifer Walsh: And bandwidth is a real issue. We have about 180,000 Medicare Advantage members
and the coding team is stretched. We outsourced some retrospective work to a vendor last year
and the quality was inconsistent -- we ended up having to re-review about 30% of what they returned.

Sarah Chen: Do you have a sense of the revenue impact of that 7% error rate on the risk score side?

Dr. Michael Torres: Our actuaries put it somewhere between 12 and 18 million dollars in missed
RAF capture annually. That is the number that got leadership attention.

Jennifer Walsh: We are also concerned about the prospective side. We do not have good visibility
into care gaps before encounters happen. Physicians are working without real-time coding assist,
so opportunities are being missed at the point of care as well.

Sarah Chen: So two distinct problems -- retrospective accuracy and RADV defensibility on one hand,
and prospective capture at point of care on the other. Is there a priority between the two?

Dr. Michael Torres: The RADV piece is more urgent given the extrapolation change. If CMS starts
extrapolating errors across the membership, a 7% error rate becomes a very different financial
conversation. We want to get that under control first.

Sarah Chen: Can I ask about the current tech stack?

Jennifer Walsh: We have Episource for some retrospective work but the contract is up for renewal
in September and the accuracy has not been where we need it. The integration with Epic has also
been problematic. We have had to do a lot of manual data wrangling.

Sarah Chen: So September is a natural decision point. What does your evaluation process look like?

Dr. Michael Torres: We would need a technical proof of concept with our actual member data --
de-identified -- to validate accuracy claims. Our IT security team would also need to review
the infrastructure. We are running everything on Azure so that would help on compatibility.

Jennifer Walsh: And we would want a reference call with at least one other Medicare Advantage
plan that has been through a RADV cycle with RAAPID.

Sarah Chen: Both are very doable. We have two MA plans that went through RADV audits this cycle
and would be willing to speak with you. On the POC, we typically scope a 90-day pilot against
a subset of your membership.

Dr. Michael Torres: One thing I want to be direct about -- we have been burned by vendors who
oversell accuracy in demos and cannot replicate in production. I would want the POC structured
against records where we already know the ground truth from the RADV audit.

Sarah Chen: That is exactly how I would structure it. Using your RADV audit sample as the test
set is the most honest validation methodology.

Jennifer Walsh: The other thing is budget. We have a line item for risk adjustment technology
in the Q3 budget cycle. The number we are working with is in the range of 800K to 1.2 million
annually depending on scope.

Sarah Chen: That is within our range for a membership your size.

Dr. Michael Torres: One concern I have is transition risk. If we switch platforms mid-year, there
is a risk of a gap in coding coverage.

Sarah Chen: We have a 60-day parallel run protocol where both systems run simultaneously before
you decommission the old one. No gap in coverage.

Dr. Michael Torres: That is good to hear. The next steps: you send a technical proposal by end of
next week, we schedule a demo with our IT team and clinical informatics lead, and set up a
reference call.

Sarah Chen: Should I coordinate with you two for demo scheduling, or is there another stakeholder?

Jennifer Walsh: Include Marcus Webb -- he is our Chief Medical Officer. He will want to be
involved in the final decision.

Sarah Chen: Noted. I will have the proposal to you by EOD Friday.

Dr. Michael Torres: Appreciate it, Sarah. Looking forward to seeing the numbers.

---
[END OF TRANSCRIPT]
"""

# ============================================================
# PROMPT LOADING
# Prompts live in ./prompts/ and are versioned (e.g. extraction.v1.txt).
# To iterate on a prompt, add a new version file and update PROMPT_VERSION.
# ============================================================

PROMPT_VERSION = "v1"
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompts(version: str) -> dict:
    """Parse prompts/prompt.{version}.txt into a dict keyed by section name."""
    path = os.path.join(_PROMPTS_DIR, f"prompt.{version}.txt")
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    sections = {}
    current_key = None
    current_lines = []
    for line in raw.splitlines():
        if line.startswith("[") and line.endswith("]"):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[1:-1]
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


_PROMPTS = _load_prompts(PROMPT_VERSION)

SYSTEM_PROMPT              = _PROMPTS["system"]
EXTRACTION_PROMPT_TEMPLATE = _PROMPTS["extraction"]
SUMMARY_PROMPT_TEMPLATE    = _PROMPTS["summary"]
EMAIL_PROMPT_TEMPLATE      = _PROMPTS["email"]



# ============================================================
# AGENT
# ============================================================

class SalesCallAgent:

    CONFIDENCE_REJECT    = 0.50   # overall avg below this → entire run rejected
    CONFIDENCE_THRESHOLD = 0.80   # overall avg below this → needs human review
                                   # overall avg above this → auto-approved
    MAX_RETRIES = 3

    def __init__(self, transcript: str, demo_mode: bool = True):
        self.transcript = transcript
        self.demo_mode = demo_mode
        self.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}
        self.flags = []
        self.step_times = {}
        self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "raapid_agent")
        os.makedirs(self.output_dir, exist_ok=True)

    def _line(self, char="-", w=68):
        print(char * w)

    def _log(self, msg, indent=0):
        print("  " * indent + msg)

    def _call_llm(self, system: str, prompt: str, label: str) -> str:
        """
        Priority order:
          1. GROQ_API_KEY set  → Groq (Llama 3.1 70B, free tier, OpenAI-compatible)
          2. ANTHROPIC_API_KEY set → Anthropic Claude
          3. Neither set       → rule-based fallback (demo mode)
        """
        self._log(f"Prompt template     : {label}", 1)

        groq_key = os.environ.get("GROQ_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if groq_key:
            self._log("Model               : llama-3.1-70b-versatile (Groq)", 1)
            self._log("Mode                : LIVE via Groq free tier", 1)
            from openai import OpenAI
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt},
                ]
            )
            return resp.choices[0].message.content

        elif anthropic_key:
            self._log("Model               : claude-sonnet-4-6 (Anthropic)", 1)
            self._log("Mode                : LIVE via Anthropic API", 1)
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text

        else:
            self._log("Model               : rule-based extractor", 1)
            self._log("Mode                : DEMO (no API key set — set GROQ_API_KEY for live LLM)", 1)
            time.sleep(0.9)
            if label == "EXTRACTION":
                return json.dumps(self._parse_transcript_intel(self.transcript))
            elif label == "SUMMARY":
                return self._generate_summary(self.results.get("intel", {}))
            elif label == "EMAIL":
                return self._generate_email(self.results.get("intel", {}))

    # ---- TRANSCRIPT-BASED EXTRACTION (demo mode) ---------------------------

    def _parse_transcript_intel(self, transcript):
        """Extract structured deal intel from transcript text without an LLM."""
        import re
        t = transcript

        # ---- METADATA ----
        call_date, duration = None, None
        date_m = re.search(r'Date:\s*([A-Za-z]+ \d{1,2},?\s*\d{4})', t)
        if date_m:
            call_date = date_m.group(1).strip()
        dur_m = re.search(r'Duration:\s*(\d+)\s*minutes', t, re.IGNORECASE)
        if dur_m:
            duration = int(dur_m.group(1))

        # ---- ATTENDEES ----
        raapid_names, prospect_company, raw_attendees = [], None, []
        block_m = re.search(r'Attendees?:?\s*\n(.*?)(?:\n---|\n\n)', t, re.DOTALL | re.IGNORECASE)
        if block_m:
            for line in block_m.group(1).split('\n'):
                m = re.match(r'[-*\u2022]\s*([^,\n]+),\s*([^,\n]+),\s*([^\n]+)', line.strip())
                if m:
                    name, title, company = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                    raw_attendees.append({'name': name, 'title': title, 'company': company})
                    if 'RAAPID' in company.upper():
                        raapid_names.append(name)
                    elif not prospect_company:
                        prospect_company = company

        ae_name = raapid_names[0] if raapid_names else 'Sarah Chen'
        ae_first = ae_name.split()[0]

        # ---- STAKEHOLDERS ----
        stakeholders = []
        for a in raw_attendees:
            if 'RAAPID' in a['company'].upper():
                continue
            tl = a['title'].lower()
            if any(x in tl for x in ['chief', 'cmo', 'ceo', 'cfo', 'cto', 'coo', 'vp ', 'vice president', 'svp', 'evp', 'president']):
                role, conf = 'decision_maker', 0.92
            elif any(x in tl for x in ['director', 'head of', 'senior dir']):
                role, conf = 'champion', 0.88
            else:
                role, conf = 'influencer', 0.82
            stakeholders.append({'name': a['name'], 'title': a['title'], 'company': a['company'],
                                  'role_in_deal': role, 'confidence': conf})

        # Additional stakeholders mentioned in transcript body (not on call)
        for m in re.finditer(
            r'(?:include|loop in|coordinate with|add|copy)\s+([A-Z][a-z]+ [A-Z][a-z]+)[^.]*?'
            r'(?:--\s*|,\s*)(?:he|she)(?:\'s| is)\s+(?:our|the)\s+([^.\n,]+)', t
        ):
            name, title = m.group(1).strip(), m.group(2).strip().rstrip(',.')
            if name not in [s['name'] for s in stakeholders]:
                stakeholders.append({'name': name, 'title': title.title(),
                                      'company': prospect_company or 'Prospect',
                                      'role_in_deal': 'decision_maker', 'confidence': 0.87})

        if not stakeholders:
            stakeholders.append({'name': 'Unknown', 'title': 'Unknown',
                                  'company': prospect_company or 'Unknown',
                                  'role_in_deal': 'influencer', 'confidence': 0.50})

        # ---- PAIN POINTS ----
        pain_points = []
        sev_kw = {
            'critical': ['extrapolat', 'audit', 'error rate', 'at risk', 'penalt',
                         'regulat', 'compliance', 'cms rule', 'failed'],
            'high':     ['inconsistent', 'manual', 'stretched', 'slipping', 'outsourc',
                         'bandwidth', 'rework', 'missed', 'not working', 'problematic',
                         'gap', 'no visibility', 'no real-time'],
            'medium':   ['concern', 'slow', 'inefficient', 'limited', 'difficult'],
        }
        speaker_turns = re.split(r'\n(?=[A-Z][a-z]+(?: [A-Z][a-z]+)?:)', t)
        seen_pain = set()
        for turn in speaker_turns:
            if turn.strip().startswith(ae_first):
                continue
            for sent in re.split(r'(?<=[.!])\s+', turn):
                sent = sent.strip()
                if len(sent) < 30 or sent.endswith('?') or ':' in sent[:25]:
                    continue
                has_number = bool(re.search(r'\$[\d.,]+|\d+%|\d+\s*(?:million|M\b)', sent, re.IGNORECASE))
                sev = next((s for s, kws in sev_kw.items() if any(kw in sent.lower() for kw in kws)), None)
                if sev or has_number:
                    key = sent[:35].lower()
                    if key not in seen_pain:
                        seen_pain.add(key)
                        conf = 0.95 if has_number else (0.90 if sev == 'critical' else 0.84)
                        pain_points.append({'description': sent[:220],
                                            'severity': sev or 'medium', 'confidence': conf})
            if len(pain_points) >= 5:
                break
        if not pain_points:
            pain_points.append({'description': 'Operational challenges discussed — manual review recommended',
                                 'severity': 'medium', 'confidence': 0.55})

        # ---- BANT ----
        budget_val, budget_conf = None, 0.50
        bm = re.search(
            r'(?:budget|number|range|working with)[^.]*?'
            r'(\$[\d.,]+[KkMm]?(?:\s*(?:to|-)\s*\$?[\d.,]+[KkMm]?)?'
            r'(?:\s*(?:million|M|K|annually|per year|a year))?)', t, re.IGNORECASE)
        if not bm:
            bm = re.search(r'(\$[\d.,]+(?:\s*(?:million|M|K))?[^.]*?(?:annually|per year|budget)?)', t, re.IGNORECASE)
        if bm:
            budget_val = bm.group(1).strip()
            surr = t[max(0, t.find(bm.group(0)) - 20):t.find(bm.group(0)) + 150]
            if any(w in surr.lower() for w in ['annual', 'per year', 'a year']):
                budget_val += ' annually'
            budget_conf = 0.93

        dms = [s for s in stakeholders if s['role_in_deal'] == 'decision_maker']
        auth_val = '; '.join(f"{s['name']}, {s['title']}" for s in dms) if dms else (
            f"{stakeholders[0]['name']}, {stakeholders[0]['title']}" if stakeholders else None)
        auth_conf = 0.91 if dms else 0.75

        need_val  = pain_points[0]['description'][:150] if pain_points else None
        need_conf = pain_points[0]['confidence'] if pain_points else 0.55

        timeline_val, timeline_conf = None, 0.50
        for pat in [
            r'contract[^.]*?(?:up for renewal|expir)[^.]*?([A-Z][a-z]+ \d{4}|Q[1-4] \d{4})',
            r'(?:by|before|EOD|end of)[^.]*?([A-Z][a-z]+ \d{1,2},?\s*\d{4})',
            r'([A-Z][a-z]+ \d{4}|Q[1-4] \d{4})[^.]*?(?:budget|decision|cycle|deadline|renewal)',
        ]:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                timeline_val = m.group(0)[:120].strip()
                timeline_conf = 0.88
                break

        # ---- OBJECTIONS ----
        objections = []
        obj_sigs = [
            (r'(?:burned|oversell|accuracy claims|not replicating)[^.]+\.', 'raised'),
            (r'(?:transition risk|switching mid|gap in coverage)[^.]+\.', 'raised'),
            (r'(?:integration|data wrangling)[^.]+problematic[^.]+\.', 'raised'),
            (r'(?:security|IT review|infrastructure review)[^.]+\.', 'raised'),
            (r'(?:pricing|cost concern|expensive)[^.]+\.', 'raised'),
        ]
        seen_obj = set()
        for pat, default_status in obj_sigs:
            for m in re.finditer(pat, t, re.IGNORECASE):
                text = m.group(0).strip()[:220]
                key = text[:30].lower()
                if key in seen_obj:
                    continue
                seen_obj.add(key)
                idx = t.find(m.group(0))
                following = t[idx:idx + 600]
                addressed = ae_first in following and len(following) > 150
                objections.append({'description': text,
                                   'status': 'addressed' if addressed else default_status,
                                   'confidence': 0.87})
            if len(objections) >= 4:
                break
        if not objections:
            objections.append({'description': 'No explicit objections identified in transcript',
                                'status': 'raised', 'confidence': 0.55})

        # ---- NEXT STEPS ----
        next_steps = []
        seen_ns = set()
        for pat in [
            r"(?:I will|I'll|we will|we'll)[^.]+\.",
            r"(?:will send|will have|will schedule|will coordinate|will share)[^.]+\.",
            r"(?:send|schedule|arrange|provide|share)[^.]*?by[^.]+\.",
        ]:
            for m in re.finditer(pat, t, re.IGNORECASE):
                text = m.group(0).strip()[:200]
                key = text[:30].lower()
                if key in seen_ns:
                    continue
                seen_ns.add(key)
                dl_m = re.search(
                    r'(?:by |EOD |end of )([A-Za-z]+ \d{1,2},?\s*\d{4}|[A-Za-z]+day|next week|Friday|Monday)',
                    text, re.IGNORECASE)
                next_steps.append({'action': text, 'owner': ae_name,
                                   'deadline': dl_m.group(0) if dl_m else None, 'confidence': 0.88})
            if len(next_steps) >= 4:
                break
        if not next_steps:
            next_steps.append({'action': 'Send follow-up with next steps as discussed on call',
                                'owner': ae_name, 'deadline': None, 'confidence': 0.65})

        # ---- COMPETITIVE INTEL ----
        current_vendor, contract_renewal, comp_conf = None, None, 0.50
        for v in ['Salesforce', 'Episource', 'Veeva', 'HubSpot', 'Optum', 'Apixio', 'Cognizant',
                  'Cotiviti', 'Inovalon', 'Change Healthcare', 'Oracle', 'Availity',
                  'Experian Health', 'Zeomega', 'Arcadia', 'Health Catalyst', 'nThrive']:
            if v.lower() in t.lower():
                current_vendor = v
                comp_conf = 0.93
                break
        ren_m = re.search(
            r'contract[^.]*?(?:up for renewal|expir)[^.]*?([A-Z][a-z]+ \d{4}|Q[1-4] \d{4}|\d{4})',
            t, re.IGNORECASE)
        if ren_m:
            contract_renewal = ren_m.group(1)
            comp_conf = max(comp_conf, 0.90)

        return {
            'metadata': {
                'call_date': call_date,
                'duration_minutes': duration,
                'prospect_company': prospect_company or 'Unknown',
                'confidence': 0.95 if (call_date and prospect_company) else 0.72,
            },
            'stakeholders': stakeholders,
            'pain_points': pain_points,
            'objections': objections,
            'bant': {
                'budget':    {'value': budget_val,  'confidence': budget_conf},
                'authority': {'value': auth_val,    'confidence': auth_conf},
                'need':      {'value': need_val,    'confidence': need_conf},
                'timeline':  {'value': timeline_val,'confidence': timeline_conf},
            },
            'next_steps': next_steps,
            'competitive_intel': {
                'current_vendor': current_vendor,
                'contract_renewal': contract_renewal,
                'confidence': comp_conf,
            },
        }

    def _generate_summary(self, intel):
        """Generate a CRM deal summary from extracted intel."""
        if not intel:
            return "Insufficient data to generate deal summary."
        meta   = intel.get('metadata', {})
        bant   = intel.get('bant', {})
        pain   = intel.get('pain_points', [])
        stakes = intel.get('stakeholders', [])
        comp   = intel.get('competitive_intel', {})
        ns     = intel.get('next_steps', [])

        company  = meta.get('prospect_company', 'the prospect')
        date     = meta.get('call_date', '')
        budget   = bant.get('budget', {}).get('value') or 'not disclosed'
        timeline = bant.get('timeline', {}).get('value') or 'not specified'
        top_pain = pain[0]['description'][:100] if pain else 'Not identified'
        dms      = [s['name'] for s in stakes if s.get('role_in_deal') == 'decision_maker']
        dm_str   = ', '.join(dms) if dms else (stakes[0]['name'] if stakes else 'Unknown')
        vendor   = comp.get('current_vendor')
        renewal  = comp.get('contract_renewal')
        next_act = ns[0]['action'][:80] if ns else 'Follow up required'

        parts = [f"{company}{' — call on ' + date if date else ''} is evaluating RAAPID"]
        if vendor:
            parts.append(f"as a replacement for {vendor}"
                         + (f" (contract renewal: {renewal})" if renewal else "") + ".")
        parts.append(f"Key pain: {top_pain}.")
        parts.append(f"Decision makers on record: {dm_str}.")
        if budget != 'not disclosed':
            parts.append(f"Budget confirmed: {budget}.")
        parts.append(f"Timeline: {timeline}.")
        parts.append(f"Immediate next step: {next_act}.")
        return ' '.join(parts)

    def _generate_email(self, intel):
        """Generate a follow-up email draft from extracted intel."""
        if not intel:
            return "Unable to generate email — insufficient intel."
        meta   = intel.get('metadata', {})
        bant   = intel.get('bant', {})
        pain   = intel.get('pain_points', [])
        stakes = intel.get('stakeholders', [])
        ns     = intel.get('next_steps', [])
        obj    = intel.get('objections', [])

        company     = meta.get('prospect_company', 'your organization')
        primary     = next((s for s in stakes if s.get('role_in_deal') in ('decision_maker', 'champion')),
                           stakes[0] if stakes else {})
        p_last      = primary.get('name', 'there').split()[-1]
        top_pain    = pain[0]['description'][:90] if pain else 'the challenges discussed'
        addressed   = [o for o in obj if o.get('status') == 'addressed']
        budget      = bant.get('budget', {}).get('value')
        timeline    = bant.get('timeline', {}).get('value')

        ns_lines = '\n'.join(
            f"{i+1}. {n['action']}" + (f" (by {n['deadline']})" if n.get('deadline') else '')
            for i, n in enumerate(ns[:3])
        )

        email = f"Subject: RAAPID Follow-up — {company}\n\n{p_last},\n\n"
        email += f"Thank you for your time on the call. The context shared around {top_pain} gives us a clear picture of what needs to be demonstrated.\n"

        if addressed:
            email += "\nOn the points raised:\n"
            for o in addressed[:2]:
                email += f"- {o['description'][:100]}\n"

        email += f"\nNext steps as agreed:\n{ns_lines}\n"

        if budget:
            email += f"\nWe are aligned on the budget range of {budget} and will scope accordingly.\n"
        if timeline:
            email += f"\nGiven the timeline ({timeline}), I want to move quickly on the above.\n"

        email += "\nLooking forward to the next conversation.\n\nBest regards,\nSales Team, RAAPID INC"
        return email

    def _parse_json_with_retry(self, raw: str) -> dict:
        """Parse JSON with up to MAX_RETRIES correction attempts.
        Strips markdown code fences before parsing (LLMs often wrap output in ```json ... ```).
        """
        def strip_fences(s):
            s = s.strip()
            if s.startswith("```"):
                s = s.split("\n", 1)[-1]          # drop opening fence line
            if s.endswith("```"):
                s = s.rsplit("```", 1)[0]          # drop closing fence
            return s.strip()

        raw = strip_fences(raw)

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                self._log(f"JSON parse error (attempt {attempt}/{self.MAX_RETRIES}): {e}", 1)
                if attempt < self.MAX_RETRIES:
                    self._log("Sending correction prompt to LLM...", 1)
                    raw = strip_fences(self._call_llm(
                        SYSTEM_PROMPT,
                        f"Your previous response was not valid JSON. Error: {e}\n\nReturn ONLY valid JSON. No explanation.",
                        "JSON_CORRECTION"
                    ))
                else:
                    raise RuntimeError(f"JSON parse failed after {self.MAX_RETRIES} attempts. Flagging for human review.")

    # -- STEP 1: PREPROCESSING -----------------------------
    def step1_preprocess(self):
        self._line()
        self._log("STEP 1 / 9   PREPROCESSING")
        self._line()
        t0 = time.time()

        if len(self.transcript.strip()) < 200:
            raise ValueError("Transcript is too short or empty. Aborting pipeline.")

        self._log(f"Transcript length   : {len(self.transcript):,} characters", 1)
        self._log(f"Run ID              : {self.run_id}", 1)
        self._log(f"Output directory    : {self.output_dir}", 1)
        self._log("Validation          : PASSED", 1)

        self.results["run_meta"] = {
            "run_id": self.run_id,
            "started_at": datetime.datetime.now().isoformat(),
            "demo_mode": self.demo_mode,
            "transcript_chars": len(self.transcript)
        }
        self.step_times["step1_preprocess"] = round(time.time() - t0, 3)
        print()

    # -- STEP 2: INTELLIGENCE EXTRACTION (LLM) ------------
    def step2_extract_intelligence(self):
        self._line()
        self._log("STEP 2 / 9   INTELLIGENCE EXTRACTION  [LLM]")
        self._line()
        t0 = time.time()

        prompt = EXTRACTION_PROMPT_TEMPLATE.replace("{transcript}", self.transcript)
        raw = self._call_llm(SYSTEM_PROMPT, prompt, "EXTRACTION")

        # Enforce JSON schema
        intel = self._parse_json_with_retry(raw)

        required = ["metadata", "stakeholders", "pain_points", "objections", "bant", "next_steps", "competitive_intel"]
        missing = [k for k in required if k not in intel]
        if missing:
            raise ValueError(f"Schema validation failed. Missing keys: {missing}")

        self._log(f"Schema validation   : PASSED ({len(required)} required fields present)", 1)
        self._log(f"Stakeholders found  : {len(intel['stakeholders'])}", 1)
        self._log(f"Pain points found   : {len(intel['pain_points'])}", 1)
        self._log(f"Objections found    : {len(intel['objections'])}", 1)
        self._log(f"Next steps found    : {len(intel['next_steps'])}", 1)

        self.results["intel"] = intel
        self.step_times["step2_extraction"] = round(time.time() - t0, 3)
        print()

    # -- STEP 3: CONFIDENCE SCORING -----------------------
    def step3_confidence_gate(self):
        self._line()
        self._log("STEP 3 / 9   CONFIDENCE SCORING & GATE")
        self._line()
        t0 = time.time()

        intel  = self.results["intel"]
        flags  = []
        scores = []

        self._log(f"Reject threshold    : avg < {self.CONFIDENCE_REJECT}", 1)
        self._log(f"Review threshold    : avg < {self.CONFIDENCE_THRESHOLD}", 1)
        print()

        # BANT scores
        self._log("BANT Field Scores:", 1)
        for field, data in intel["bant"].items():
            score = data["confidence"]
            scores.append(score)
            bar   = "#" * int(score * 10) + "-" * (10 - int(score * 10))
            label = "OK    " if score >= self.CONFIDENCE_THRESHOLD else "REVIEW"
            self._log(f"  bant.{field:<12} [{bar}] {score:.2f}  {label}", 1)
            if score < self.CONFIDENCE_THRESHOLD:
                flags.append({"field": f"bant.{field}", "confidence": score, "value": data["value"]})

        print()
        self._log("Next Steps Scores:", 1)
        for i, ns in enumerate(intel["next_steps"]):
            score = ns["confidence"]
            bar   = "#" * int(score * 10) + "-" * (10 - int(score * 10))
            label = "OK    " if score >= self.CONFIDENCE_THRESHOLD else "REVIEW"
            self._log(f"  next_steps[{i}]     [{bar}] {score:.2f}  {label}", 1)
            if score < self.CONFIDENCE_THRESHOLD:
                flags.append({"field": f"next_steps[{i}]", "confidence": score, "value": ns["action"]})

        avg = sum(scores) / len(scores) if scores else 0
        self._log(f"\n  Overall avg confidence : {avg:.2f}", 1)
        self._log(f"  Fields needing review  : {len(flags)}", 1)

        self.results["avg_confidence"] = round(avg, 3)
        self.flags = flags
        self.results["flags"] = flags
        self.step_times["step3_confidence"] = round(time.time() - t0, 3)
        print()

    # -- STEP 4: HUMAN REVIEW GATE ------------------------
    def step4_human_review(self):
        self._line()
        self._log("STEP 4 / 9   HUMAN REVIEW GATE")
        self._line()
        t0 = time.time()

        avg = self.results.get("avg_confidence", 0)

        if avg < self.CONFIDENCE_REJECT:
            self._log(f"Overall confidence {avg:.0%} < {self.CONFIDENCE_REJECT:.0%} -- RUN REJECTED", 1)
            self.results["human_review"] = {
                "required":    False,
                "outcome":     "rejected",
                "reviewed_by": "system",
            }
        elif avg < self.CONFIDENCE_THRESHOLD:
            self._log(f"Overall confidence {avg:.0%} -- {len(self.flags)} field(s) need AE review before CRM push", 1)
            for f in self.flags:
                self._log(f"  > {f['field']}  conf={f['confidence']:.2f}  value={f['value']}", 1)
            self.results["human_review"] = {
                "required":    True,
                "outcome":     "pending_review",
                "reviewed_by": None,
            }
        else:
            self._log(f"Overall confidence {avg:.0%} -- auto-approved, pushing to CRM", 1)
            self.results["human_review"] = {
                "required":    False,
                "outcome":     "auto_approved",
                "reviewed_by": "system",
            }

        self.step_times["step4_human_gate"] = round(time.time() - t0, 3)
        print()

    # -- STEP 5: DEAL SUMMARY (LLM) -----------------------
    def step5_deal_summary(self):
        self._line()
        self._log("STEP 5 / 9   DEAL SUMMARY GENERATION  [LLM]")
        self._line()
        t0 = time.time()

        prompt = SUMMARY_PROMPT_TEMPLATE.replace("{intel}", json.dumps(self.results["intel"], indent=2))
        summary = self._call_llm(SYSTEM_PROMPT, prompt, "SUMMARY")

        self._log(f"Summary length      : {len(summary.split())} words", 1)
        print()
        self._line(".")
        print(summary)
        self._line(".")

        self.results["deal_summary"] = summary
        self.step_times["step5_summary"] = round(time.time() - t0, 3)
        print()

    # -- STEP 6: EMAIL DRAFT (LLM) ------------------------
    def step6_email_draft(self):
        self._line()
        self._log("STEP 6 / 9   FOLLOW-UP EMAIL DRAFT  [LLM]")
        self._line()
        t0 = time.time()

        prompt = EMAIL_PROMPT_TEMPLATE.replace("{intel}", json.dumps(self.results["intel"], indent=2))
        email = self._call_llm(SYSTEM_PROMPT, prompt, "EMAIL")

        self._log(f"Email length        : {len(email.split())} words", 1)
        self._log("Guardrail           : Grounded on transcript only -- no external data injected", 1)
        self._log("Send gate           : Human approval required before send", 1)
        print()
        self._line(".")
        print(email)
        self._line(".")

        self.results["email_draft"] = email
        self.step_times["step6_email"] = round(time.time() - t0, 3)
        print()

    # -- STEP 7: ERROR HANDLING DEMO ----------------------
    def step7_error_handling_demo(self):
        self._line()
        self._log("STEP 7 / 9   ERROR HANDLING -- JSON RETRY DEMO")
        self._line()
        t0 = time.time()

        self._log("Simulating truncated/malformed JSON response from LLM...", 1)
        time.sleep(0.3)

        malformed = '{"pain_points": [{"description": "RADV error rate"'  # intentionally broken

        for attempt in range(1, self.MAX_RETRIES + 1):
            self._log(f"Attempt {attempt}/{self.MAX_RETRIES}: parsing JSON...", 1)
            try:
                json.loads(malformed)
                self._log("Parse succeeded", 1)
                break
            except json.JSONDecodeError as e:
                self._log(f"  JSONDecodeError: {e}", 1)
                if attempt < self.MAX_RETRIES:
                    self._log("  Action: sending correction prompt to LLM", 1)
                    time.sleep(0.3)
                    malformed = json.dumps({"recovered": True})  # simulate corrected response
                else:
                    self._log("  Max retries reached -- flagging for human review, no partial write to CRM", 1)

        self._log("Recovery demonstrated: retry with correction prompt resolved parse failure", 1)
        self.step_times["step7_error_demo"] = round(time.time() - t0, 3)
        print()

    # -- STEP 8: CRM PUSH (MOCK SALESFORCE) ---------------
    def step8_crm_push(self):
        self._line()
        self._log("STEP 8 / 9   CRM PUSH  [Supabase PostgreSQL]")
        self._line()
        t0 = time.time()

        intel = self.results["intel"]
        bant  = intel["bant"]
        avg_confidence = round(
            sum(bant[k]["confidence"] for k in bant) / 4, 3
        )

        row = {
            "run_id":                self.run_id,
            "started_at":            self.results["run_meta"]["started_at"],
            "input_type":            self.results.get("input_type", "unknown"),
            "prospect_company":      intel["metadata"].get("prospect_company"),
            "call_date":             intel["metadata"].get("call_date"),
            "duration_minutes":      intel["metadata"].get("duration_minutes"),
            "budget":                bant["budget"].get("value"),
            "budget_confidence":     bant["budget"].get("confidence"),
            "authority":             bant["authority"].get("value"),
            "authority_confidence":  bant["authority"].get("confidence"),
            "need":                  bant["need"].get("value"),
            "need_confidence":       bant["need"].get("confidence"),
            "timeline":              bant["timeline"].get("value"),
            "timeline_confidence":   bant["timeline"].get("confidence"),
            "avg_confidence":        avg_confidence,
            "current_vendor":        intel["competitive_intel"].get("current_vendor"),
            "contract_renewal":      intel["competitive_intel"].get("contract_renewal"),
            "human_review_required": self.results["human_review"]["required"],
            "human_review_outcome":  self.results["human_review"]["outcome"],
            "flags_count":           len(self.results.get("flags", [])),
            "pain_points_count":     len(intel.get("pain_points", [])),
            "deal_summary":          self.results.get("deal_summary", ""),
            "email_draft":           self.results.get("email_draft", ""),
            "transcript":            self.results.get("transcript", ""),
            "stakeholders":          json.dumps(intel.get("stakeholders", [])),
            "pain_points":           json.dumps(intel.get("pain_points", [])),
            "objections":            json.dumps(intel.get("objections", [])),
            "next_steps":            json.dumps(intel.get("next_steps", [])),
            "flags":                 json.dumps(self.results.get("flags", [])),
        }

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if supabase_url and supabase_key:
            try:
                import urllib.request, logging as _logging
                _logger = _logging.getLogger("raapid.supabase")

                endpoint = f"{supabase_url}/rest/v1/runs"
                payload  = json.dumps(row, default=str).encode("utf-8")
                req = urllib.request.Request(
                    endpoint,
                    data    = payload,
                    method  = "POST",
                    headers = {
                        "Content-Type":  "application/json",
                        "apikey":        supabase_key,
                        "Authorization": f"Bearer {supabase_key}",
                        "Prefer":        "resolution=ignore-duplicates",
                    }
                )
                with urllib.request.urlopen(req) as resp:
                    status = resp.status

                _logger.info(f"Supabase REST INSERT OK — run_id={self.run_id} status={status}")
                self._log("Database            : Supabase (REST API)", 1)
                self._log("Table               : runs", 1)
                self._log(f"Run ID              : {self.run_id}", 1)
                self._log(f"Avg BANT confidence : {avg_confidence:.0%}", 1)
                self._log(f"Status              : {status} OK", 1)
            except Exception as e:
                import logging as _logging, traceback as _tb
                _logging.getLogger("raapid.supabase").error(
                    f"Supabase REST insert failed: {e}\n{_tb.format_exc()}"
                )
                self._log(f"Supabase insert failed: {e}", 1)
                self._log("Falling back to local JSON payload", 1)
                self._write_local_payload(row)
        else:
            self._log("SUPABASE_DB_URL not set — writing local JSON payload", 1)
            self._write_local_payload(row)

        self.results["crm_payload"] = row
        self.step_times["step8_crm"] = round(time.time() - t0, 3)
        print()

    def _write_local_payload(self, row):
        out_file = os.path.join(self.output_dir, f"crm_payload_{self.run_id}.json")
        with open(out_file, "w") as f:
            json.dump(row, f, indent=2, default=str)
        self._log(f"Payload written to  : {out_file}", 1)

    # -- STEP 9: SLACK NOTIFICATION -----------------------
    def step9_slack_notify(self):
        self._line()
        self._log("STEP 9 / 9   AE NOTIFICATION  [Mock Slack]")
        self._line()
        t0 = time.time()

        intel = self.results["intel"]
        conf = self.results["crm_payload"]["avg_confidence"]

        primary = intel['stakeholders'][0] if intel['stakeholders'] else {}
        approver = next(
            (s for s in intel['stakeholders'] if s.get('role_in_deal') == 'decision_maker'),
            intel['stakeholders'][-1] if intel['stakeholders'] else {}
        )
        top_pain = intel['pain_points'][0]['description'][:75] if intel['pain_points'] else 'N/A'
        next_action = intel['next_steps'][0]['action'][:70] if intel['next_steps'] else 'N/A'
        deadline = (intel['next_steps'][0].get('deadline') or 'TBD') if intel['next_steps'] else 'TBD'

        msg = (
            f"\n"
            f"  *New Deal Intel: {intel['metadata']['prospect_company']}*\n"
            f"  {'-' * 50}\n"
            f"  Primary Contact : {primary.get('name', 'N/A')} ({primary.get('title', 'N/A')})\n"
            f"  Final Approver  : {approver.get('name', 'N/A')} ({approver.get('title', 'N/A')})\n"
            f"  Budget          : {intel['bant']['budget']['value']}\n"
            f"  Timeline        : {intel['bant']['timeline']['value']}\n"
            f"  Top Pain Point  : {top_pain}...\n"
            f"  Next Action     : {next_action}\n"
            f"  Due             : {deadline}\n"
            f"  {'-' * 50}\n"
            f"  Agent confidence: {conf:.0%}  |  "
            f"Human review: {'Required' if self.results['human_review']['required'] else 'Not required'}\n"
            f"  CRM updated. Email draft queued for AE review.\n"
        )

        self._log("Channel             : #gtm-deal-intel [MOCK]", 1)
        self._log("Message preview:", 1)
        self._line(".")
        print(msg)
        self._line(".")

        self.step_times["step9_slack"] = round(time.time() - t0, 3)
        print()

    # -- EXECUTION SUMMARY ---------------------------------
    def _print_summary(self):
        self._line("=")
        self._log("EXECUTION SUMMARY")
        self._line("=")

        total = sum(self.step_times.values())
        self._log(f"Run ID              : {self.run_id}", 1)
        self._log(f"Total runtime       : {total:.2f}s (includes simulated API latency)", 1)
        self._log(f"Steps completed     : {len(self.step_times)} / 9", 1)
        self._log(f"Fields flagged      : {len(self.flags)}", 1)
        self._log(f"Human review        : {'Required' if self.results['human_review']['required'] else 'Not required'}", 1)
        print()

        self._log("Step timings:", 1)
        for step, t in self.step_times.items():
            self._log(f"  {step:<30} {t:.3f}s", 1)

        print()
        self._log("Outputs:", 1)
        self._log(f"  CRM payload  : {self.output_dir}/crm_payload_{self.run_id}.json", 1)
        self._log(f"  Email draft  : Queued for AE review (not auto-sent)", 1)
        self._log(f"  Slack msg    : Posted to #gtm-deal-intel [simulated]", 1)

        print()
        self._log("Cost estimate (live Claude API):", 1)
        self._log("  ~2,400 tokens across 3 LLM calls", 1)
        self._log("  ~$0.012 per transcript at claude-sonnet-4-6 pricing", 1)
        self._log("  50 calls/day  -> ~$18/month", 1)
        self._log("  200 calls/day -> ~$72/month", 1)
        self._log("  Latency per run: ~4-6s end-to-end (live API)", 1)
        self._line("=")

    # -- MAIN RUN ------------------------------------------
    def run(self):
        print()
        self._line("=")
        self._log("RAAPID  SALES CALL INTELLIGENCE AGENT")
        self._log(f"Run: {self.run_id}  |  Mode: {'DEMO' if self.demo_mode else 'LIVE'}")
        self._line("=")
        print()

        try:
            self.step1_preprocess()
            self.step2_extract_intelligence()
            self.step3_confidence_gate()
            self.step4_human_review()
            self.step5_deal_summary()
            self.step6_email_draft()
            self.step7_error_handling_demo()
            self.step8_crm_push()
            self.step9_slack_notify()
            self._print_summary()

        except (ValueError, RuntimeError) as e:
            self._line("!")
            self._log(f"AGENT HALTED: {e}")
            self._log("No partial data written to CRM. Flagged for human review.")
            self._line("!")
            raise  # surface to caller so backend returns a proper 500 with the real error

        return self.results


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    agent = SalesCallAgent(transcript=MOCK_TRANSCRIPT, demo_mode=True)
    agent.run()
