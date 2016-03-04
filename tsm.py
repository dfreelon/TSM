#!/usr/bin/python3

# TSM (Twitter Subgraph Manipulator) for Python 3
# release 6 (03/04/16)
# (c) 2014, 2015, 2016 by Deen Freelon <dfreelon@gmail.com>
# Distributed under the BSD 3-clause license. See LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause for details.

# This Python module contains a set of functions that create and manipulate Twitter and Twitter-like (directed, long-tailed, extremely sparse) network communities/subgraphs in various ways. The only Twitter-specific functions are t2e, get_top_rts, and get_top_hashtags; the rest can be used with any directed edgelist. It functions only with Python 3.x and is not backwards-compatible (although one could probably branch off a 2.x port with minimal effort).

# Warning: TSM performs no custom error-handling, so make sure your inputs are formatted properly! If you have questions, please let me know via email.

# FUNCTION LIST

# load_data: Loads data quickly

# save_csv: Quick CSV output

# t2e: Converts raw tweets into edgelist format (retweets and @-mentions, not follows)

# get_top_communities: A wrapper for Thomas Aynaud's implementation of the Louvain method for community detection. Gets the top k or (k*100)% largest communities by membership in a network and then outputs a file/variable containing the community labels and in-degrees of each user.

# calc_ei: Calculates the E-I index (a measure of insularity) of each community detected by get_top_communities

# _get_shared_ties: An extension of calc_ei that shows how "close" each community is to all of the others in terms of shared ties

# get_top_rts: Gets the most-retweeted tweets within each community

# match_communities: Compares community membership within two networks, A and B, and gives the best match found in B for each community in A

# get_intermediaries: Discovers which nodes intermediate between which communities

# get_top_hashtags: Gets the most-used hashtags in each community

# get_top_links: Gets the most-used hyperlinks or link domains in each community

# shared_ties_grid: Coaxes output of _get_shared_ties into a convenient grid format

# REQUIRED MODULES

#Below are all this module's dependencies. Everything except NetworkX and community comes standard with Python. You can get NetworkX here: http://networkx.github.io/ or through pip. You'll also need Thomas Aynaud's implementation of the Louvain method for community detection (python-louvain, which is where the community module lives), which is available here: https://bitbucket.org/taynaud/python-louvain or through pip. (Note that only the Py3-compliant version 0.4 of python-louvain will work with TSM.)

import collections
import community
import copy
import csv
import networkx as nx
import operator
import random
import re

# FUNCTIONS

# load_data: load data from a string or variable
# Arguments:
    # data: If load_data is fed a string, it assumes it is a path to a CSV file and attempts to load the contents into a list of lists. If it is fed a variable, it creates a deep copy.
    # enc: the character encoding of the file you're trying to open. See https://docs.python.org/3.4/library/codecs.html#standard-encodings
# Output:
    # A list of lists representing the contents of a CSV file, or a deep copy of a variable.

def load_data(data,enc='utf-8'):
    if type(data) is str:
        csv_data = []
        with open(data,'r',encoding = enc,errors = 'replace') as f:
            reader = csv.reader((line.replace('\0','') for line in f)) #remove NULL bytes
            for row in reader:
                if row != []:
                    csv_data.append(row)
        print('Data loaded from file "' + data + '".')
        return csv_data
    else:
        print('Data loaded.')
        return copy.deepcopy(data)

# save_csv: save tabular data to a CSV file
# Arguments:
    # filename: a string representing the filename to save to.
    # data: a list of lists containing your data. If fed anything else, save_csv may behave erratically.
    # use_quotes: If this flag is set to True, save_csv will add double quotes around each value before saving to disk. This flag will also convert all existing double quotes to single quotes to avoid delimiter confusion. If set to False, delimiting quotes will not be added.
    # file_mode: a string variable representing any of the standard modes for the open function. See https://docs.python.org/3.4/library/functions.html#open
    # enc: the character encoding for the file you're trying to save. See https://docs.python.org/3.4/library/codecs.html#standard-encodings
# Output:
    # save_csv returns nothing, but should leave a text file in the Python's current working directory containing the data in the data variable, assuming that directory is writeable. 
    
def save_csv(filename,data,use_quotes=False,file_mode='w',enc='utf-8'): #this assumes a list of lists wherein the second-level list items contain no commas
    with open(filename,file_mode,encoding = enc) as out:
        for line in data:
            if type(line) is not list and type(line) is not tuple:
                line = [line] #forces all items in 'data' to be lists
            if use_quotes == True:
                row = '"' + '","'.join([str(i).replace('"',"'") for i in line]) + '"' + "\n"
            else:
                row = ','.join([str(i) for i in line]) + "\n"
            out.write(row)
    print('Data saved to file "' + filename + '".')

# t2e: convert raw Twitter data to edgelist format
# Description: t2e takes raw Twitter data as input and outputs an edgelist consisting of the names of the tweet authors (col 1) and the names of the nodes mentioned and/or retweeted (col 2). 
# Arguments: 
    # tweet_data: One of two things:
        # 1. a string representing a path to a comma-delimited CSV file with tweet author screen names listed in col 1 and corresponding tweet text in col 2, OR 
        # 2. a list of lists wherein each second-degree list has a len of 2 with a tweet author screen name at index 0 and a corresponding fulltext tweet at index 1. 
    # extmode: see below
    # enc: the character encoding of the file you're trying to open. See https://docs.python.org/3.4/library/codecs.html#standard-encodings
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_edgelist.csv
# Output: An edgelist in the form of a Python list of lists. If save_prefix is set, the edgelist will also be saved as a CSV file.

# t2e has four extraction modes (specified by the extmode variable). Default is ALL.
# ALL = do not differentiate between retweets and non-retweets, include isolates (default)
# ALL_NO_ISOLATES = do not differentiate between retweets and non-retweets, exclude isolates
# RTS_ONLY = retweets only, exclude isolates
# AT_MENTIONS_ONLY = non-retweets (@-mentions) only, exclude isolates
# REPLIES_ONLY = only tweets in which the first or second character is an "@", exclude isolates

