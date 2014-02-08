#!/usr/bin/python3

# TSM (Twitter Subgraph Manipulator) for Python 3
# release 1 (02/08/14)
# (c) 2014 by Deen Freelon <dfreelon@gmail.com>
# Distributed under the BSD 3-clause license. See LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause for details.

# This Python module contains a set of functions that create and manipulate network communities (subgraphs) in various ways. I created it to work with Twitter networks, but only t2e and get_top_rts are Twitter-specific. This module is intended for use with long-tailed, extremely sparse networks like those commonly found on the web. It functions only with Python 3.x and is not backwards-compatible. Here's a brief list of the functions and what each does:

# Warning: TSM performs very little custom error-handling, so make sure your inputs are formatted properly! If you have questions, please let me know via email.

# FUNCTION LIST

# load_file: Loads files quickly

# save_csv: Quick CSV output

# t2e: Converts raw tweets into edgelist format (retweets and @-mentions, not follows)

# get_top_communities: A wrapper for Thomas Aynaud's implementation of the Louvain method for community detection. Gets the top N largest communities by membership in a network and then outputs a file/variable containing the community labels and in-degrees of each user.

# calc_ei: Calculates the E-I index (a measure of insularity) of each community detected by get_top_communities.

# _get_community_overlap: An extension of calc_ei that shows how "close" each community is to all of the others in terms of shared ties

# get_top_rts: Gets the most-retweeted tweets within each community

# match_communities: Compares community membership within two networks, A and B, and gives the best match found in B for each community in A

# MODULE-WIDE VARIABLES (these need to remain the same for all functions in this module)

#The var below, top_comm, is an integer representing the top N communities by node population. These will be the communities which this module's functions will manipulate. For large Twitter networks, I have found it fruitful to work with the top ten largest retweet or @-mention communities. Other things being equal, top_comm should be roughly correlated with processing time.

top_comm = 10

#Change the text encoding below. If 'utf-8' produces garbage characters and your data are in English, try 'latin1'

enc = 'utf-8'

# REQUIRED MODULES

#Below are all the dependencies this module requires. Everything except NetworkX and community.py comes standard with Python. You can get NetworkX here: http://networkx.github.io/ . Beware, it can be a bit tricky to install. You'll also need Thomas Aynaud's implementation of the Louvain method for community detection, but you must use the version I modified to work with Python 3 (community3.py)--otherwise the only TSM function that will work is t2e. (Aynaud's original 2.x-compliant version is available here: http://perso.crans.org/aynaud/communities/) 

import csv
import re
import community3
import networkx as nx
import random

# FUNCTIONS

# load_file and save_csv are mostly self-explanatory. load_file accepts both strings representing file paths and variables. Either must contain the expected internal structure for the function to work properly.

def load_file(data):
    if type(data) is str:
        csv_out = []
        with open(data,'r',encoding = enc) as f:
            reader = csv.reader(f)
            for row in reader:
                csv_out.append(row)
        return csv_out
    else:
        return data

def save_csv(outfile,data):
    with open(outfile,'w',encoding = enc) as out: 
        for line in data:
            row = ','.join(line) + "\n"
            out.write(row)

# t2e: convert raw Twitter data to edgelist format
# Description: t2e takes raw Twitter data as input and outputs an edgelist consisting of the names of the tweet authors (col 1) and the names of the users mentioned and/or retweeted (col 2). 
# Arguments: 
    # tweets_file: a path to a CSV file (the only delimiter currently allowed is commas) with tweet authors listed in col 1 and corresponding tweet text in col 2. If col 1 contains text, col 2 must as well, and vice versa.
    # extmode: see below
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_edgelist.csv
# Output: An edgelist in the form of a Python list of lists. If save_prefix is set, the edgelist will also be saved as a CSV file.

# t2e has four extraction modes (specified by the extmode variable). Default is ALL.
# ALL = do not differentiate between retweets and non-retweets, include isolates (default)
# ALL_NO_ISOLATES = do not differentiate between retweets and non-retweets, exclude isolates
# RTS_ONLY = retweets only, exclude isolates
# AT_MENTIONS_ONLY = non-retweets (@-mentions) only, exclude isolates
    
