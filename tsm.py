#!/usr/bin/python3

# TSM (Twitter Subgraph Manipulator) for Python 3
# release 3 (07/23/14)
# (c) 2014 by Deen Freelon <dfreelon@gmail.com>
# Distributed under the BSD 3-clause license. See LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause for details.

# This Python module contains a set of functions that create and manipulate Twitter and Twitter-like network communities (subgraphs) in various ways. The only Twitter-specific functions are t2e and get_top_rts; the rest can be used with any directed edgelist. This module is intended for use with directed, long-tailed, and extremely sparse networks like those commonly found on the web. It functions only with Python 3.x and is not backwards-compatible (although one could probably branch off a 2.x port with minimal effort).

# Warning: TSM performs no custom error-handling, so make sure your inputs are formatted properly! If you have questions, please let me know via email.

# FUNCTION LIST

# load_data: Loads files quickly

# save_csv: Quick CSV output

# t2e: Converts raw tweets into edgelist format (retweets and @-mentions, not follows)

# get_top_communities: A wrapper for Thomas Aynaud's implementation of the Louvain method for community detection. Gets the top N largest communities by membership in a network and then outputs a file/variable containing the community labels and in-degrees of each user.

# calc_ei: Calculates the E-I index (a measure of insularity) of each community detected by get_top_communities.

# _get_community_overlap: An extension of calc_ei that shows how "close" each community is to all of the others in terms of shared ties

# get_top_rts: Gets the most-retweeted tweets within each community

# match_communities: Compares community membership within two networks, A and B, and gives the best match found in B for each community in A

# get_bridges: Discovers which nodes bridge which communities

# get_top_hashtags: Gets the most-used hashtags in each community

# MODULE-WIDE VARIABLES (these need to remain the same for all functions in this module)

#The var below, top_comm, is an integer representing the top N communities by node population. These will be the communities which this module's functions will manipulate. For large Twitter networks, I have found it fruitful to work with the top ten largest retweet or @-mention communities. Other things being equal, top_comm should be roughly correlated with processing time.

top_comm = 10

#Change the text encoding below. If 'utf-8' produces garbage characters and your data are in English, try 'latin1'

enc = 'utf-8'

# REQUIRED MODULES

#Below are all the dependencies this module requires. Everything except NetworkX and community.py comes standard with Python. You can get NetworkX here: http://networkx.github.io/ . Beware, it can be a bit tricky to install. You'll also need Thomas Aynaud's implementation of the Louvain method for community detection, but you must use the version I modified to work with Python 3 (community3.py)--otherwise the only TSM function that will work is t2e. (Aynaud's original 2.x-compliant version is available here: http://perso.crans.org/aynaud/communities/) 

import collections
import community3
import copy
import csv
import networkx as nx
import operator
import random
import re

# FUNCTIONS

# load_data and save_csv are mostly self-explanatory. load_data accepts both strings representing file paths and variables. Whichever you choose must contain the expected internal structure for the function to work properly.

def load_data(data):
    if type(data) is str:
        csv_data = []
        with open(data,'r',encoding = enc) as f:
            reader = csv.reader(f)
            for row in reader:
                csv_data.append(row)
        return csv_data
    else:
        return copy.deepcopy(data)

def save_csv(outfile,data): #this assumes a list of lists wherein the second-level list items contain no commas
    with open(outfile,'w',encoding = enc) as out: 
        for line in data:
            row = ','.join([str(i) for i in line]) + "\n"
            out.write(row)

# t2e: convert raw Twitter data to edgelist format
# Description: t2e takes raw Twitter data as input and outputs an edgelist consisting of the names of the tweet authors (col 1) and the names of the nodes mentioned and/or retweeted (col 2). 
# Arguments: 
    # tweets_file: a path to a CSV file (the only delimiter currently allowed is commas) with tweet authors listed in col 1 and corresponding tweet text in col 2. If col 1 contains any text, col 2 must as well, and vice versa.
    # extmode: see below
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_edgelist.csv
# Output: An edgelist in the form of a Python list of lists. If save_prefix is set, the edgelist will also be saved as a CSV file.

