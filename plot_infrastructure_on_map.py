"""
In this file we plot infrastructure investments on a map of Norway

(much code is copied from plot_flow_on_map.py)
"""

import warnings
warnings.filterwarnings("ignore")

# IMPORTS

import numpy as np
import pandas as pd
import pickle
from mpl_toolkits.basemap import Basemap #for creating the background map
import matplotlib.pyplot as plt #for plotting on top of the background map
import matplotlib.patches as patches #import library for fancy arrows/edges

####################################################################

# FUNCTIONS

# a. Charging

# function that processes the charging infrastructure data, puts it in a data frame
def process_charging_infra(y_charging, sel_time_period, sel_scenario="BBB", cumulative=False):
    
    #initialize lists that will store output
    arcs = []       # all relevant arcs
    infra = []      # investment levels in charging infrastructure

    for index, row in y_charging.iterrows():
        if row["mode"] == "Road" and row["fuel"] == "Battery electric": # check road-electric
            if row["scenario"] == sel_scenario: # check scenario
                if (cumulative == True and row["time_period"] <= sel_time_period) or (cumulative == False and row["time_period"] == sel_time_period):
                    #temporarily store current arc and its opposite
                    cur_arc = (row["from"], row["to"])
                    cur_cra = (row["to"], row["from"]) #opposite arc
                    #check if new arc
                    if cur_arc not in arcs and cur_cra not in arcs: #new arc
                        arcs.append(cur_arc) #append forward arc (we don't care about forward/backward)
                        #add zero values for the corresponding lists (initialization)
                        infra.append(0.0)
                    #find index of current arc (or cra) in list "arcs"
                    cur_arc_ind = None
                    if cur_arc in arcs:
                        cur_arc_ind = arcs.index(cur_arc)
                    elif cur_cra in arcs:
                        cur_arc_ind = arcs.index(cur_cra)
                    #store corresponding flows in lists
                    infra[cur_arc_ind] += row["weight"]
    


    #store aggregate flows in a dataframe
    df_infra = pd.DataFrame()
    df_infra["arc"] = arcs
    df_infra["orig"] = [""]*len(arcs)
    df_infra["dest"] = [""]*len(arcs)
    df_infra["infra"] = infra

    #fix origins and destinations
    for i in range(len(df_infra)):
        df_infra.orig[i] = str(df_infra.arc[i][0])
        df_infra.dest[i] = str(df_infra.arc[i][1])

    return df_infra