def t2e(tweet_data,extmode='ALL',enc='utf-8',save_prefix=''):
    authors = []
    tweets = []
    final = []

    if type(tweet_data) is str:
        f = open(tweet_data,'r',encoding = enc,errors = 'replace')
        tweet_data = csv.reader(f)

    for row in tweet_data:
        if extmode.upper() == 'ALL_NO_ISOLATES':
            condition = '@' in row[1]
        elif extmode.upper() == 'RTS_ONLY':
            condition = 'rt @' in row[1].lower()
        elif extmode.upper() == 'AT_MENTIONS_ONLY':
            condition = '@' in row[1] and 'rt @' not in row[1].lower()
        elif extmode.upper() == 'REPLIES_ONLY':
            condition = row[1][0] == '@' or row[1][1] == '@'
        else:
            condition = True
        if condition is True:
            authors.append(re.sub('[^A-Za-z0-9_]','',row[0].lower().strip()))
            tweets.append(' ' + row[1].lower() + ' ')
    if type(tweet_data) is str: 
        f.close()

    if extmode == 'RTS_ONLY': #only the RTed username is pulled from each RT
        for i,j in enumerate(tweets):
            ts = j.split('rt @')[1]
            try:
                rted = ts[:re.search('[^a-z0-9_]',ts).start()]
            except AttributeError:
                rted = ts
            if len(authors[i]) >= 1 and authors[i] != rted: #prevents ppl from manually RTing themselves
                final.append([authors[i],rted])

    else: #the code below is necessary to pull multiple mentioned users from single tweets
        tweets = [t.split('@') for t in tweets] #splits each tweet along @s
        for n,chunk in enumerate(tweets):
            ment_users = [t[:re.search('[^A-Za-z0-9_]',t).start()].lower().strip() for t in chunk if re.search('[^A-Za-z0-9_]',t) is not None]
            final.extend([[authors[n],name] for name in ment_users if len(name.strip()) > 0])
          
    print('Edge list created.')
    
    if len(save_prefix) > 0:
        outfile = save_prefix + '_edgelist.csv'
        save_csv(outfile,final)
    
    return final

# get_top_communities: Get top k communities by membership
# Description: This function runs the Louvain method for community detection on an edgelist and returns the names within each of the top k detected communities, the community to which each name belongs, and each name's in-degree. It's basically a wrapper for Thomas Aynaud's excellent Python implementation of Louvain (original version here: http://perso.crans.org/aynaud/communities/) with a few upgrades I found useful. See Blondel, V. D., Guillaume, J. L., Lambiotte, R., & Lefebvre, E. (2008). Fast unfolding of communities in large networks. Journal of Statistical Mechanics: Theory and Experiment, 2008(10), P10008.
# Arguments:
    # edges_data: An edgelist of the type exported by t2e. Can be a list of lists or a path to a CSV file.
    # top_comm: This variable can either be an integer or a decimal (float) between 0 and 1. If an integer, it represents the top k communities by node population to be analyzed. If a decimal, it represents the top (k*100)% of communities by population to be analyzed. These will be the communities which this module's functions will manipulate. For large Twitter networks, I have found it fruitful to work with the top ten largest retweet or @-mention communities. The higher this integer or decimal, the longer TSM will take to process your data. Enter 1.0 to analyze all communities. Default is 10.
    # randomize: If this variable is set to True, the edgelist will be randomized before running the rest of the function. This will produce slightly different results on each run. If the variable is set to False, the edgelist will not be randomized and the results will always be the same. Default is True.
    # prominence_metric: The network metric by which nodes will be ranked in descending order in the nodes_list of your louvainObject. This variable may be assigned any per-node metric available in NetworkX (see http://networkx.github.io/documentation/networkx-1.9.1/ ). NetworkX's methods need to be written as strings (e.g. 'in_degree'); functions need to be written with the appropriate module prefix(es) and without quotes (e.g. tsm.nx.eigenvector_centrality). Default is 'in_degree'.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_communities.csv
# Output: An object of the custom class 'louvainObject' with the following attributes:
    # node_list: A list of lists containing each unique node in the largest communities as defined above by the top_comm variable, the ID of the community to which it belongs, and its in-degree.
    # n_nodes: A dict in which the keys are community IDs and the values are integers representing the number of nodes belonging to each community
    # n_communities: An integer representing the total number of communities detected by the algorithm.
    # modularity: A float representing the network's modularity.
    # node_propor: A float representing the proportion of all nodes included within the largest communities.
    # edge_propor: A float representing the proportion of all edges included within the largest communities.

class louvainObject:
    '''an object class with attributes for various Louvain-related data and metadata'''
    def __init__(self,node_list,n_nodes,n_communities,modularity,node_propor,edge_propor):
        self.node_list = node_list
        self.n_nodes = n_nodes
        self.n_communities = n_communities
        self.modularity = modularity
        self.node_propor = node_propor
        self.edge_propor = edge_propor

def get_top_communities(edges_data,top_comm=10,randomize=True,prominence_metric='in_degree',save_prefix=''):
    edge_list = load_data(edges_data)
    if randomize == True:
        random.shuffle(edge_list)

    non_dir = nx.Graph()
    non_dir.add_edges_from(edge_list)
    print("Non-directed network created.")
    allmods = community.best_partition(non_dir)
    print("Community partition complete.")
    uniqmods = {}

    for i in allmods: #creates a dict of unique communities and the n of times they occur
        if allmods[i] in uniqmods:
            uniqmods[allmods[i]] += 1
        else:
            uniqmods[allmods[i]] = 1
    
    n_communities = len(uniqmods)
    
    if (top_comm > 0 and top_comm < 1) or top_comm == 1.0: 
        top_comm = int(round(n_communities * top_comm,0))
    
    top_n = sorted(uniqmods,key=uniqmods.get,reverse=True)[0:top_comm] #gets a list of the top k communities by node count as defined by the top_comm variable
    filtered_nodes = {}

    for i in allmods: #creates a dict containing only handles belonging to one of the top k communities
        if allmods[i] in top_n:
            filtered_nodes[i] = allmods[i]

    top_edge_list = [i for i in edge_list if i[0] in filtered_nodes and i[1] in filtered_nodes]
    
    di_net = nx.DiGraph()
    di_net.add_edges_from(top_edge_list)
    try:    
        ind = getattr(di_net,prominence_metric)()
    except (AttributeError,TypeError):
        ind = prominence_metric(di_net)
    outlist = []

    for i in filtered_nodes:
        outlist.append([ind[i],i,str(filtered_nodes[i]),str(ind[i])])

    outlist.sort(reverse=True)
    for i in outlist:
        del i[0]

    mod = round(community.modularity(allmods,non_dir),2)
    node_propor = round((len(filtered_nodes)/len(allmods))*100,2)
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
        if type(prominence_metric) is str:
            prominence_header = prominence_metric
        else:
            prominence_header = prominence_metric.__name__
        outlist.insert(0,['name','community',prominence_header])
        outfile = save_prefix + '_communities.csv'
        save_csv(outfile,outlist)
    
    return louvainObject(outlist,n_nodes,n_communities,mod,node_propor,edge_propor)
     
