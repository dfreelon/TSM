# This is a test file for the TSM Python module by Deen Freelon <dfreelon@gmail.com>. For all functions to operate as intended, you need at least one CSV file containing Twitter data to use as input. (You can use the same file for tweet_file_A and tweet_file_B, in which case match_communities will compare two separate runs of the Louvain method on that file to each other.) Unfortunately, Twitter's terms of service prevent me from making these publicly available. However, you can pull your own Twitter data using Martin Hawksey's excellent Google-spreadsheet-based TAGS system, which requires no code: http://mashe.hawksey.info/2013/02/twitter-archive-tagsv5/
# For instructions on how to format your data files and what the functions below output, see tsm.py which is available at https://github.com/dfreelon/TSM

import tsm

# change the next two lines, obviously

tweet_file_A = '/path/to/properly_formatted_A.csv'
tweet_file_B = '/path/to/properly_formatted_B.csv'
edgelist_A = tsm.t2e(tweet_file_A)
edgelist_B = tsm.t2e(tweet_file_B)
top_communities_A = tsm.get_top_communities(edgelist_A)
top_communities_B = tsm.get_top_communities(edgelist_B)
ei_indices_A = tsm.calc_ei(top_communities_A,edgelist_A)
ei_indices_B = tsm.calc_ei(top_communities_B,edgelist_B)
top_rts_A = tsm.get_top_rts(tweet_file_A,top_communities_A)
top_rts_B = tsm.get_top_rts(tweet_file_B,top_communities_B)
community_matches = tsm.match_communities(top_communities_A,top_communities_B)
intermediaries_A = get_intermediaries(top_communities_A,edgelist_A)
intermediaries_B = get_intermediaries(top_communities_B,edgelist_B)
top_hashtags_A = get_top_hashtags(tweet_file_A,top_communities_A)
top_hashtags_B = get_top_hashtags(tweet_file_B,top_communities_B)
top_links_A = get_top_links(tweet_file_A,top_communities_A)
top_links_B = get_top_links(tweet_file_B,top_communities_B)
grid_A = shared_ties_grid(ei_indices_A,calc_propor=True)
grid_B = shared_ties_grid(ei_indices_B,calc_propor=True)

print("Now feel free to inspect the variables...")
''' Use the following code to inspect grid_A and grid_B:

for line in grid_A:
    print(line)

for line in grid_B:
    print(line)
'''
