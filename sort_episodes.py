import os  
import pandas as pd 



# series = pd.read_csv("episodes.csv") 



# series_copy = series.copy() 

# # Extract episode numbers from URLs using string operations
# series_copy['episode_number'] = series_copy['episode_url'].str.extract(r'podcast-(\d+)|/(\d+)-').fillna('').sum(axis=1)

# # Convert to numeric, handling non-numeric values
# series_copy['episode_number'] = pd.to_numeric(series_copy['episode_number'], errors='coerce')


# # Sort by episode number and reset index to match episode numbers
# series_copy = series_copy.sort_values('episode_number').reset_index(drop=True)

# # Add 1 to index to start from 1 instead of 0
# series_copy.index = series_copy.index + 1

# print("Episodes sorted and reindexed to match episode numbers")
# print(series_copy.head())


series_sorted = pd.read_csv("sorted_episodes.csv")  


series_episode_number_null = series_sorted[series_sorted['episode_number'].isnull()]  


pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

print(series_episode_number_null) 