# calc_ei: Calculate EI index for top k communities
# Description: This function calculates Krackhardt & Stern's EI index for each community represented in a file or variable output by get_top_communities. The EI index ranges between 1 and -1, with 1 indicating that all the community's ties are with outsiders, -1 indicating they are all with members, and 0 indicating equal numbers of ties with members and outsiders. See Krackhardt, D., & Stern, R. N. (1988). Informal networks and organizational crises: An experimental simulation. Social psychology quarterly, 123-140.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities. Can be a variable (a list of lists) or a path to a CSV file. 
    # edges_data: An edgelist of the type exported by t2e. Can be a variable (a list of lists) or a path to a CSV file.
    # all_output: If set to True, the function _get_shared_ties will execute after calc_ei has finished. If set to False, _get_shared_ties will not execute. Default is True.
    # pause: If set to True, the function will pause and wait for a key strike before displaying the results of _get_shared_ties. If set to False, it will not pause. Default is True.
    # weight_edges: If set to True, the function will include duplicate edges in the EI calculations. If set to False, the edgelist will be unweighted--in other words all duplicate edges will be removed. For example, if the userA->userB edge has a weight of 5 (meaning A linked to B five distinct times), the function will count that as a single tie. Default is True.
    # verbose: If set to True, calc_ei will print some of its output to the shell prompt. If set to False, this output will be suppressed. Default is False.
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_communities.csv
# Output: An object of the custom class "eiObject" containing the following attributes:
    # n_nodes: An OrderedDict in which the keys are community IDs and the values are integers representing the number of nodes belonging to each community
    # index: An OrderedDict in which the keys are community IDs and the values are corresponding EI indices.
    # internal_ties: An OrderedDict in which the keys are community IDs and the values are counts of internal edges.
    # external_ties: An OrderedDict in which the keys are community IDs and the values are counts of external edges.
    # mean_ei: The mean of the EI indices from index.
    # If the all_output flag is set to True, the returned eiObject will also include the following optional attributes:
        # total_ties: An OrderedDict in which the keys are community IDs and the values are total counts of all ties involving at least one community member.
        # received_ties: An OrderedDict in which each key is a community ID and each value is a count of all ties wherein the recipient is a community member.
        # sent_ties: An OrderedDict in which each key is a community ID and each value is a count of all ties wherein the sender is a community member.
        # r_s: An OrderedDict in which each key is a community ID and each value is the received count minus the sent count.
        # adj_in: An OrderedDict of dicts in which each key is a community ID (A), each second-level key is a community ID (B), and each second-level value is the number of edges originating in B and pointing to A.
        # adj_out: An OrderedDict of dicts in which each key is a community ID (A), each second-level key is a community ID (B), and each second-level value is the number of edges originating in A and pointing to B.
        
class eiObject:
    '''an object class with attributes for various EI-index-related data and metadata'''
    def __init__(self,n_nodes=None,ei_indices=None,internal_ties=None,external_ties=None,mean_ei=None,total_ties=None,received_ties=None,sent_ties=None,r_s=None,adj_in=None,adj_out=None):
        self.n_nodes = n_nodes
        self.ei_indices = ei_indices
        self.internal_ties = internal_ties
        self.external_ties = external_ties
        self.mean_ei = mean_ei
        self.total_ties = total_ties
        self.received_ties = received_ties
        self.sent_ties = sent_ties
        self.r_s = r_s
        self.adj_out = adj_out
        self.adj_in = adj_in
        
def calc_ei(nodes_data,edges_data,all_output=True,pause=False,weight_edges=True,verbose=False,save_prefix=''):
    if weight_edges == False:
        print("Calculating EI indices using *UNweighted* edges.\n")
    else:
        print("Calculating EI indices using *weighted* edges.\n")
    
    nodes = load_data(nodes_data)
    if nodes[0][0] == 'name':
        del nodes[0] #remove headers from CSV
    
    edges = load_data(edges_data)
    modclass = [i[1] for i in nodes]
    moduniq = {}

    for i in modclass: #get and count unique community IDs
        if i in moduniq:
            moduniq[i] += 1
        else:
            moduniq[i] = 1

    mu_top = sorted(moduniq,key=moduniq.get,reverse=True) #get all communities from node file
    top_nodes_list = [i for i in nodes if i[1] in mu_top]   
    top_nodes = {node[0]:node[1] for node in top_nodes_list} #create dict of screen names and community IDs
    
    if weight_edges == False:
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
    mean_ei = round(sum(ei_indices.values())/len(ei_indices.values()),3)
    
    if verbose == True:
        print("***EI indices***\n")
        print("Community\tEI index")
        for i in ei_ord:
            print(str(i)+"\t"+str(ei_ord[i]))
            
        print("Mean EI:\t",mean_ei)
    
    n_nodes = {}
    for i in nodes:
        if i[1] in n_nodes:
            n_nodes[i[1]] += 1
        else:
            n_nodes[i[1]] = 1
    
    if pause == True:
        input('Press any key to continue...')
    
    if all_output == True:
        ei_out = _get_shared_ties(mu_top,top_edges,ei_int,ei_ext,n_nodes,verbose)
    else:
        ei_out = eiObject()
        
    if len(save_prefix) > 0:
        ei_list = []
        for i in ei_ord:
            ei_list.append([str(i),str(ei_ord[i])])
        ei_list.insert(0,['Community IDs','EI indices']) 
        save_csv(save_prefix + '_ei_indices.csv',ei_list)
    print("\n")
    
    ei_out.n_nodes = collections.OrderedDict(sorted(n_nodes.items()))
    ei_out.ei_indices = ei_ord
    ei_out.internal_ties = ei_int
    ei_out.external_ties = ei_ext
    ei_out.mean_ei = mean_ei
    return ei_out