def t2e(tweets_file,extmode='ALL',save_prefix=''):
    
    g_src = []
    g_tmp = []
    
    with open(tweets_file,'r',encoding = enc) as f:
        reader = csv.reader(f)
        for row in reader:
            if extmode == 'ALL_NO_ISOLATES':
                condition = row[1].find('@')>-1
            elif extmode == 'RTS_ONLY':
                condition = row[1].find('RT @')>-1
            elif extmode == 'AT_MENTIONS_ONLY':
                condition = row[1].find('@')>-1 and row[1].find('RT @')==-1
            else:
                condition = True
            if condition is True:
                g_src.append(row[0].lower().strip())
                g_tmp.append(' ' + row[1] + ' ')

    g_tmp = [t.split('@') for t in g_tmp] #splits each tweet along @s
    g_trg = [[t[:re.search('[^A-Za-z0-9_]',t).start()].lower().strip() for t in chunk if re.search('[^A-Za-z0-9_]',t) is not None] for chunk in g_tmp] #strips out everything after the @ sign and trailing colons, leaving (hopefully) a list of lists of usernames
    for line in g_trg:
        if len(line) > 1 and line[0] == '': #removes blank entries from lines mentioning at least one name
            del line[0]

    final = []
    i = 0

    if extmode == 'RTS_ONLY':
        for olist in g_trg: #creates final output list
            if len(g_src[i] + olist[0]) > len(g_src[i]):
                final.append([g_src[i],olist[0]]) #ensures that only the RTed user is captured
            i+=1
    else:
        for olist in g_trg: 
            for name in olist: #captures multiple names per tweet where applicable
                if len(g_src[i] + name) > len(g_src[i]):
                    final.append([g_src[i],name])
            i+=1
    
    if len(save_prefix) > 0:
        outfile = tweets_file + '_edgelist.csv'
        save_csv(outfile,final)
        print('Your export file is "' + outfile + '".')
    
    return final

# get_top_communities: Get top N communities by membership
# Description: This function runs the Louvain method for community detection on an edgelist and returns the names within each of the top N detected communities, the community to which each name belongs, and each name's in-degree. It's basically a wrapper for Thomas Aynaud's excellent Python implementation of Louvain (original version here: http://perso.crans.org/aynaud/communities/) with a few upgrades I found useful. See also Blondel, V. D., Guillaume, J. L., Lambiotte, R., & Lefebvre, E. (2008). Fast unfolding of communities in large networks. Journal of Statistical Mechanics: Theory and Experiment, 2008(10), P10008.
# Arguments:
    # edges: An edgelist of the type exported by t2e. Can be a variable (a list of lists) or a path to a CSV file.
    # return_var: By default, this function returns all community data as described above. If set to any other string, it returns the list of summary data described above.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_communities.csv
# Output: If return_var is set to NODE_MEMBERS, a list of lists, each of which contains a unique node name, its community ID number, and its in-degree, ranked in descending order by in-degree. If return_var is set to anything else, a list of summary data about the Louvain partition (modularity, proportion of nodes included in the top N communities, proportion of edges included in the top N communities, total number of communities detected). If save_prefix is set and return_var is set to NODE_MEMBERS, the community partition data will be saved to CSV. If save_prefix is set but return_var is set to anything else, nothing will be saved. 

def get_top_communities(edges_data,return_var='NODE_MEMBERS',save_prefix=''):

    edge_list = load_file(edges_data)
    random.shuffle(edge_list)

    non_net = nx.Graph()
    non_net.add_edges_from(edge_list)
    print("Non-directed network created.")
    allmods = community3.best_partition(non_net)
    print("Community partition complete.")
    uniqmods = {}

    for i in allmods: #creates a dict of unique communities and the n of times they occur
        if allmods[i] in uniqmods:
            uniqmods[allmods[i]] += 1
        else:
            uniqmods[allmods[i]] = 1

    top10 = sorted(uniqmods,key=uniqmods.get,reverse=True)[0:top_comm] #gets a list of the top N communities by prevalence as defined by the top_comm variable
    topnodes = {}

    for i in allmods: #creates a dict containing only handles belonging to one of the top 10 communities
        if allmods[i] in top10:
            topnodes[i] = allmods[i]

    top_edge_list = [i for i in edge_list if i[0] in topnodes and i[1] in topnodes]

    di_net = nx.DiGraph()
    di_net.add_edges_from(top_edge_list)
    ind = di_net.in_degree()
    outlist = []

    for i in topnodes:
        outlist.append([ind[i],i,str(topnodes[i]),str(ind[i])])

    outlist.sort(reverse=True)
    for i in outlist:
        del i[0]

    edge_list = list(set([i[0] + "," + i[1] for i in edge_list])) #unweight the edgelist--multiple RTs of B by A count as one edge
    edge_list = [i.split(",") for i in edge_list]
    top_edge_list = list(set([i[0] + "," + i[1] for i in top_edge_list]))
    top_edge_list = [i.split(",") for i in top_edge_list]

    node_propor = round((len(topnodes)/len(allmods))*100,2)
    edge_propor = round((len(top_edge_list)/len(edge_list))*100,2)
    mod = round(community3.modularity(allmods,non_net),2)
    print("Total n of clusters: "+str(len(uniqmods)))
    print("Modularity: "+str(mod))
    print("Community analysis complete. The top ten communities in this network account for "+str(node_propor)+"% of all nodes.")
    print("And",edge_propor,"% of all edges.")
    
    summary_data = [mod,node_propor,edge_propor,len(uniqmods)]
    
    if return_var == 'NODE_MEMBERS':
        if len(save_prefix)>0:
            outlist.insert(0,['name','community','in-degree'])
            outfile = save_prefix + '_communities.csv'
            save_csv(outfile,outlist)
            return outlist[1:]
        else:
            return outlist
    else:
        return summary_data