# t2e has four extraction modes (specified by the extmode variable). Default is ALL.
# ALL = do not differentiate between retweets and non-retweets, include isolates (default)
# ALL_NO_ISOLATES = do not differentiate between retweets and non-retweets, exclude isolates
# RTS_ONLY = retweets only, exclude isolates
# AT_MENTIONS_ONLY = non-retweets (@-mentions) only, exclude isolates
# REPLIES_ONLY = only tweets in which the first or second character is an "@," exclude isolates

def t2e(tweets_file,extmode='ALL',save_prefix=''):
    
    g_src = []
    g_tmp = []
    
    with open(tweets_file,'r',encoding = enc) as f:
        reader = csv.reader(f)
        for row in reader:
            if extmode.upper() == 'ALL_NO_ISOLATES':
                condition = row[1].find('@')>-1
            elif extmode.upper() == 'RTS_ONLY':
                condition = row[1].find('RT @')>-1
            elif extmode.upper() == 'AT_MENTIONS_ONLY':
                condition = row[1].find('@')>-1 and row[1].find('RT @')==-1
            elif extmode.upper() == 'REPLIES_ONLY':
                condition = row[1].find('@')==0 or row[1].find('@')==1
            else:
                condition = True
            if condition is True:
                g_src.append(row[0].lower().strip())
                g_tmp.append(' ' + row[1] + ' ')

    g_tmp = [t.split('@') for t in g_tmp] #splits each tweet along @s
    g_trg = [[t[:re.search('[^A-Za-z0-9_]',t).start()].lower().strip() for t in chunk if re.search('[^A-Za-z0-9_]',t) is not None] for chunk in g_tmp] #strips out everything after the @ sign and trailing colons, leaving (hopefully) a list of lists of node names
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
    # edges_data: An edgelist of the type exported by t2e. Can be a variable (a list of lists) or a path to a CSV file.
    # weight_edges: If set to 'NO', the edgelist will be unweighted--in other words all duplicate edges will be removed. For example, if the userA->userB edge has a weight of 5 (meaning A linked to B five distinct times), the function will count that as a single tie. If unweight_edges is set to anything else, the function will include duplicate edges in the final calculations (so each of the userA->userB edge's five weights would count as a separate edge). This option only affects the summary statistics calculated at the end--it does not change the content of the dataset. Default is 'YES'.
    # return_var: By default, this function returns all community data as described above. If set to any other string, it returns the list of summary data described above.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_communities.csv
# Output: An object of the custom class "louvainObject" with the following attributes:
    # node_list: A list of lists containing each unique node in the largest communities as defined above by the top_comm variable, the ID of the community to which it belongs, and its in-degree.
    # n_nodes: A dict in which the keys are community IDs and the values are integers representing the number of nodes belonging to each community
    # n_communities: An integer representing the total number of communities detected by the algorithm.
    # modularity: The network's modularity.
    # node_propor: The proportion of all nodes included within the largest communities.
    # edge_propor: The proportion of all edges included within the largest communities. 

class louvainObject:
    '''an object class with attributes for various Louvain-related data and metadata'''
    def __init__(self,node_list,n_nodes,n_communities,modularity,node_propor,edge_propor):
        self.node_list = node_list
        self.n_nodes = n_nodes
        self.n_communities = n_communities
        self.modularity = modularity
        self.node_propor = node_propor
        self.edge_propor = edge_propor

def get_top_communities(edges_data,weight_edges='YES',save_prefix=''):

    edge_list = load_data(edges_data)
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
        
    if weight_edges.upper() == 'NO':
        edge_list = list(set([i[0] + "," + i[1] for i in edge_list])) #unweight the edgelist--multiple RTs of B by A count as one edge
        edge_list = [i.split(",") for i in edge_list]
        top_edge_list = list(set([i[0] + "," + i[1] for i in top_edge_list]))
        top_edge_list = [i.split(",") for i in top_edge_list]

    n_communities = len(uniqmods)
    mod = round(community3.modularity(allmods,non_net),2)
    node_propor = round((len(topnodes)/len(allmods))*100,2)
    edge_propor = round((len(top_edge_list)/len(edge_list))*100,2)
    n_nodes = {}
    for i in outlist:
        if i[1] in n_nodes:
            n_nodes[i[1]] += 1
        else:
            n_nodes[i[1]] = 1
        
    
    print("Total n of communities:",n_communities)
    print("Modularity:",mod)
    print("Community analysis complete. The top",top_comm,"communities in this network account for",node_propor,"% of all nodes.")
    print("And",edge_propor,"% of all edges.")
    
    if len(save_prefix)>0:
        outlist.insert(0,['name','community','in-degree'])
        outfile = save_prefix + '_communities.csv'
        save_csv(outfile,outlist)
    
    louvain_out = louvainObject(outlist,n_nodes,n_communities,mod,node_propor,edge_propor)
    return louvain_out