# _get_shared_ties: Obtains numbers of shared ties between each community and all others
# Description: This function reveals how a given community's "external" edges are distributed among the other communities. It is not a standalone function: it can only be run by using the "PROX" or "PROX_PAUSE" option from calc_ei. So don't try to enter the following arguments into the function yourself unless you know what you're doing.
# Arguments:
    # top_community_ids: A list of the top k communities by membership.
    # top_edges: A list of all edges both of whose nodes belong to one of the top k communities.
    # ei_int: A dict in which each key is one of the top k community IDs and each value is the number of edges in which both nodes are members of that community.
    # ei_ext: A dict in which each key is one of the top k community IDs and each value is the number of edges in which one node is a member of that community and the other is a member of any other community.
    # n_nodes: A dict in which each key is one of the top k community IDs and each value is the total number of nodes in that community.
    # verbose: If set to True, _get_shared_ties will print some of its output to the shell prompt. If set to False, this output will be suppressed. The value of this variable is inherited from calc_ei, where its default value is False.
# Output: The optional output attributes for the "eiObject" class (see above).
    
def _get_shared_ties(top_community_ids,top_edges,ei_int,ei_ext,n_nodes,verbose):
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
            if j[2] != i and j[3] == i:
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
        incoming = sum(adj_in[i].values())
        received_dict[i] = incoming
        outgoing = sum(adj_out[i].values())
        sent_dict[i] = outgoing
        r_s = round(incoming - outgoing,3)
        r_s_dict[i] = r_s
        
        if verbose == True:
            print("\nCommunity\tSize\tInternal\tReceived\tSent\tReceived - Sent")
            print(str(i)+"\t"+str(n_nodes[i])+"\t"+str(round(ei_int[i]/total,3))+"\t"+str(round(incoming/total,3))+"\t"+str(round(outgoing/total,3))+"\t"+str(round(r_s/total,3))+"\n")
            for j in top_community_ids:
                if i != j:
                    if j in adj_out[i]:
                        print(str(j)+"-s\t"+str(round(adj_out[i][j]/total,3)))
                    if j in adj_in[i]:
                        print(str(j)+"-r\t"+str(round(adj_in[i][j]/total,3)))
    
    prox_out = eiObject()
    prox_out.adj_in = collections.OrderedDict(sorted(adj_in.items()))
    prox_out.adj_out = collections.OrderedDict(sorted(adj_out.items()))
    prox_out.total_ties = collections.OrderedDict(sorted(total_dict.items()))
    prox_out.received_ties = collections.OrderedDict(sorted(received_dict.items()))
    prox_out.sent_ties = collections.OrderedDict(sorted(sent_dict.items()))
    prox_out.r_s = collections.OrderedDict(sorted(r_s_dict.items()))
    
    return prox_out

# get_top_rts: Gets the most-retweeted tweets in a Twitter dataset with community IDs
# Description: This function returns a list of the most-retweeted tweets along with the community IDs of the tweet authors and retweet counts. This allows researchers to easily view the most-retweeted tweets within each community.
# Arguments:
    # tweets_file: A CSV file containing tweets formatted for t2e as specified above. 
    # nodes_data: A community-partition dataset of the type exported by get_top_communities. Can be a variable (a list of lists) or a path to a CSV file. 
    # min_rts: An integer indicating the minimum number of retweets to be included in the output. Default is 5. Increasing this number will reduce your filesize and processing time; decreasing it will do the opposite.
    # lc: A boolean value determining whether the retweets will be converted to lowercase before counting duplicates. Lowercasing retweets may increase retweet counts but it will break case-sensitive hyperlinks such as those generated by Twitter. Default is False.
    # enc: the character encoding of the file you're trying to open and/or save. See https://docs.python.org/3.4/library/codecs.html#standard-encodings
    # save_prefix: Add a string here to save your file to CSV. Your saved file will be named as follows: 'string'_top_RTs.csv
# Output: A list of lists, each of which contains the name of the retweeted user, the full text of the retweet, the user's community ID, and the number of times the tweet was retweeted. This list is ranked in descending order of retweet count.

def get_top_rts(tweets_file,nodes_data,min_rts=5,lc=False,enc='utf-8',save_prefix=''):
    rts = []
    node_dict = {i[0]:i[1] for i in load_data(nodes_data)}
    
    with open(tweets_file,'r',encoding=enc,errors='replace') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[1].startswith('RT @') and row[1].find(':')>-1:
                if lc == False:
                    rts.append(row[1])
                else:
                    rts.append(row[1].lower())
    
    rts_ct = collections.Counter(rts).most_common()
    rts_ct_out = []
    
    for n,i in enumerate(rts_ct):
        rted = i[0][i[0].find('@')+1:i[0].find(':')].lower()
        try:
            rts_ct_out.append([rted,rts_ct[n][0],node_dict[rted],rts_ct[n][1]])
        except KeyError:
            pass
            
    rts_ct_out = [i for i in rts_ct_out if i[3] >= min_rts]

    if len(save_prefix) > 0:
        rts_ct_out.insert(0,['rted_user','rt_text','community','n_rts'])
        out_fn = save_prefix + '_top_RTs.csv'
        save_csv(out_fn,rts_ct_out,True)
        return rts_ct_out[1:]
    
    else:
        return rts_ct_out
    
