#!/usr/bin/env python3
"""
Script to sort podcast episodes chronologically and add episode numbers.
Reverses the current order (newest first) to oldest first and adds episode_number column.
"""

import pandas as pd
import os

def sort_podcast_episodes():
    """
    Read episodes.csv, reverse the order to put oldest episodes first,
    add episode_number column starting from 1, and save the result.
    """
    
    # Read the current episodes.csv file
    print("Reading episodes.csv...")
    df = pd.read_csv('episodes.csv') 

    df_copy = df.copy() 
    
    print(f"Found {len(df)} episodes")
    print(f"Current order: {df.iloc[0]['episode_url']} (first row)")
    print(f"Current order: {df.iloc[-1]['episode_url']} (last row)")
    
    # Reverse the order to put oldest episodes first
    print("\nReversing episode order...")
    df_reversed = df_copy.iloc[::-1].reset_index(drop=True)
    
    print(f"After reversal: {df_reversed.iloc[0]['episode_url']} (first row)")
    print(f"After reversal: {df_reversed.iloc[-1]['episode_url']} (last row)")
    
    # Add episode_number column starting from 1
    print("\nAdding episode_number column...")
    df_reversed['episode_number'] = range(1, len(df_reversed) + 1)
    
    # Save the result
    output_file = 'sorted_episodes.csv'
    print(f"\nSaving to {output_file}...")
    df_reversed.to_csv(output_file, index=False)
    
    print(f"Successfully created {output_file} with {len(df_reversed)} episodes")
    print(f"Episode numbers range from 1 to {len(df_reversed)}")
    
    # Show first few rows as verification
    print("\nFirst 5 episodes:")
    print(df_reversed[['episode_number', 'episode_url']].head())
    
    # Show last few rows as verification
    print("\nLast 5 episodes:")
    print(df_reversed[['episode_number', 'episode_url']].tail())

if __name__ == "__main__":
    # Check if episodes.csv exists
    if not os.path.exists('episodes.csv'):
        print("Error: episodes.csv not found in current directory")
        exit(1)
    
    try:
        sort_podcast_episodes()
        print("\nScript completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1) 