# calc_ei: Calculate EI index for top N communities
# Description: This function calculates Krackhardt & Stern's EI index for each community represented in a file or variable output by get_top_communities. The EI index ranges between 1 and -1, with 1 indicating that all the community's ties are with outsiders, -1 indicating they are all with members, and 0 indicating equal numbers of ties with members and outsiders. See Krackhardt, D., & Stern, R. N. (1988). Informal networks and organizational crises: An experimental simulation. Social psychology quarterly, 123-140.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities. Can be a variable (a list of lists) or a path to a CSV file. 
    # edges_data: An edgelist of the type exported by t2e. Can be a variable (a list of lists) or a path to a CSV file.
    # verbose: If set to 'ON', the function _get_community_overlap will execute after calc_ei has finished. If set to 'ON_PAUSE', _get_community_overlap will execute but you will be prompted to press any key to proceed after calc_ei has finished. Default is 'OFF'.
    # weight_edges: If set to 'NO', the edgelist will be unweighted--in other words all duplicate edges will be removed. For example, if the userA->userB edge has a weight of 5 (meaning A linked to B five distinct times), the function will count that as a single tie. If unweight_edges is set to anything else, the function will include duplicate edges in the EI calculations (so each of the userA->userB edge's five weights would count as a separate edge). Default is 'YES'.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_communities.csv
# Output: An object of the custom class "eiObject" containing the following mandatory attributes:
    # n_nodes: A dict in which the keys are community IDs and the values are integers representing the number of nodes belonging to each community
    # index: An OrderedDict in which the keys are community IDs and the values are corresponding EI indices.
    # internal_ties: An OrderedDict in which the keys are community IDs and the values are counts of internal edges.
    # external_ties: An OrderedDict in which the keys are community IDs and the values are counts of external edges.
    # mean_ei: The mean of the EI indices from index.
    # If verbose is set to "ON" or "ON_PAUSE," the returned eiObject will include the following optional attributes:
        # total_ties: An OrderedDict in which the keys are community IDs and the values are total counts of all links involving a community member.
        # received_ties: An OrderedDict in which each key is a community ID and each value is a count of all links wherein the recipient is a community member.
        # sent_ties: An OrderedDict in which each key is a community ID and each value is a count of all links wherein the sender is a community member.
        # r_s: An OrderedDict in which each key is a community ID and each value is the received count minus the sent count.
        # adj_in: An OrderedDict of dicts in which each key is a community ID (A), each second-level key is a community ID (B), and each second-level value is the number of edges originating in B and pointing to A.
        # adj_out: An OrderedDict of dicts in which each key is a community ID (A), each second-level key is a community ID (B), and each second-level value is the number of edges originating in A and pointing to B.
 
class eiObject:
    '''an object class with attributes for various EI-index-related data and metadata'''
    def __init__(self,n_nodes=None,index=None,internal_ties=None,external_ties=None,mean_ei=None,total_ties=None,received_ties=None,sent_ties=None,r_s=None,adj_in=None,adj_out=None):
        self.n_nodes = n_nodes
        self.index = index
        self.internal_ties = internal_ties
        self.external_ties = external_ties
        self.mean_ei = mean_ei
        self.total_ties = total_ties
        self.received_ties = received_ties
        self.sent_ties = sent_ties
        self.r_s = r_s
        self.adj_in = adj_in
        self.adj_out = adj_out
        