# match_communities: Find the best community matches between two networks using the weighted Jaccard coefficient
# Description: This function takes two partitioned networks, A and B, and finds the best match for each community in A among the communities in B. Matches are determined by measuring membership overlap with either the weighted or the unweighted Jaccard coefficient, depending on how the weight_nodes parameter is set. To reduce processing time, only the top (propor * 100)% of nodes by in-degree in each community are compared. The weighted Jaccard comparisons are weighted by in-degree, meaning that higher in-degree nodes count more toward community similarity. This is based on the assumption that nodes of higher in-degree play a proportionately larger role in terms of maintaining community coherence.
# Arguments:
    # nodes_data_A: A community-partition dataset of the type exported by get_top_communities (network A). Can be a variable or a path to a CSV file. 
    # nodes_data_B: A community-partition dataset of the type exported by get_top_communities (network B). Can be a variable or a path to a CSV file.
    # nodes_propor: A float variable greater than 0 and less than 1 representing the per-community proportion of top in-degree nodes to compare between A and B. Default is 0.01 (1%). Increasing this number will increase processing time.
    # jacc_threshold: A float variable greater than 0 and less than 1 representing the Jaccard value above which community pairs will be considered valid matches. Default is 0.3. I would caution against using this blindly--try a few different values and see what seems to make sense for your data.
    # dc_threshold: A float variable representing the Jaccard value above which convergences and divergences (as defined below) will be considered valid. I suggest setting this somewhat lower than jacc_threshold. 
    # weight_edges: If set to True, the function will weight the Jaccard coefficient by each node's in-degree to match communities between networks A and B. If set to False, it will use the unweighted Jaccard coefficient. Default is True.
    # verbose: If set to True, match_communities will print some of its output to the shell prompt. If set to False, this output will be suppressed. Default value is False.
# Output: An object of the custom class "cMatchObject" containing the following attributes:
    # best_match: An OrderedDict in which the keys are the best community matches for network A in network B (in AxB format where A and B are community IDs) and the values are the corresponding Jaccard values.
    # shared_node: An OrderedDict in which the keys are the best matches for network A in network B (in AxB format where A and B are community IDs) and the values comprise the set of top nodes shared between the two networks.
    # nonzero_jacc: An OrderedDict of dicts in which each first-order key is a community ID from network A, each second-order key is a community ID from network B, and each second-order value is the nonzero Jaccard between the A and B IDs.
    # diverge: An OrderedDict in which each key is a community ID from network A and each value is a list containing two or more IDs from network B. These IDs represent divergences, i.e. situations in which two or more month-B communities share Jaccard values exceeding jacc_threshold with a single month-A community.
    # converge: An OrderedDict in which each key is a community ID from network B and each value is a list containing two or more IDs from network A. These IDs represent convergences--the logical converses of divergences--i.e. situations in which two or more month-A communities share Jaccard values exceeding jacc_threshold with a single month-B community.

class cMatchObject:
    '''an object class with attributes for various matched-community data and metadata'''
    def __init__(self,best_matches=None,shared_nodes=None,nonzero_jaccs=None,divergences=None,convergences=None):
        self.best_matches = best_matches
        self.shared_nodes = shared_nodes
        self.nonzero_jaccs = nonzero_jaccs
        self.divergences = divergences
        self.convergences = convergences

def match_communities(nodes_data_A,nodes_data_B,nodes_filter=0.01,jacc_threshold=0.3,dc_threshold=0.2,weight_edges=True,verbose=False):
    nodesA = load_data(nodes_data_A)
    if nodesA[0][0] == 'name':
        del nodesA[0]

    nodesB = load_data(nodes_data_B)
    if nodesB[0][0] == 'name':
        del nodesB[0]

    filtered_nodes_1 = _filter_nodes(nodesA,nodes_filter)
    filtered_nodes_2 = _filter_nodes(nodesB,nodes_filter)
    
    hijacc = 0
    best_match = {}
    nonzero_jacc = {}

    for i in filtered_nodes_1:
        nonzero_jacc[i] = {}
        hix = i+'x'
        for j in filtered_nodes_2:
            intersect = set(filtered_nodes_1[i]).intersection(set(filtered_nodes_2[j])) #get intersection of names for month 1 + 2
            union_both = set(filtered_nodes_1[i]).union(set(filtered_nodes_2[j]))
            if weight_edges == True:
                inter_weights = [int(k[2]) for k in nodesA if k[0] in intersect] + [int(k[2]) for k in nodesB if k[0] in intersect] #pull intersection in-degrees from both months and combine into a single list
                union_weights = [int(k[2]) for k in nodesA if k[0] in union_both] + [int(k[2]) for k in nodesB if k[0] in union_both] #pull union in-degrees from both months and combine into a single list
                jacc = sum(inter_weights)/sum(union_weights)
            else: #if weight_edges is set to anything other than 'WEIGHT_JACCARD', set all weights to 1 for each node
                inter_weights = len(intersect) 
                union_weights = len(union_both) 
                jacc = inter_weights/union_weights
            if jacc > 0:
                if verbose == True:
                    print(i+'x'+j+"\t"+str(round(jacc,4)))
                nonzero_jacc[i][j] = round(jacc,4) #
            if jacc > hijacc:
                hijacc = round(jacc,4)
                hix = i+'x'+j
        if verbose == True:
            print('high:'+"\t"+hix+"\t"+str(hijacc)+"\n")
        best_match[hix] = hijacc
        hijacc = 0

    shared_node = {}    
    if verbose == True:
        print('Top community matches:')
    for i in best_match:
        if best_match[i] >= jacc_threshold:
            nodes_A = set(filtered_nodes_1[i[:i.find('x')]])
            nodes_B = set(filtered_nodes_2[i[i.find('x')+1:]])
            shared_node[i] = nodes_A.intersection(nodes_B)
            sn = ', '.join(shared_node[i])
            if verbose == True:
                print(i,"\t",best_match[i],"\t",sn,"\n")
    
    diverge = {}
    for i in nonzero_jacc: #divergence test
        if len(nonzero_jacc[i]) > 0:
            jacc_tmp = sorted(nonzero_jacc[i].values(),reverse=True)
            highest_key = sorted(nonzero_jacc[i],key=nonzero_jacc[i].get,reverse=True)[0]
            for j in nonzero_jacc[i]:
                if highest_key != j and jacc_tmp[0] >= dc_threshold and nonzero_jacc[i][j] >= dc_threshold:
                    if verbose == True:
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
                            if verbose == True:
                                print('Convergence of month-A communities',i,'and',j,'into month-B community',k)
    
    converge = {}
    for i in conv:
        if len(conv[i]) > 0:
            converge[i] = conv[i]
    
    match_out = cMatchObject()
    match_out.best_matches = collections.OrderedDict(sorted(best_match.items()))
    match_out.shared_nodes = collections.OrderedDict(sorted(shared_node.items()))
    match_out.nonzero_jaccs = collections.OrderedDict(sorted(nonzero_jacc.items()))
    match_out.divergences = collections.OrderedDict(sorted(diverge.items()))
    match_out.convergences = collections.OrderedDict(sorted(converge.items()))
    
    return match_out

