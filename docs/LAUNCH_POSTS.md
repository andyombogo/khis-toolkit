# Launch Posts

Replace `https://khis-toolkit-dashboard.onrender.com` if Render assigns a different live URL after the first deploy.

## LinkedIn

Kenya county health teams still rely on DHIS2 every day, but the Python tooling around DHIS2 has gone quiet, generic, or both.

I'm John Andrew, a data scientist in Nairobi, and I built `khis-toolkit` because I needed a Kenya-first workflow that could go from DHIS2 extraction to cleaning, quality checks, forecasting, and dashboarding without stitching together half-maintained packages every time.

Three lines is enough to start:

```python
import khis
conn = khis.connect()
df = khis.get(conn, "malaria", counties=["Nairobi"], periods="last_12_months")
```

GitHub: https://github.com/andyombogo/khis-toolkit  
Live demo: https://khis-toolkit-dashboard.onrender.com

If you work in county health records, DHIS2 support, NGO analytics, or public health delivery in Kenya, I’d love your feedback on what should come next.

#Kenya #PublicHealth #OpenSource #DataScience

## Twitter/X

Built `khis-toolkit` because Kenya DHIS2 work deserves better Python tooling than abandoned generic wrappers. It pulls, cleans, checks quality, forecasts, and maps county health data in one workflow.  
GitHub: https://github.com/andyombogo/khis-toolkit  
Live demo: https://khis-toolkit-dashboard.onrender.com  
#Kenya #PublicHealth #OpenSource #DataScience
