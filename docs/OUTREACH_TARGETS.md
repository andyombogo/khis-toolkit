# Outreach Targets

Use this alongside [KHIS_OUTREACH_EMAIL.md](KHIS_OUTREACH_EMAIL.md) and [PITCH.md](PITCH.md).

The goal at this stage is a **narrow first conversation**, not a broad integration ask. Lead with the demo link, explain offline mode, and ask for the smallest useful next step.

---

## Tier 1 — Highest Priority (KHIS Access and Validation)

### Kenya Ministry of Health — KHIS Support

- **Contact**: khissupport@health.go.ke
- **What to ask**: Read-only KHIS access for one county or one indicator package to validate org-unit IDs and indicator naming.
- **Why now**: The demo is stable. The specific gap is correct org-unit IDs — placeholder IDs are clearly marked in the code and the README is honest about this.
- **Talking point**: The toolkit already understands Kenya county structure, period formats, and KHIS cleaning quirks. What is missing is live metadata confirmation.
- **Template**: [KHIS_OUTREACH_EMAIL.md — Short Version](KHIS_OUTREACH_EMAIL.md)

### Kenya Ministry of Health — Division of Health Informatics

- **Contact**: Find via the MoH digital health portal or LinkedIn search for "health informatics Kenya Ministry of Health".
- **What to ask**: A 20-minute conversation about the toolkit and whether it fits any county review or digital health workflows they are currently piloting.
- **Why this team**: The Division of Health Informatics sits between KHIS infrastructure and county use. They can advise on correct entry points and are more likely to respond to a workflow demo than a generic access request.

---

## Tier 2 — Research and NGO Partners

### Aga Khan University — Faculty of Health Sciences / AKU-AIMS

- **Contact**: andyombogo@gmail.com is already associated with AKU. Use internal channels directly.
- **What to ask**: Research collaboration — use of the toolkit in a county health analytics project or grant methodology section.
- **Why AKU**: AKU runs AIMS (AKU Institute for Management Sciences) and has existing county health partnerships, especially in Nairobi and Mombasa. The mental-health workflow is directly relevant to AKU's global mental health research portfolio.
- **Talking point**: "I built this as the reproducible data-engineering layer for county health workflows. It can support exploratory research, review meetings, and grant reporting in the same pipeline."

### Amref Health Africa — Data and Analytics Team

- **Website**: amref.org
- **Contact**: Use the contact page or LinkedIn search for Amref data/analytics leads in Nairobi.
- **What to ask**: Whether the toolkit can support any of their county health indicator work in Kenya, particularly malaria or mental health programs.
- **Why Amref**: Amref runs large county-level health programs in Kenya and uses DHIS2 data routinely. They have in-country analytics capacity and are receptive to open-source tools.

### Kenya Health Informatics Association (KeHIA)

- **Website**: kehia.or.ke
- **Contact**: info@kehia.or.ke or LinkedIn.
- **What to ask**: Feedback from KHIS practitioners and potentially a short presentation slot at a KeHIA event or webinar.
- **Why KeHIA**: KeHIA connects health records officers, informaticists, and county HIS teams. These are the practitioners who would use the toolkit daily. One positive mention in their network is worth more than a Ministry approval for adoption.

---

## Tier 3 — International and Academic

### WHO AFRO — Health Information and Data Analytics

- **Website**: afro.who.int
- **Contact**: afrodata@who.int or use the WHO directory for the Kenya country office.
- **What to ask**: Whether the toolkit or the county-level forecasting workflow aligns with any WHO AFRO analytics or digital health priorities.
- **Why WHO AFRO**: WHO AFRO supports DHIS2 implementations across Africa and publishes county-level health analytics. A Kenya-first toolkit that is open source and already demonstrates quality checks and forecasting is relevant to their work.
- **Caveat**: WHO moves slowly. Frame this as a research collaboration introduction, not a product pitch.

### PATH Kenya — Digital Health Team

- **Website**: path.org/countries/kenya
- **Contact**: LinkedIn search for PATH Kenya digital health or data leads.
- **What to ask**: Whether PATH Kenya's digital health programs use DHIS2 analytics that the toolkit could support.
- **Why PATH**: PATH Kenya has active digital health and malaria programs and has worked with KHIS data. They are a credible reference partner if they find the toolkit useful.

### Global Fund — Kenya Country Team

- **What to ask**: Not a direct technology conversation — this is about methodology. The toolkit's quality scorecard and forecasting approach are relevant to Global Fund malaria grant reporting workflows.
- **Entry point**: Through AKU or Amref relationships, not a cold contact.

---

## Outreach Order Recommendation

1. **MoH KHIS support** (khissupport@health.go.ke) — submit the narrow access request using the existing email draft.
2. **AKU internal channels** — start a research collaboration conversation that uses the toolkit as the analytics layer.
3. **KeHIA** — get practitioner feedback and a community introduction.
4. **Amref** — once the toolkit has one practitioner endorsement, this conversation is easier.
5. **WHO AFRO and PATH** — after live KHIS access is confirmed and the workflow is validated.

---

## What to Have Ready Before Any Outreach

- Public demo link: https://khis-toolkit.streamlit.app (offline_demo, stable)
- GitHub repo: https://github.com/andyombogo/khis-toolkit
- [PITCH.md](PITCH.md) walkthrough order
- [KHIS_OUTREACH_EMAIL.md](KHIS_OUTREACH_EMAIL.md) for the initial ask
- A 15–20 minute live demo slot prepared, with the dashboard open and the county selector set to a recognisable county (Nairobi for city teams, Kisumu or Mombasa for coastal/nyanza partners)