# _filter_nodes: Get the nodes of highest in-degree in a network OR the nodes in a fixed list that appear in a network
# Desciption: This is a helper function for match_communities and get_intermediaries that simply loads the top (propor * 100)% of nodes by in-degree OR a preset list of nodes in each community in a partitioned network into a list.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # propor: This variable can either be a float greater than 0 and less than 1 OR a list of node names. If a float, the variable represents the proportion of top in-degree nodes to extract from each community. If a list of nodes, it represents the specific set of nodes to extract from nodes_data when present. Default is 0.01 (1%). Increasing the float will increase processing time.
#Output: A dict whose keys are community IDs and whose values are filtered lists of node names.
    
def _filter_nodes(nodes_data,nodes_filter=0.01):
    uniq_cl = set([i[1] for i in nodes_data]) #creates a unique list of the top 10 communities from each community file

    filtered_nodes = {} #creates a dict of lists. Each list contains the top [propor*100]% most-connected nodes within each community
    
    if type(nodes_filter) is float:
        for i in uniq_cl:
            cltemp = [j[0] for j in nodes_data if j[1] == i]
            pct = int(len(cltemp) * nodes_filter)
            filtered_nodes[i] = [j for j in cltemp][0:pct]
    else:
        nf2 = [[j[0],j[1]] for j in nodes_data if j[0] in nodes_filter]
        for i in uniq_cl:
            filtered_nodes[i] = [j[0] for j in nf2 if j[1] == i]
    
    return filtered_nodes

# get_intermediaries: Identifies nodes who are heavily connected to by multiple network communities
# Description: When analyzing partitioned networks, it is sometimes helpful to know not only which nodes are high in betweenness centrality, but also which communities are bridged by such nodes. This function identifies high in-degree nodes whose ties are relatively evenly distributed across at least two communities.
# Arguments:
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # edges_data: An edgelist of the type exported by t2e.
    # threshold: A float variable greater than 0 and less than 1 representing the minimum proportion of internal ties a given top node needs to receive from an external community to count as a bridge. For example, for node DF where the community most connected to DF is A, setting the threshold to 0.5 means that for DF to count as a bridge, the number of ties DF receives from second most-connected community B must equal at least 50% of the ties it receives from A.
    # nodes_filter: This variable can be either a float greater than 0 and less than 1 or a list of node names. If the former, it represents the proportion of top in-degree nodes to extract from each community. If the latter, it represents the collection of nodes to search for in each community. Default is 0.01 (1%). Increasing the float or list size will increase processing time.
    # verbose: If set to True, the shell will print a message every time a new node is added to the bridge list. Default is False.
    # zeropad: If zeropad is set to False, if a node from Community A receives no edges from Community B, get_intermediaries will omit community B from that node's dict of received ties. If zeropad is set to True, for each community like B, get_intermediaries will create a new dict item whose value is 0 (whereas otherwise that dict item would simply not exist). 
# Output: A list of lists, each of which contains a bridge node's in-degree (at index 0), its name (at index 1), and a dict in which each key is a community ID and each value is the N of ties the node received from that community (at index 2). Note: the community ID of the bridge node is not explicitly indicated in this dict, but it is almost always the ID with the highest N of received ties.
    
def get_intermediaries(nodes_data,edges_data,bridge_threshold=0.5,nodes_filter=0.01,verbose=False,zeropad=True):
    nodes = load_data(nodes_data)
    if nodes_data[0][0] == 'name':
        del nodes[0]
    edges = load_data(edges_data)
    filtered_nodes = _filter_nodes(nodes,nodes_filter)
    
    cmty_list = list(filtered_nodes.keys())
    node_dict = {i[0]:i[1] for i in nodes} #create dict of node names and community IDs
    bridge_cands = {}
    
    for cmty in filtered_nodes:
        for name in filtered_nodes[cmty]:
            if verbose == True:
                print('Analyzing node "' + name + '".')
            user_edges = []
            
            for i in edges: #pull all edges of which node is the recipient
                if name == i[1]:
                    user_edges.append(i)
            
            ue_minus = [i for i in user_edges if i[0] in node_dict] #remove all nodes not in the top k communities
            cmty_rts = {}
            
            for i in cmty_list:
                for j in ue_minus:
                    if node_dict[j[0]] == i:
                        if i in cmty_rts:
                            cmty_rts[i] += 1
                        else:
                            cmty_rts[i] = 1
                            
            list_rts_ct = sorted(list(cmty_rts.values()),reverse=True)
            if bridge_threshold > 0:
                add_bool = len(cmty_rts) >= 2 and list_rts_ct[1] >= list_rts_ct[0]*bridge_threshold #the N of ties to the 2nd-highest community must equal or exceed a minimum proportion of the N of ties to the highest community
            elif len(list_rts_ct) > 0:
                add_bool = True
            else:
                add_bool = False
            if add_bool is True:
                if verbose == True:
                    print('Node "' + name + '" added to the list.')
                cmty_rts = collections.OrderedDict(sorted(cmty_rts.items(),key=operator.itemgetter(1),reverse=True))
                bridge_cands[name] = cmty_rts
                
    bridge_list = []
    for i in bridge_cands:
        bridge_list.append([sum(bridge_cands[i].values()),i,bridge_cands[i]])
        
    bridge_list = sorted(bridge_list,reverse=True)
    
    if zeropad == True:
        for i in bridge_list:
            if len(i[2]) < len(cmty_list):
                omitted = [j for j in cmty_list if j not in i[2]]
                for k in omitted:
                    i[2][k] = 0
    
    return bridge_list