def calc_ei(nodes_data,edges_data,verbose='OFF',weight_edges='YES',save_prefix=''):
    
    if weight_edges.upper() == 'NO':
        print("Calculating EI indices using *UNweighted* edges.\n")
    else:
        print("Calculating EI indices using *weighted* edges.\n")
    
    nodes = load_data(nodes_data)
    if type(nodes_data) is str:
        del nodes[0] #remove headers from CSV
    
    edges = load_data(edges_data)

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
    
    if weight_edges.upper() == 'NO':
        edges = list(set([i[0] + "," + i[1] for i in edges])) #unweight the edgelist--multiple links to B from A count as one edge
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
    
    ei_ord = collections.OrderedDict(sorted(ei_indices.items()))
    ei_int = collections.OrderedDict(sorted(ei_int.items()))
    ei_ext = collections.OrderedDict(sorted(ei_ext.items()))
    
    print("***EI indices***\n")
    print("Community\tEI index")
    for i in ei_ord:
        print(str(i)+"\t"+str(ei_ord[i]))
    mean_ei = round(sum(ei_indices.values())/len(ei_indices.values()),3)
    print("Mean EI:\t",mean_ei)
    
    n_nodes = {}
    for i in nodes:
        if i[1] in n_nodes:
            n_nodes[i[1]] += 1
        else:
            n_nodes[i[1]] = 1
    
    if verbose.upper() == 'ON_PAUSE':
        input('Press any key to continue...')
    
    if verbose.upper() == 'ON' or verbose.upper() == 'ON_PAUSE':
        ei_out = _get_community_overlap(mu_top,top_edges,ei_int,ei_ext,n_nodes)
    
    if len(save_prefix) > 0:
        ei_list = []
        for i in ei_ord:
            ei_list.append([str(i),str(ei_ord[i])])
        ei_list.insert(0,['Community IDs','EI indices']) 
        save_csv(save_prefix + '_ei_indices.csv',ei_list)
    print("\n")
    
    if verbose.upper() != 'ON' and verbose.upper() != 'ON_PAUSE':
        ei_out = eiObject()
        
    ei_out.n_nodes = n_nodes
    ei_out.index = ei_ord
    ei_out.internal_ties = ei_int
    ei_out.external_ties = ei_ext
    ei_out.mean_ei = mean_ei
    return ei_out

# _get_community_overlap: Measures overlap between each community and all others
# Description: This function reveals how a given community's "external" edges are distributed among the other communities. It is not a standalone function: it can only be run by using the "verbose" option from calc_ei. Thus, don't try to enter the following arguments into the function yourself unless you know what you're doing.
# Arguments:
    # top_community_ids: A list of the top N communities by membership.
    # top_edges: A list of all edges both of whose nodes belong to one of the top N communities.
    # ei_int: A dict in which each key is one of the top N community IDs and its value is the number of edges in which both nodes are members of that community.
    # ei_ext: A dict in which each key is one of the top N community IDs and its value is the number of edges in which one node is a member of that community and the other is a member of any other community.
# Output: An object of the custom class "eiObject" containing only its non-mandatory attributes (see documentation for calc_ei).
    
def _get_community_overlap(top_community_ids,top_edges,ei_int,ei_ext,n_nodes):
    
    ei_out = eiObject()
    adj_out = {} #sent ties point away from the focal community
    adj_in = {} #received ties point toward the focal community

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
    
    total_dict = {}
    received_dict = {}
    sent_dict = {}
    r_s_dict = {}
    
    for i in top_community_ids:
        total = ei_int[i]+ei_ext[i]
        total_dict[i] = total
        print("\nCommunity\tSize\tInternal\tReceived\tSent\tReceived - Sent")
        incoming = sum(adj_in[i].values())
        received_dict[i] = incoming
        outgoing = sum(adj_out[i].values())
        sent_dict[i] = outgoing
        r_s = round(incoming-outgoing,3)
        r_s_dict[i] = r_s
        print(str(i)+"\t"+str(n_nodes[i])+"\t"+str(round(ei_int[i]/total,3))+"\t"+str(round(incoming/total,3))+"\t"+str(round(outgoing/total,3))+"\t"+str(round(r_s/total,3))+"\n")
        for j in top_community_ids:
            if i != j:
                if j in adj_out[i]:
                    print(str(j)+"-s\t"+str(round(adj_out[i][j]/total,3)))
                if j in adj_in[i]:
                    print(str(j)+"-r\t"+str(round(adj_in[i][j]/total,3)))
    
    ei_out.adj_in = collections.OrderedDict(sorted(adj_in.items()))
    ei_out.adj_out = collections.OrderedDict(sorted(adj_out.items()))
    ei_out.total_ties = collections.OrderedDict(sorted(total_dict.items()))
    ei_out.received_ties = collections.OrderedDict(sorted(received_dict.items()))
    ei_out.sent_ties = collections.OrderedDict(sorted(sent_dict.items()))
    ei_out.r_s = collections.OrderedDict(sorted(r_s_dict.items()))
    
    return ei_out

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
    
    nodes = load_data(nodes_data)
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
        top_rts_out.insert(0,['"rted_user"','"rt_text"','"community"','"n_rts"'])
        save_csv(save_prefix + '_top_RTs.csv',top_rts_out)
        return top_rts_out[1:]
    
    else:
        return top_rts_out

