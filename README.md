## Overview

This scraper is created to collect all possible reviews about companies from the site https://www.indeed.com/. The results are saved into a single CSV file.

Format: Company Name,Review Date,Location City,Location State,Job Title,Employment Status,Overall Rating,Job Work/Life Balance Rating,Compensation/Benefits Rating,Job Security/Advancement Rating,Management Rating,Job Culture Rating,Title, Review

## Config (config.yaml)
```yaml
threads: 30 # Number of threads (it is recommended to use no more than 50)
proxy: username:pass@ip:port # Residential proxy to bypass blocking (rate limit)
urls:
   - https://www.indeed.com/cmp/Spark-Driver-1/reviews
   - https://www.indeed.com/cmp/Teleperformance/reviews
# Links to company pages
```

## Installation:
Required Python 3.10 or higher
```bash
git clone this_repo
cd this_repo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```