# get_top_hashtags: Collects the most-used hashtags in each community in descending order of popularity
# Description: This function collects the most-used hashtags in a set of tweets that's been partitioned into communities and organizes them first by community and then in descending order of popularity.
# Arguments:
    # tweets_data: a path to a CSV file (the only delimiter currently allowed is commas) with tweet authors listed in col 1 and corresponding tweet text in col 2. If col 1 contains any text, col 2 must as well, and vice versa.
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # min_ct: The minimum number of times a hashtag must appear in a given community to be included in that community's list. Increasing this number speeds processing. Default is 10.
    # rtl_ht: If set to True, the function will search for hashtags written with the hashmark on the right, such as those in right-to-left languages like Arabic and Hebrew. If set to False, it will not include such hashtags. Default is False.
# Output: A dict whose keys are community IDs and whose values are lists, the entries of which are tuples in which the first value is a hashtag and the second is the number of times it appears within the given community. Each list is arranged in descending order of hashtag prevalence.
    
def get_top_hashtags(tweets_data,nodes_data,min_ct=10,rtl_ht=False):
    tweets = [i for i in load_data(tweets_data) if i[0].strip() != '']  
    nodes = [i for i in load_data(nodes_data) if i[0].strip() != '']
    if nodes_data[0][0] == 'name':
        del nodes[0]

    clust_uniq = set([i[1] for i in nodes])
    node_dict = {i[0].lower():i[1] for i in nodes}
    tweets = [[i[0].lower(),i[1].lower()] for i in tweets if i[0].lower() in node_dict]
    ht_dict = {}

    for cid in clust_uniq:
        splitprep = [' ' + re.sub(r'[\\\"\'\.\,\-\:“”()!&\[\]]',' ',t[1]).lower().replace(u'\u200F','') + ' ' for t in tweets if '#' in t[1] and node_dict[t[0]] == cid] #fills in the list tweets with hashtags, lowercased, space-padded, cleaned and only if a hashmark exists in the tweet
        tweets_split = [t.split('#') for t in splitprep] #splits each tweet along #s
        final = []
        for chunk in tweets_split:
            f_hashtags = [t[:re.search('[\s\r\n\t]',t).start()].strip() for t in chunk if re.search('[\s\r\n\t]',t) is not None]  #strips out everything after the # sign, leaving (hopefully) a list of lists of hashtags
            final.extend(set([h for h in f_hashtags if len(h.strip()) > 0])) #use set so as not to count multiple iterations of the same hashtag used in a single tweet
        if rtl_ht == True:
            for chunk in tweets_split:
                r_hashtags = [t[t.rfind(' ')+1:].strip() for t in chunk]
                final.extend(set([h for h in r_hashtags if len(h) > 0]))
  
        ht_dict[cid] = final

    return _count_cmty_dups(ht_dict,min_ct)
    
# get_top_links: Collects the most-used hyperlinks or web domains in each community in descending order of popularity
# Description: This function collects the most-used hyperlinks or web domains in a set of tweets that's been partitioned into communities and organizes them first by community and then in descending order of popularity.
# Arguments:
    # tweets_data: a path to a CSV file (the only delimiter currently allowed is commas) with tweet authors listed in col 1 and corresponding tweet text in col 2. If col 1 contains any text, col 2 must as well, and vice versa.
    # nodes_data: A community-partition dataset of the type exported by get_top_communities.
    # min_ct: The minimum number of times a hyperlink or domain must appear in a given community to be included in that community's list. Increasing this number speeds processing. Default is 10.
    # domains_only: If set to True, get_top_links will extract only web domains (e.g. all articles from the New York Times will be counted under the nytimes.com domain). If set to False, it will extract full links and count distinct links with the same domain separately. Default is False.
    # remove_3ld: If set to True, the function will remove all third-level domains from the links (e.g. "www."). If set to False, it will leave all third-level domains intact. Default is False.
    # remove_tco: If set to True, the function will remove any t.co links from the results. If set to False, it will leave in any t.co links. Default is True.
# Output: A dict whose keys are community IDs and whose values are lists, each of which contains one community's top hyperlinks or web domains arranged in descending order of popularity.

def get_top_links(tweets_data,nodes_data,min_ct=10,domains_only=False,remove_3ld=False,remove_tco=True):
    tweets = [i for i in load_data(tweets_data) if i[0].strip() != '']  
    nodes = [i for i in load_data(nodes_data) if i[0].strip() != '']
    if nodes_data[0][0] == 'name':
        del nodes[0]

    clust_uniq = set([i[1] for i in nodes])
    node_dict = {i[0].lower():i[1] for i in nodes}
    tweets = [[i[0].lower(),i[1].replace('https','http')] for i in tweets if i[0].lower() in node_dict]
    links_dict = {}
    if remove_tco == True:
        tweets = [[i[0],i[1].replace('http://t.co/','')] for i in tweets]

    for cid in clust_uniq:
        splitprep = [' ' + re.sub(r'[\\"\'“”\[\]><]','',t[1]).replace(u'\u200F','') + ' ' for t in tweets if 'http://' in t[1] and node_dict[t[0]] == cid] #fills in the list tweets with hyperlinks, lowercased, space-padded, cleaned and only if 'http://' exists in the tweet
        tweets_split = [t.split('http://') for t in splitprep] #splits each tweet along 'http://'s
        final = []
        for chunk in tweets_split:
            links = [t[:re.search('[\s\r\n\t]',t).start()].strip() for t in chunk if re.search('[\s\r\n\t]',t) is not None] #strips out everything after the 'http://', leaving (hopefully) a list of lists of hyperlinks
            if domains_only == True:
                final.extend([hyperlink[:hyperlink.find('/')] for hyperlink in links if len(hyperlink.strip()) > 0 and '/' in hyperlink])
                final.extend([hyperlink for hyperlink in links if len(hyperlink.strip()) > 0 and '/' not in hyperlink])
            else:
                final.extend([hyperlink for hyperlink in links if len(hyperlink.strip()) > 0])

        if remove_3ld == True:
            for key,_ in enumerate(final):
                if final[key].count('.') >= 2:
                    final[key] = final[key][final[key].find('.')+1:]
                    
        links_dict[cid] = final

    return _count_cmty_dups(links_dict,min_ct)