# match_communities: Find the best community matches between two networks using the weighted Jaccard coefficient
# Description: This function takes two partitioned networks, A and B, and finds the best match for each community in A among the communities in B. Matches are determined by measuring membership overlap with either the weighted or the unweighted Jaccard coefficient, depending on how the weight_nodes parameter is set. To reduce processing time, only the top (propor * 100)% of nodes by in-degree in each community are compared. The weighted Jaccard comparisons are weighted by in-degree, meaning that higher in-degree nodes count more toward community similarity. This is based on the assumption that nodes of higher in-degree play a proportionately larger role in terms of maintaining community coherence.
# Arguments:
    # nodes_data_A: A community-partition dataset of the type exported by get_top_communities (network A). Can be a variable or a path to a CSV file. 
    # nodes_data_B: A community-partition dataset of the type exported by get_top_communities (network B). Can be a variable or a path to a CSV file.
    # nodes_propor: A float variable greater than 0 and less than 1 representing the per-community proportion of top in-degree nodes to compare between A and B. Default is 0.01 (1%). Increasing this number will increase processing time.
    # jacc_threshold: A float variable greater than 0 and less than 1 representing the Jaccard value above which community pairs will be considered valid matches. Default is 0.3. I would caution against using this blindly--try a few different values and see what seems to make sense for your data.
    # dc_threshold: A float variable representing the Jaccard value above which convergences and divergences (as defined below) will be considered valid. I suggest setting this somewhat lower than jacc_threshold. 
    # weight_jaccard: If set to 'YES', the function will weight the Jaccard coefficient by each node's in-degree to match communities between networks A and B. If set to anything else, it will use the unweighted Jaccard coefficient. Default is 'YES'.
# Output: An object of the custom class "cMatchObject" containing the following attributes:
    # best_match: An OrderedDict in which the keys are the best community matches for network A in network B (in AxB format where A and B are community IDs) and the values are the corresponding Jaccard values.
    # shared_node: An OrderedDict in which the keys are the best matches for network A in network B (in AxB format where A and B are community IDs) and the values comprise the set of top nodes shared between the two networks.
    # nonzero_jacc: An OrderedDict of dicts in which each first-order key is a community ID from network A, each second-order key is a community ID from network B, and each second-order value is the nonzero Jaccard between the A and B IDs.
    # diverge: An OrderedDict in which each key is a community ID from network A and each value is a list containing two or more IDs from network B. These IDs represent divergences, i.e. situations in which two or more month-B communities share Jaccard values exceeding jacc_threshold with a single month-A community.
    # converge: An OrderedDict in which each key is a community ID from network B and each value is a list containing two or more IDs from network A. These IDs represent convergences--the logical converses of divergences--i.e. situations in which two or more month-A communities share Jaccard values exceeding jacc_threshold with a single month-B community.

class cMatchObject:
    '''an object class with attributes for various matched-community data and metadata'''
    def __init__(self,best_match=None,shared_node=None,nonzero_jacc=None,diverge=None,converge=None):
        self.best_match = best_match
        self.shared_node = shared_node
        self.nonzero_jacc = nonzero_jacc
        self.diverge = diverge
        self.converge = converge