# calc_ei: Calculate EI index for top N communities
# Description: This function calculates Krackhardt & Stern's EI index for each community represented in a file or variable output by get_top_communities. See Krackhardt, D., & Stern, R. N. (1988). Informal networks and organizational crises: An experimental simulation. Social psychology quarterly, 123-140.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities. Can be a variable (a list of lists) or a path to a CSV file. 
    # edges_data: An edgelist of the type exported by t2e. Can be a variable (a list of lists) or a path to a CSV file.
    # verbose: If set to 'ON', the function _get_community_overlap will execute. Default is 'OFF'.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_communities.csv
# Output: A dict wherein the keys are the community ID numbers and the values are their EI indices.  If save_prefix is set, this dict will also be saved as a CSV file.
        
def calc_ei(nodes_data,edges_data,verbose='OFF',save_prefix=''):

    nodes = load_file(nodes_data)
    if(type(nodes_data) is str):
        del nodes[0] #remove headers from CSV
    
    edges = load_file(edges_data)

    modclass = [i[1] for i in nodes]
    moduniq = {}

    for i in modclass: #get and count unique community IDs
        if i in moduniq:
            moduniq[i] += 1
        else:
            moduniq[i] = 1

    mu_top = sorted(moduniq,key=moduniq.get,reverse=True)[0:top_comm] #get the top N most populous communities
    top_nodes_list = [i for i in nodes if i[1] in mu_top]   
    top_nodes = {node[0]:node[1] for node in top_nodes_list} #create dict of screen names and community IDs

    edges = list(set([i[0] + "," + i[1] for i in edges])) #unweight the edgelist--multiple RTs of B by A count as one edge
    edges = [i.split(",") for i in edges]

    for edge in edges:
        if edge[0] in top_nodes:
            edge.append(top_nodes[edge[0]])

    for edge in edges:
        if edge[1] in top_nodes:
            edge.append(top_nodes[edge[1]])

    top_edges = [i for i in edges if len(i) == 4]

    ei_int = {}
    ei_ext = {}

    for i in mu_top:
        ei_int[i] = 0
        ei_ext[i] = 0
        for j in top_edges:
            if j[2] == i and j[3] == i:
                ei_int[i] += 1
            elif j[2] == i or j[3] == i:
                ei_ext[i] += 1

    ei_indices = {}

    for i in ei_int:
        ei_indices[i] = round((ei_ext[i]-ei_int[i])/(ei_ext[i]+ei_int[i]),3)

    print("***EI indices***\n")
    print("Cluster\tEI index")
    for i in ei_indices:
        print(str(i)+"\t"+str(ei_indices[i]))
    mean_ei = round(sum(ei_indices.values())/len(ei_indices.values()),3)
    print("Mean EI:\t",mean_ei)
    
    if len(save_prefix) > 0:
        ei_list = []
        for i in ei_indices:
            ei_list.append([str(i),str(ei_indices[i])])
        ei_list.insert(0,['Community IDs','EI indices']) 
        save_csv(save_prefix + '_ei_indices.csv',ei_list)
    
    if verbose == 'ON':
        input('Press any key to continue...')
        _get_community_overlap(mu_top,top_edges,ei_int,ei_ext)
    
    print("\n")
    return ei_indices

