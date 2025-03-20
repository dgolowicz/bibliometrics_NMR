# Interactive Dashboard app

This repo contains an interactive online dashboard for visualizing the data related to papers where *Nuclear Magnetic Resonance* has been mentioned in the paper's title or abstract.
The repo is deployment-ready but does not include the SQLite database itself. However, one can recreate database file by fetching specific data from PubMed and OpenAlex following instructions published in the complementary repository https://github.com/dgolowicz/bibliometrics_NMR_data_prep

**To try out the running app and read more about this project, you are encouraged to visit https://darekds.com/dashboardnmr/**
![collaborators](https://github.com/user-attachments/assets/27871c0f-14d0-48b0-bc5a-4645a1de092e)





## Runinng Dashboard locally
To run the dashboard locally:
1. clone the repo
2. install required libraries as listed in the requirements.txt (gunicorn and flask are not required)
3. prepare data.db file following instructions from **bibliometrics_NMR_data_prep** repository. This step involves fetching data from PubMed and OpenAlex and may be lengthy.
4. put your data.db into /var/data or another directory, but make sure the correct path is set in ./app.py in the line DB_FILE = '/var/data/data.db'
5. run app.py
6. go to http://0.0.0.0:8080/ in the browser
7. your dashboard is ready to use