def match_communities(nodes_data_A,nodes_data_B,nodes_propor=0.01,jacc_threshold=0.3,dc_threshold=0.2,weight_jaccard='YES'):

    nodesA = load_data(nodes_data_A)
    if type(nodes_data_A) is str:
        del nodesA[0]

    nodesB = load_data(nodes_data_B)
    if type(nodes_data_B) is str:
        del nodesB[0]

    topnodes_1 = _get_top_nodes(nodesA,nodes_propor)
    topnodes_2 = _get_top_nodes(nodesB,nodes_propor)
    
    hijacc = 0
    best_match = {}
    nonzero_jacc = {}

    for i in topnodes_1:
        nonzero_jacc[i] = {}
        hix = i+'x'
        for j in topnodes_2:
            intersect = set(topnodes_1[i]).intersection(set(topnodes_2[j])) #get intersection of names for month 1 + 2
            union_both = set(topnodes_1[i] + topnodes_2[j])
            if weight_jaccard.upper() == 'YES':
                inter_weights = [int(k[2]) for k in nodesA if k[0] in intersect] + [int(k[2]) for k in nodesB if k[0] in intersect] #pull intersection in-degrees from both months and combine into a single list
                union_weights = [int(k[2]) for k in nodesA if k[0] in union_both] + [int(k[2]) for k in nodesB if k[0] in union_both] #pull union in-degrees from both months and combine into a single list
                jacc = sum(inter_weights)/sum(union_weights)
            else: #if weight_jaccard is set to anything other than 'YES', set all weights to 1 for each node
                inter_weights = len(intersect) 
                union_weights = len(union_both) 
                jacc = inter_weights/union_weights
            if jacc > 0:
                print(i+'x'+j+"\t"+str(round(jacc,4)))
                nonzero_jacc[i][j] = round(jacc,4) #
            if jacc > hijacc:
                hijacc = round(jacc,4)
                hix = i+'x'+j
        print('high:'+"\t"+hix+"\t"+str(hijacc)+"\n")
        best_match[hix] = hijacc
        hijacc = 0

    shared_node = {}    
    print('Top community matches:')
    for i in best_match:
        if best_match[i] >= jacc_threshold:
            nodes_A = set(topnodes_1[i[:i.find('x')]])
            nodes_B = set(topnodes_2[i[i.find('x')+1:]])
            shared_node[i] = nodes_A.intersection(nodes_B)
            sn = ', '.join(shared_node[i])
            print(i,"\t",best_match[i],"\t",sn,"\n")
    
    diverge = {}
    for i in nonzero_jacc: #divergence test
        if len(nonzero_jacc[i]) > 0:
            jacc_tmp = sorted(nonzero_jacc[i].values(),reverse=True)
            highest_key = sorted(nonzero_jacc[i],key=nonzero_jacc[i].get,reverse=True)[0]
            for j in nonzero_jacc[i]:
                if highest_key != j and jacc_tmp[0] >= dc_threshold and nonzero_jacc[i][j] >= dc_threshold:
                    print('Divergence of month-A community',i,'into month-B communities',highest_key,'and',j)
                    diverge[i] = [highest_key,j]
    
    thres_jacc = {} #convergence test
    for i in nonzero_jacc: #get all jaccs above dc_threshold
        thres_jacc[i] = {}
        for j in nonzero_jacc[i]:
            if nonzero_jacc[i][j] >= dc_threshold:
                thres_jacc[i][j] = nonzero_jacc[i][j]
    
    thres_dict_list = {} #get a dict of lists of the month-B IDs above jacc_threshold
    for i in thres_jacc:
        thres_dict_list[i] = list(thres_jacc[i].keys())
        
    conv = {} #create a dict of empty lists corresponding to all unique month-B IDs
    for i in thres_dict_list:
        for j in thres_dict_list[i]:
            conv[j] = []
    
    for i in thres_dict_list: #figure out which month-B IDs appear as multiple matches for month-A IDs
        for j in thres_dict_list:
            if i != j:
                c_intersect = set(thres_dict_list[i]).intersection(set(thres_dict_list[j]))
                if len(c_intersect) > 0:
                    conv_msg = 0
                    for k in c_intersect:
                        if i not in conv[k]:
                            conv_msg += 1
                            conv[k].append(i)
                        if j not in conv[k]:
                            conv_msg += 1
                            conv[k].append(j)
                        if conv_msg == 2:
                            print('Convergence of month-A communities',i,'and',j,'into month-B community',k)
    
    converge = {}
    for i in conv:
        if len(conv[i]) > 0:
            converge[i] = conv[i]
    
    match_out = cMatchObject()
    match_out.best_match = collections.OrderedDict(sorted(best_match.items()))
    match_out.shared_node = collections.OrderedDict(sorted(shared_node.items()))
    match_out.nonzero_jacc = collections.OrderedDict(sorted(nonzero_jacc.items()))
    match_out.diverge = collections.OrderedDict(sorted(diverge.items()))
    match_out.converge = collections.OrderedDict(sorted(converge.items()))
    
    return match_out