# function that plots flow on the map
def plot_charging_infra_on_map(df_infra, base_data, show_fig=True, save_fig=False, filename="test.png"):    
    """
    Create a plot on the map of Norway with infrastructure investments

    INPUT
    df_infra:       dataframe with investment in charging infrastructure
    base_data:      base model data (only used to extract N_NODES)
    show_fig:       indicate whether to show the figure
    save_fig:       indicate whether to save the figure (filename is determined automatically)
    
    OUTPUT
    figure that is shown and/or saved to disk if requested
    """

    ####################################
    # a. Extract nodes and coordinates

    #extract nodes from base_data
    N_NODES = base_data.N_NODES

    #import norwegian city coordinates
    NO_coordinates = pd.read_csv("Data/NO_cities_coordinates.csv")
    #extract latitudes and longitudes
    lats = [0.0] * len(N_NODES)
    lons = [0.0] * len(N_NODES)
    for index, row in NO_coordinates.iterrows():
        if row["city"] in N_NODES:
            n_ind = N_NODES.index(row["city"]) #index of this city in list N_NODES
            lats[n_ind] = row["lat"]
            lons[n_ind] = row["lng"]

    #Manually define foreign city coordinates (HARDCODED)
    foreign_cities = pd.DataFrame()
    foreign_cities["city"] = ["Sør-Sverige", "Nord-Sverige", "Kontinentalsokkelen", "Europa", "Verden"] 
    foreign_cities["lat"] = [59.33, 63.82, 60, 56.2, 56.5] 
    foreign_cities["lon"] = [18.06, 20.26, 2,  9, 3]
    #add to vectors lats and lons
    for index, row in foreign_cities.iterrows():
        if row["city"] in N_NODES:
            n_ind = N_NODES.index(row["city"]) #index of this city in list N_NODES
            lats[n_ind] = row["lat"]
            lons[n_ind] = row["lon"]
    #add colors (for checking and perhaps plotting)
    node_colors = ["black"]*len(N_NODES)     


    ####################
    # b. Build a map

    #draw the basic map including country borders
    map = Basemap(llcrnrlon=1, urcrnrlon=29, llcrnrlat=55, urcrnrlat=70, resolution='i', projection='aeqd', lat_0=63.4, lon_0=10.4) # Azimuthal Equidistant Projection
    # map = Basemap(llcrnrlon=1, urcrnrlon=29, llcrnrlat=55, urcrnrlat=70, resolution='i', projection='tmerc', lat_0=0, lon_0=0) # mercator projection
    map.drawmapboundary(fill_color='aqua')
    map.fillcontinents(color='lightgrey', lake_color='aqua')
    map.drawcoastlines(linewidth=0.2)
    map.drawcountries(linewidth=0.2)

    #draw nodes on the map
    node_x, node_y = map(lons, lats)
    map.scatter(node_x, node_y, color=node_colors, zorder=100)


    ##########################
    # c. Plot flow in the map

    #arrow settings
    tail_width_base = 20
    min_tail_width = 0
    head_with = 0.01
    head_length = 0.01
    benchmark_level = 1000 # we compare investment levels with this to determine line width


    # compute maximum and total flows over all edges (for scaling purposes)
    #   note: use absolute value to deal with flow_diff if we use that plotting option
    max_infra = max(df_infra["infra"]) #TODO: UPDATE variable name
    total_infra = sum(df_infra["infra"]) #TODO: UPDATE variable name

    #iterate over egdes
    for index, row in df_infra.iterrows():
        #store current origin and destinations + indices
        cur_orig = row["orig"]
        cur_dest = row["dest"]
        cur_orig_index = N_NODES.index(cur_orig)
        cur_dest_index = N_NODES.index(cur_dest)
        #get current investment and related information
        cur_infra = row["infra"]
        #create new arc
        if cur_infra > 0.0000001*total_infra: #only plot an arc if we have significant flow (at least ...% of total flow for the relevant mode)
            new_arc = patches.FancyArrowPatch(
                (node_x[cur_orig_index], node_y[cur_orig_index]), 
                (node_x[cur_dest_index], node_y[cur_dest_index]), 
                connectionstyle=f"arc3,rad={0}",
                #linewidth = max(tail_width_base * cur_infra/max_infra, min_tail_width),
                linewidth = max(tail_width_base * cur_infra/benchmark_level, min_tail_width),
                linestyle="-",
                color="magenta",
                zorder = 1
                )    
            #add the arc to the plot
            plt.gca().add_patch(new_arc)
    
    ###############################
    # d. Show and save the figure

    #set size
    scale = 1.3
    plot_width = 5 #in inches
    plot_height = scale * plot_width
    plt.gcf().set_size_inches(plot_width, plot_height, forward=True) #TODO: FIND THE RIGH TSIZE
    #save figure
    if save_fig:
        plt.savefig(filename)
    #show figure
    if show_fig:
        plt.show()

# function that processes data and makes a charging infra plot in one go
def process_and_plot_charging_infra(output, base_data, sel_time_period, sel_scenario="BBB", cumulative=False, show_fig=True, save_fig=False):
    # process data 
    print("Processing charging infrasructure investments...")
    df_infra = process_charging_infra(output.y_charging, sel_time_period, sel_scenario, cumulative)

    # make plot
    print("Making plot...")
    filename = f"Plots/charging_infra_plot_{sel_time_period}_{sel_scenario}_{cumulative}.png"
    plot_charging_infra_on_map(df_infra, base_data, show_fig, save_fig, filename)


# b. Harbors

# function that processes the charging infrastructure data, puts it in a data frame
def process_terminal_infra(nu_node, mode, terminal_type, sel_time_period, sel_scenario="BBB", cumulative=False):
    
    # initialize lists that will store output
    nodes = base_data.N_NODES   # all nodes
    infra = [0.0] * len(nodes)  # investment levels in terminal capacity

    node_dict = {}
    for i in range(len(nodes)):
        node_dict[nodes[i]] = i

    # process data
    for index, row in nu_node.iterrows():
        if row["mode"] == mode: # check correct mode
            if row["terminal_type"] == terminal_type or terminal_type == "all": #check terminal type
                if row["scenario"] == sel_scenario: # check scenario
                    if (cumulative == True and row["time_period"] <= sel_time_period) or (cumulative == False and row["time_period"] == sel_time_period):    
                        cur_node_index = node_dict[row["from"]]
                        #store corresponding flows in lists
                        infra[cur_node_index] += row["weight"]
    
    #store aggregate flows in a dataframe
    df_infra = pd.DataFrame()
    df_infra["node"] = nodes
    df_infra["infra"] = infra


    return df_infra

