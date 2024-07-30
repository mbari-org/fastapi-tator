# Open a csv file and put into a pandas dataframe

import pandas as pd
import os
import time
import requests

cluster_version = "20240205_225539"
df = pd.read_csv(f'/Users/dcline/i2MAPclusters - {cluster_version}".csv')

# Print the first 5 rows of the dataframe
print(df.head())

# Iterate through the rows of the dataframe
# Column Cluster# is the cluster number
# Columne Predominant concept is the Label


for index, row in df.iterrows():
    print(row["Cluster#"], row["Predominant concept"])

    # Run a REST API call to update the cluster number and label in the database, e.g.
    version_name = f"dino_vits8_{cluster_version}"
    url = f"http://i2map.shore.mbari.org:8001/label/filename_cluster/{row['Predominant concept']}"
    headers = {"accept": "application/json", "Content-Type": "application/json", "Authorization": "Bearer YOUR_TOKEN_HERE"}
    data = {
        "filter_media": "Includes",
        "filter_cluster": "Equals",
        "media_name": "_200m_",
        "version_name": version_name,
        "cluster_name": f"Unknown C{row['Cluster#']}",
        "project_name": "i2map",
        "dry_run": True,
    }

    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)  # Print the status code to check if the request was successful

    # Sleep for 30 seconds to avoid rate limiting
    time.sleep(30)
