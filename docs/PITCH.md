# County Pitch Outline

## Slide 1 - The problem

"Your county generates data every month. But the analysis that should drive decisions often happens weeks later, in Excel, by one person."

- Open with a simple county reporting workflow diagram: facility report -> KHIS upload -> delayed manual analysis.
- Emphasize delay, fragility, and the risk of review meetings happening after the moment to act has already passed.

## Slide 2 - What khis-toolkit does

- Show one screenshot of the county map from the dashboard.
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

## Slide 4 - What it costs to pilot

- Free for the first county
- Open source
- Runs on a $5/month server
- "We want one real use case from a Kenya county. That is the only thing we are asking for."

## Slide 5 - Next step

- "Give us 30 minutes and your KHIS credentials. We will show you your own county's malaria forecast for the next 4 weeks."
- Contact: andyombogo@gmail.com
- Location: Nairobi, Kenya