# _get_community_overlap: Measures overlap between each community and all others
# Description: This function determines how a given community's "external" edges are distributed among the other communities. It is not a standalone function: it can only be run by using the "verbose" option from calc_ei. Thus, don't try to enter the following arguments into the function yourself unless you know what you're doing.
# Arguments:
    # top_community_ids: A list of the top N communities by membership.
    # top_edges: A list of all edges both of whose nodes belong to one of the top N communities.
    # ei_int: A dict in which each key is one of the top N community IDs and its value is the number of edges in which both nodes are members of that community.
    # ei_ext: A dict in which each key is one of the top N community IDs and its value is the number of edges in which one node is a member of that community and the other is a member of any other community.
# Output: A display of the top N community IDs, each of which is followed by: 
    # the proportion of internal ties (i.e. those in which both nodes are community members)
    # the total proportion of external ties (i.e. those in which one node is a community member and one is not)
    # The proportion of external ties that are incoming
    # The proportion of external ties that are outgoing
    # The proportions of incoming and outgoing ties shared with every other community. 
# Incoming ties, denoted by "-i," are initiated by members of other communities and point toward members of the focal community; outgoing ties, denoted by "-o," are the opposite. Note: this function returns no values; instead, it pushes the results of its calculations to stdout. Future versions of TSM may include a file output option for this function.
    
def _get_community_overlap(top_community_ids,top_edges,ei_int,ei_ext):
    
    adj_out = {} #outgoing retweets point away from the focal cluster
    adj_in = {} #incoming retweets point toward the focal cluster

    for i in top_community_ids:
        adj_out[i] = {}
        adj_in[i] = {}
        for j in top_edges:
            if j[2] == i and j[3] != i:
                if j[3] in adj_out[i]:
                    adj_out[i][j[3]] += 1
                else:
                    adj_out[i][j[3]] = 1
            if j[3] == i and j[2] != i:
                if j[2] in adj_in[i]:
                    adj_in[i][j[2]] += 1
                else:
                    adj_in[i][j[2]] = 1

    for i in top_community_ids:
        total = ei_int[i]+ei_ext[i]
        print("\nCommunity\tInternal\tIncoming\tOutgoing\tIn - out")
        incoming = round(sum(adj_in[i].values())/total,3)
        outgoing = round(sum(adj_out[i].values())/total,3)
        print(str(i)+"\t"+str(round(ei_int[i]/total,3))+"\t"+str(incoming)+"\t"+str(outgoing)+"\t"+str(round(incoming-outgoing,3))+"\n")
        for j in top_community_ids:
            if i != j:
                if j in adj_out[i]:
                    print(str(j)+"-o\t"+str(round(adj_out[i][j]/total,3)))
                if j in adj_in[i]:
                    print(str(j)+"-i\t"+str(round(adj_in[i][j]/total,3)))

# get_top_rts: Gets the most-retweeted tweets in a Twitter dataset with community IDs
# Description: This function returns a list of the most-retweeted tweets along with the community IDs of the tweet authors and retweet counts. This allows researchers to easily view the most-retweeted tweets within each community.
# Arguments:
    # tweets_file: A CSV file containing tweets formatted for t2e as specified above. 
    # nodes_data: A community-partition dataset of the type exported by get_top_communities. Can be a variable (a list of lists) or a path to a CSV file. 
    # min_rts: An integer indicating the minimum number of retweets to be included in the output. Default is 5. Increasing this number will reduce your filesize and processing time; decreasing it will do the opposite.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_top_RTs.csv
# Output: A list of lists, each of which contains the name of the retweeted user, the full text of the retweet, the user's community ID, and the number of times the tweet was retweeted. This list is ranked in descending order of retweet count.
                    
def get_top_rts(tweets_file,nodes_data,min_rts=5,save_prefix=''):

    rts = []
    
    nodes = load_file(nodes_data)
    if type(nodes_data) is str:
        del nodes[0]
    
    with open(tweets_file,'r',encoding=enc) as f:
        reader = csv.reader(f)
        for row in reader:
            if row[1].startswith('RT @') and row[1].find(':')>-1:
                rts.append(row[1].lower())

    node_dict = {}
    for i in nodes:
        node_dict[i[0]] = i[1]

    dups = {}
    for i in rts:
        if i in dups:
            dups[i] +=1
        else:
            dups[i] = 1

    rted_user_list = []
    for i in dups:
        rted_user_list.append([i[i.find('@')+1:i.find(':')],i])

    top_rts_out = []
    for i in rted_user_list:
        if i[0] in node_dict and dups[i[1]] >= min_rts:
            top_rts_out.append([dups[i[1]],i[0],i[1],str(node_dict[i[0]]),str(dups[i[1]])])

    top_rts_out.sort(reverse=True)
    for i in top_rts_out:
        del i[0]
    
    if len(save_prefix) > 0:
        for i,row in enumerate(top_rts_out):
            for j,_ in enumerate(row):
                top_rts_out[i][j] = '"' + top_rts_out[i][j] + '"'
        top_rts_out.insert(0,['"rted_user"','"rt_text"','"cluster"','"n_rts"'])
        save_csv(save_prefix + '_top_RTs.csv',top_rts_out)
        return top_rts_out[1:]
    
    else:
        return top_rts_out

