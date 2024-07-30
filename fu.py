import pandas as pd

# Sample DataFrame
# data = {'instance': [1, 1, 2, 2, 3, 3, 4, 4],
#         'label': ['X', 'Y', 'X', 'Z', 'Y', 'Z', 'X', 'Y']}
data = {
    "instance": [
        1,
        1,
        1,
        1,
        2,
        2,
    ],
    "label": ["X", "X", "Y", "Y", "Y", "Z"],
}
df = pd.DataFrame(data)

# Group by 'instance', count occurrences, and find the label with the maximum count
max_labels = df.groupby("instance")["label"].apply(lambda x: x.value_counts().idxmax()).reset_index(name="max_label")

# Display the maximum labels per instance
print(max_labels)

for index, row in max_labels.iterrows():
    print(f"Instance {row['instance']} has the maximum label '{row['max_label']}'")
