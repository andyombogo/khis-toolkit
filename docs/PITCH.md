# County Pitch Outline

Use this with the public `offline_demo` dashboard link. The point is to show the workflow clearly before you ask for KHIS access, not to pretend the public link is already live against Ministry of Health data.

## Before The Call

- Open the public dashboard in one tab and the GitHub repo in another.
- Be ready to say, early, that the public demo uses stable bundled county data by design.
- Frame the ask as a small pilot: one county workflow, one indicator package, read-only access if appropriate.

## Slide 1 - The problem

"Your county generates data every month. But the analysis that should drive decisions often happens weeks later, in Excel, by one person."

- Open with a simple county reporting workflow diagram: facility report -> KHIS upload -> delayed manual analysis.
- Emphasize delay, fragility, and the risk of review meetings happening after the moment to act has already passed.

## Slide 2 - What khis-toolkit does

- Show one screenshot of the county map from the dashboard.
- Say plainly that the public link is an offline demo showing the workflow, not claiming live KHIS integration yet.
- Show one small code block:

```python
import khis
conn = khis.connect()
df = khis.clean(khis.get(conn, "malaria", counties=["Nairobi"], periods="last_12_months"))
```

- Show one forecast chart beside it.
- Keep the language plain: "pulls your county data, cleans it, and turns it into a weekly picture you can act on."

## Slide 3 - What you get

- 4-week disease forecast every Monday morning
- Automated data quality report
- County comparison map updated weekly
- Exportable reports for county health review meetings
- Optional mental-health indicator package once live access is validated

## Slide 4 - What it costs to pilot

- Free for the first county
- Open source
- Runs on a $5/month server
- "We want one real use case from a Kenya county. That is the only thing we are asking for."
- Emphasise that the first live step can be read-only and narrow in scope.

## Slide 5 - Next step

- "Give us 30 minutes and one narrow validation path. We will adapt this demo to your real county workflow."
- Suggested ask:
  - read-only KHIS access if appropriate
  - one county or one program area first
  - confirmation of the right org-unit IDs and indicator names
- Contact: andyombogo@gmail.com
- Location: Nairobi, Kenya

## Talk Track

- "This is already a working county analytics product demo."
- "What is still missing is not the workflow. It is validated live access and metadata confirmation."
- "I am asking for the smallest useful next step so we can prove value safely."