# function that plots flow on the map
def plot_terminal_infra_on_map(df_infra, base_data, show_fig=True, save_fig=False, filename="test.png"):    
    """
    Create a plot on the map of Norway with infrastructure investments

    INPUT
    df_infra:       dataframe with investment in terminal infrastructure
    base_data:      base model data (only used to extract N_NODES)
    show_fig:       indicate whether to show the figure
    save_fig:       indicate whether to save the figure (filename is determined automatically)
    
    OUTPUT
    figure that is shown and/or saved to disk if requested
    """

    ####################################
    # a. Extract nodes and coordinates

    #extract nodes from base_data
    N_NODES = base_data.N_NODES

    #import norwegian city coordinates
    NO_coordinates = pd.read_csv("Data/NO_cities_coordinates.csv")
    #extract latitudes and longitudes
    lats = [0.0] * len(N_NODES)
    lons = [0.0] * len(N_NODES)
    for index, row in NO_coordinates.iterrows():
        if row["city"] in N_NODES:
            n_ind = N_NODES.index(row["city"]) #index of this city in list N_NODES
            lats[n_ind] = row["lat"]
            lons[n_ind] = row["lng"]

    #Manually define foreign city coordinates (HARDCODED)
    foreign_cities = pd.DataFrame()
    foreign_cities["city"] = ["Sør-Sverige", "Nord-Sverige", "Kontinentalsokkelen", "Europa", "Verden"] 
    foreign_cities["lat"] = [59.33, 63.82, 60, 56.2, 56.5] 
    foreign_cities["lon"] = [18.06, 20.26, 2,  9, 3]
    #add to vectors lats and lons
    for index, row in foreign_cities.iterrows():
        if row["city"] in N_NODES:
            n_ind = N_NODES.index(row["city"]) #index of this city in list N_NODES
            lats[n_ind] = row["lat"]
            lons[n_ind] = row["lon"]
    #add colors (for checking and perhaps plotting)
    node_colors = ["black"]*len(N_NODES)     


    ####################
    # b. Build a map

    #draw the basic map including country borders
    map = Basemap(llcrnrlon=1, urcrnrlon=29, llcrnrlat=55, urcrnrlat=70, resolution='i', projection='aeqd', lat_0=63.4, lon_0=10.4) # Azimuthal Equidistant Projection
    # map = Basemap(llcrnrlon=1, urcrnrlon=29, llcrnrlat=55, urcrnrlat=70, resolution='i', projection='tmerc', lat_0=0, lon_0=0) # mercator projection
    map.drawmapboundary(fill_color='aqua')
    map.fillcontinents(color='lightgrey', lake_color='aqua')
    map.drawcoastlines(linewidth=0.2)
    map.drawcountries(linewidth=0.2)



    ##########################
    # c. Plot nodes on the map

    # define color for each investment level
    color_dict = {0.0: "black", 1.0: "green", 2.0:"blue", 3.0:"red"}

    # update colors based on data
    for i in range(len(N_NODES)):
        node_colors[i] = color_dict[df_infra.infra[i]]

    #plot nodes on map
    node_x, node_y = map(lons, lats)
    map.scatter(node_x, node_y, color=node_colors, zorder=100)
    
    ###############################
    # d. Show and save the figure

    #set size
    scale = 1.3
    plot_width = 5 #in inches
    plot_height = scale * plot_width
    plt.gcf().set_size_inches(plot_width, plot_height, forward=True) #TODO: FIND THE RIGH TSIZE
    #save figure
    if save_fig:
        plt.savefig(filename)
    #show figure
    if show_fig:
        plt.show()

# function that processes data and makes a terminal infra plot in one go
def process_and_plot_terminal_infra(output, base_data, mode, terminal_type, sel_time_period, sel_scenario="BBB", cumulative=False, show_fig=True, save_fig=False):
    # process data 
    print("Processing terminal infrasructure investments...")
    df_infra = process_terminal_infra(output.nu_node, mode, terminal_type, sel_time_period, sel_scenario, cumulative)

    # make plot
    print("Making plot...")
    filename = f"Plots/terminal_infra_plot_{mode}_{terminal_type}_{sel_time_period}_{sel_scenario}_{cumulative}.png"
    plot_terminal_infra_on_map(df_infra, base_data, show_fig, save_fig, filename)



#####################################################################################

# RUN ANALYSIS

# Read model output
analyses_type = 'SP' # EV , EEV, 'SP
with open(r'Data\output_data_'+analyses_type, 'rb') as output_file:
    output = pickle.load(output_file)
with open(r'Data\base_data', 'rb') as data_file:
    base_data = pickle.load(data_file)

# plot charging infra for multiple years
for t in [2022, 2026, 2030, 2040, 2050]:
    process_and_plot_charging_infra(output, base_data, t, cumulative=True, show_fig=True, save_fig=False)

# plot charging infra for one year
process_and_plot_charging_infra(output, base_data, 2040, cumulative=False, show_fig=True, save_fig=False)



# plot terminal infra investment for all years
for t in [2022, 2026, 2030, 2040, 2050]:
    process_and_plot_terminal_infra(output, base_data, "Rail", "all", t, sel_scenario="BBB", cumulative=True, show_fig=True, save_fig=False)

# plot terminal infra investment for one year
process_and_plot_terminal_infra(output, base_data, "Rail", "all", 2050, sel_scenario="BBB", cumulative=True, show_fig=True, save_fig=False)


output.nu_node.head()