# _count_cmty_dups: Helper function for get_top_hashtags and get_top_links
# Description: This function helps coax the data for get_top_hashtags and get_top_links into the proper format. You shouldn't need to alter it.
    
def _count_cmty_dups(dup_dict,min_ct):
    ht_top = {}

    for i in dup_dict:
        ht_ct = {}
        for ht in dup_dict[i]:
            if ht in ht_ct:
                ht_ct[ht] += 1
            else:
                ht_ct[ht] = 1
        ht_top[i] = ht_ct
        
    ht_top_sorted = {}

    for i in ht_top:
        ht_top_sorted[i] = []
        for j in sorted(ht_top[i],key=ht_top[i].get,reverse=True):
            if ht_top[i][j] >= min_ct:
                ht_top_sorted[i].append([j,ht_top[i][j]])
    try:
        del ht_top_sorted['community']
    except KeyError:
        pass            
    return ht_top_sorted

# shared_ties_grid: arranges counts or proportions of ties shared within and between top communities in a network into a grid
# Description: shared_ties_grid arranges the output of _get_shared_ties into a list of lists which is printable as a grid.
# Arguments:
    # ei_obj: a variable of type eiObject containing all the optional attributes.
    # rec_sent: a flag determining whether the off-diagonal grid cells will represent received edges ('REC'), sent edges ('SENT'), or sent and received edges summed ('ALL'). Default is 'ALL'.
    # calc_propor: If set to True, each cell value will represent a proportion of the total edges in the community indicated by index 0 of the given row. If set to False, shared_ties_grid will output edge counts. Default is False.
    # invert: If set to True, the function will output the reciprocals of all the off-diagonal cell values and zeroes for all diagonal values. Cells whose reciprocals would result in division by zero will be assigned a value of 1. The contents of the top row and leftmost column will remain unaltered. If set to True, non-reciprocal values (i.e., shared-tie counts or proportions) will be output. Default is False.
# Output: shared_ties_grid outputs a list of lists in the following format: 
    # Indices 1 through k of the first row contain all k communities represented in the eiObject. Index 0 is left blank.
    # The 0 indices of all remaining rows also contain all k communities represented in the eiObject. Thus the grid always has a size of k+1 x k+1.
    # Each off-diagonal grid "cell" represents either the count, inverted count, or proportion (depending on how the flags are set) of edges received or sent (or both) by the community indicated by index 0 of the kth row from or to the community indicated on the kth index of the first row (the "column"). Diagonal grid cells represent the proportions or counts of internal edges of the community indicated by index 0 of the given row.
    # Grids created by shared_ties_grid can easily be viewed in the shell using the following code (where ei is a variable of type eiObject created with the 'PROX' flag):
    # testgrid = shared_ties_grid(ei)
    # for i in testgrid:
    #     print(i)

def shared_ties_grid(ei_obj,rec_sent='ALL',calc_propor=False,invert=False):
    if rec_sent.upper() == 'REC':
        raw = ei_obj.adj_in
    elif rec_sent.upper() == 'SENT':
        raw = ei_obj.adj_out
    else:
        raw = {}
        for i in ei_obj.adj_in:
            raw[i] = {}
            for j in ei_obj.adj_in:
                if j in ei_obj.adj_in[i]:
                    in_add = ei_obj.adj_in[i][j]
                else:
                    in_add = 0
                if j in ei_obj.adj_out[i]:
                    out_add = ei_obj.adj_out[i][j]
                else:
                    out_add = 0
                raw[i][j] = in_add + out_add
    
    raw2 = {}
    
    for i in raw: #converts all subdict keys to ints
        raw2[int(i)] = {}
        for j in raw[i]:
            raw2[int(i)][int(j)] = raw[i][j]
            
    clist = sorted(list(raw2.keys()))
    
    for i in raw2:
        raw2[i][i] = ei_obj.internal_ties[str(i)] #add internal ties
        for j in clist:
            if j not in raw2[i]: #add zeroes for disconnected communities
                raw2[i][j] = 0
    
    raw3 = {}
    
    for i in raw2: #put the subdict keys in numerical order
        raw3[i] = collections.OrderedDict(sorted(raw2[i].items()))
    
    raw3 = collections.OrderedDict(sorted(raw3.items())) #put the main dict keys in order
    outlist = []
    
    for n,i in enumerate(raw3):
        if calc_propor == True: #if PROPOR flag is set, divide each value by total N of ties
            outlist.append([round(j/ei_obj.total_ties[str(i)],3) for j in list(raw3[i].values())])
        else:
            outlist.append(list(raw3[i].values()))
        outlist[n].insert(0,i)
    
    outlist.insert(0,['']+clist)
    print('Grid created.')
    
    if invert == True:
        recip = []
        for n,i in enumerate(outlist):
            recip.append([])
            for x,j in enumerate(outlist[n]):
                if n != x and n != 0 and x != 0:
                    try:
                        recip[n].append(format(1/outlist[n][x],'f'))
                    except ZeroDivisionError:
                        recip[n].append(1)
                elif n == x and n != 0 and x != 0:
                    recip[n].append(0)
                else:    
                    recip[n].append(outlist[n][x])
        return recip
    else:    
        return outlist