# _get_top_nodes: Get the nodes of highest in-degree in a network
# Desciption: This is a helper function for match_communities and get_bridges that simply loads the top (propor * 100)% of nodes by in-degree in each community in a partitioned network into a list.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # propor: A float variable greater than 0 and less than 1 representing the proportion of top in-degree nodes to extract from each community. Default is 0.01 (1%). Increasing this number will increase processing time.
#Output: A dict containing lists of the top (propor * 100)% of nodes by in-degree for each network community.
    
def _get_top_nodes(nodes_data,propor=0.01):
    uniq_cl = list(set([i[1] for i in nodes_data])) #creates a unique list of the top 10 communities from each community file

    topnodes = {} #creates a dict of lists. Each list contains the top [propor*100]% most-connected nodes within each community
    for i in uniq_cl:
        cltemp = [j[0] for j in nodes_data if j[1] == i]
        pct = int(len(cltemp) * propor)
        topnodes[i] = [j for j in cltemp][0:pct] 
    
    return topnodes

# get_bridges: Identifies nodes who are heavily linked to by multiple network communities
# Description: When analyzing partitioned networks, it is sometimes helpful to know not only which nodes are high in betweenness centrality, but also which communities are bridged by such nodes. This function identifies high in-degree nodes whose links are relatively evenly distributed across at least two communities.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # edges_data: An edgelist of the type exported by t2e.
    # threshold: A float variable greater than 0 and less than 1 representing the minimum proportion of internal links a given top node needs to receive from an external community to count as a bridge. For example, for node DF in community A where the external community most connected to DF is B, setting threshold to 0.5 means that for DF to count as a bridge, the number of links DF receives from B must equal at least 50% of the links it receives from A.
    # propor: A float variable greater than 0 and less than 1 representing the proportion of top in-degree nodes to extract from each community. Default is 0.01 (1%). Increasing this number will increase processing time.
    # verbose: If set to 'ON,' the shell will print a message every time a new node is added to the bridge list. Default is 'OFF.'
# Output: A list of lists, each of which contains a bridge node's in-degree (at index 0), its name (at index 1), and a dict in which each key is a community ID and each value is the N of links the node received from that community (at index 2). Note: the community ID of the bridge node is not explicitly listed in this variable, but it is almost always the ID with the highest N of received links.
    