# match_communities: Find the best community matches between two networks using the weighted Jaccard coefficient
# Description: This function takes two partitioned networks, A and B, and finds the best match for each community in A among the communities in B. Matches are determined by measuring membership overlap with the weighted Jaccard coefficient. To reduce processing time, only the top x% of users by in-degree in each community are compared. The Jaccard comparisons are weighted by in-degree, meaning that higher in-degree users count more toward community similarity. This decision is based on the assumption that users of higher in-degree play a proportionately larger role in terms of maintaining community coherence.
# Arguments:
    # nodes_data_A: A community-partition dataset of the type exported by get_top_communities (network A). Can be a variable or a path to a CSV file. 
    # nodes_data_B: A community-partition dataset of the type exported by get_top_communities (network B). Can be a variable or a path to a CSV file.
    # propor: A float variable greater than 0 and less than 1 representing the per-community proportion of top in-degree users to compare between A and B. Default is 0.01 (1%). Increasing this number will increase processing time.
    # threshold: A float variable greater than 0 and less than 1 representing the weighted Jaccard threshold above which communities will be considered "valid" matches. Default is 0.3. I would caution against using this blindly--try a few different values and see what seems to make sense for your data.
# Output: A display of each community ID number in A together with all nonzero weighted Jaccard coefficients with communities in B. Following this, for each community in A containing at least one Jaccard exceeding the threshold, the highest Jaccard is displayed along with the users appearing in both communities. Note: this function returns no values; instead, it pushes the results of its calculations to stdout. Future versions of TSM may include a file output option for this function. 
        
def match_communities(nodes_data_A,nodes_data_B,propor=0.01,threshold=0.3):

    nodesA = load_file(nodes_data_A)
    del nodesA[0]

    nodesB = load_file(nodes_data_B)
    del nodesB[0]

    uniq_cl_1 = list(set([i[1] for i in nodesA])) #creates a unique list of the top 10 clusters from each cluster file
    uniq_cl_2 = list(set([i[1] for i in nodesB]))

    topusers_1 = {} #creates a dict of lists. Each list contains the top [propor*100]% most-connected nodes within each community
    for i in uniq_cl_1:
        cltemp = [j[0] for j in nodesA if j[1] == i]
        pct = int(len(cltemp) * propor)
        topusers_1[i] = [j for j in cltemp][0:pct] 

    topusers_2 = {}
    for i in uniq_cl_2:
        cltemp = [j[0] for j in nodesB if j[1] == i]
        pct = int(len(cltemp) * propor)
        topusers_2[i] = [j for j in cltemp][0:pct]

    hijacc = 0
    hidict = {}

    for i in topusers_1:
        hix = i+'x'
        for j in topusers_2:
            intersect = set(topusers_1[i]).intersection(set(topusers_2[j])) #get intersection of names for month 1 + 2
            inter_weights = [int(k[2]) for k in nodesA if k[0] in intersect] + [int(k[2]) for k in nodesB if k[0] in intersect] #pull intersection in-degrees from both months and combine into a single list
            union_both = set(topusers_1[i] + topusers_2[j])
            union_weights = [int(k[2]) for k in nodesA if k[0] in union_both] + [int(k[2]) for k in nodesB if k[0] in union_both] #pull union in-degrees from both months and combine into a single list
            jacc = sum(inter_weights)/sum(union_weights)
            if jacc > 0:
                print(i+'x'+j+"\t"+str(round(jacc,4)))
            if jacc > hijacc:
                hijacc = round(jacc,4)
                hix = i+'x'+j
        print('high:'+"\t"+hix+"\t"+str(hijacc)+"\n")
        hidict[hix] = hijacc
        hijacc = 0

    print('Top cluster matches:')
    for i in hidict:
        if hidict[i] > threshold:
            users_A = set(topusers_1[i[:i.find('x')]])
            users_B = set(topusers_2[i[i.find('x')+1:]])
            shared_users = ', '.join(users_A.intersection(users_B))
            print(i,"\t",hidict[i],"\t",shared_users,"\n")
    
    return hidict