def get_bridges(nodes_data,edges_data,bridge_threshold=0.5,propor=0.01,verbose='OFF'):
    nodes = load_data(nodes_data)
    if type(nodes_data) is str:
        del nodes[0]
    edges = load_data(edges_data)
    topnodes = _get_top_nodes(nodes,propor)
    
    cmty_list = list(topnodes.keys())
    node_dict = {i[0]:i[1] for i in nodes} #create dict of node names and community IDs
    bridge_cands = {}
    
    for cmty in topnodes:
        for name in topnodes[cmty]:
            if verbose.upper() == 'ON':
                print('Analyzing node "' + name + '".')
            user_edges = []
            
            for i in edges: #pull all edges of which node is the recipient
                if name == i[1]:
                    user_edges.append(i)
            
            ue_minus = [i for i in user_edges if i[0] in node_dict] #remove all nodes not in the top N communities
            cmty_rts = {}
            
            for i in cmty_list:
                for j in ue_minus:
                    if node_dict[j[0]] == i:
                        if i in cmty_rts:
                            cmty_rts[i] += 1
                        else:
                            cmty_rts[i] = 1
                            
            list_rts_ct = sorted(list(cmty_rts.values()),reverse=True)
            if len(cmty_rts) >= 2 and list_rts_ct[1] >= list_rts_ct[0]*bridge_threshold: #the N of ties to the 2nd-highest community must equal or exceed a minimum proportion of the N of ties to the highest community
                if verbose.upper() == 'ON':
                    print('Node "' + name + '" added to the list.')
                cmty_rts = collections.OrderedDict(sorted(cmty_rts.items(),key=operator.itemgetter(1),reverse=True))
                bridge_cands[name] = cmty_rts
                
    bridge_list = []
    for i in bridge_cands:
        bridge_list.append([sum(bridge_cands[i].values()),i,bridge_cands[i]])
        
    bridge_list = sorted(bridge_list,reverse=True)
    
    return bridge_list

# get_top_hashtags: Collects the most-used hashtags in each community in descending order of popularity
# Description: This function collects the most-used hashtags in a set of tweets that's been partitioned into communities and organizes them first by community and then in descending order of popularity.
# Arguments:
    # tweets_data: a path to a CSV file (the only delimiter currently allowed is commas) with tweet authors listed in col 1 and corresponding tweet text in col 2. If col 1 contains any text, col 2 must as well, and vice versa.
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # min: The minimum number of times a hashtag must have been used in a given community to be included in that community's list. Increasing this number speeds processing. Default is 10.
# Output: A dict whose keys are community IDs and whose values are lists, each of which contains one community's top hashtags arranged in descending order of popularity.
    
def get_top_hashtags(tweets_data,nodes_data,min=10):
    tweets = load_data(tweets_data)
    if type(tweets_data) is str:
        del tweets[0]
        
    nodes = load_data(nodes_data)
    if type(nodes_data) is str:
        del nodes[0]

    clust_uniq = list(set([i[1] for i in nodes]))
    node_dict = {i[0].lower():i[1] for i in nodes}
    tweets = [[i[0].lower(),i[1].lower()] for i in tweets if i[0].lower() in node_dict]
    ht_dict = {}

    for id in clust_uniq:
        g_tmp = [' ' + re.sub(r'[\\\"\'\.\,\-\:“”()!&\[\]]','',t[1]).lower().replace(u'\u200F','') + ' ' for t in tweets if t[1].find('#') > -1 and node_dict[t[0]] == id] #fills in the list g_tmp with hashtags, lowercased, space-padded, cleaned and only if a hashmark exists in the tweet
        g_tmp_split = [t.split('#') for t in g_tmp] #splits each tweet along #s
        g_trg = [[t[:re.search('[\s\r\n\t]',t).start()].strip() for t in chunk if re.search('[\s\r\n\t]',t) is not None] for chunk in g_tmp_split] #strips out everything after the # sign, leaving (hopefully) a list of lists of hashtags
        g_trg2 = [[t[t.rfind(' ')+1:].strip() for t in chunk] for chunk in g_tmp_split]

        final = []
        for hlist in g_trg: #creates final output list
            for hashtag in hlist:
                if len(hashtag)>0:
                    final.append(hashtag)
        for hlist in g_trg2: #creates final output list
            for hashtag in hlist:
                if len(hashtag)>0:
                    final.append(hashtag)
                    
        ht_dict[id] = final

    ht_top = {}

    for i in ht_dict:
        ht_ct = {}
        for ht in ht_dict[i]:
            if ht in ht_ct:
                ht_ct[ht] += 1
            else:
                ht_ct[ht] = 1
        ht_top[i] = ht_ct
        
    ht_top_sorted = {}

    for i in ht_top:
        ht_top_sorted[i] = []
        for j in sorted(ht_top[i],key=ht_top[i].get,reverse=True):
            if ht_top[i][j] >= min:
                ht_top_sorted[i].append([j,ht_top[i][j]])
                
    return ht_top_sorted
