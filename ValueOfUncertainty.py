from Data.settings import *

import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from matplotlib.transforms import Affine2D
import numpy as np
import pandas as pd

import pickle
import json

#---------------------------------------------------------#
#       User Settings
#---------------------------------------------------------#

scenarios = "9Scen"   # '4Scen', '9Scen','AllScen'
analyses = ["SP","EEV"]

#---------------------------------------------------------#
#       Output data
#---------------------------------------------------------#

output={analysis:None for analysis in analyses}
for analysis in analyses:
    with open(r'Data\\output\\'+analysis+'_'+scenarios+'.pickle', 'rb') as output_file:
        output[analysis] = pickle.load(output_file)

with open(r'Data\base_data\\'+scenarios+'.pickle', 'rb') as data_file:
    base_data = pickle.load(data_file)

if True:


    #---------------------------------------------------------#
    #       COSTS
    #---------------------------------------------------------#

        
    #create the all_cost_table
    def cost_and_investment_table(base_data,output):
        
        cost_vars = ["TranspOpexCost","TranspOpexCostB","TranspCO2Cost","TranspCO2CostB","TransfCost","EdgeCost","NodeCost","UpgCost", "ChargeCost"]
        legend_names = {"TranspOpexCost":"OPEX",
            "TranspOpexCostB":"OPEX_Empty",
            "TranspCO2Cost":"Carbon",
            "TranspCO2CostB":"Carbon_Empty",
            "TransfCost":"Transfer",
            "EdgeCost":"Edge",
            "NodeCost":"Node",
            "UpgCost":"Upg", 
            "ChargeCost":"Charge",
            }
        output.cost_var_colours =  {"OPEX":"royalblue",
            "OPEX_Empty":"cornflowerblue",
            "Carbon":"dimgrey",
            "Carbon_Empty":"silver",
            "Transfer":"brown",
            "Edge":"indianred",
            "Node":"darkred",
            "Upg":"teal", 
            "Charge":"forestgreen",
            }
        
        output.all_costs = {legend_names[var]:output.costs[var] for var in cost_vars}
        
        
        #get the right measure:
        for var in cost_vars:
            var2 = legend_names[var]
            for key, value in output.all_costs[var2].items():
                output.all_costs[legend_names[var]][key] = round(value/10**9*SCALING_FACTOR_MONETARY,3) # in GNOK

        output.all_costs_table = pd.DataFrame.from_dict(output.all_costs, orient='index')
        
        for t in base_data.T_TIME_PERIODS: 
            #t = base_data.T_TIME_PERIODS[0]
            level_values =  output.all_costs_table.columns.get_level_values(1) #move into loop?
            columns = ((output.all_costs_table.columns.get_level_values(0)==t) & 
                        ([level_values[i] in base_data.S_SCENARIOS for i in range(len(level_values))]))
            mean = output.all_costs_table.iloc[:,columns].mean(axis=1)
            std = output.all_costs_table.iloc[:,columns ].std(axis=1)
            output.all_costs_table[(t,'mean')] = mean
            output.all_costs_table[(t,'std')] = std
        output.all_costs_table = output.all_costs_table.fillna(0) #in case of a single scenario we get NA's

        #only select mean and std data (go away from scenarios)
        columns = ((output.all_costs_table.columns.get_level_values(1)=='mean') | (output.all_costs_table.columns.get_level_values(1)=='std'))
        output.all_costs_table = output.all_costs_table.iloc[:,columns ].sort_index(axis=1,level=0)
        
        discount_factors = pd.Series([round(base_data.D_DISCOUNT_RATE**n,3) for n in [t - base_data.T_TIME_PERIODS[0]  for t in base_data.T_TIME_PERIODS for dd in range(2)]],index = output.all_costs_table.columns).to_frame().T #index =
        discount_factors = discount_factors.rename({0:'discount_factor'})

        output.all_costs_table = pd.concat([output.all_costs_table, discount_factors],axis=0, ignore_index=False)

        return output   

    def plot_costs(output,which_costs,ylabel,filename):

        #which_costs = opex_variables
        #ylabel = 'Annual costs (GNOK)'
        
        #indices = [i for i in output.all_costs_table.index if i not in ['discount_factor']]
        all_costs_table2 = output.all_costs_table.loc[which_costs]

        mean_data = all_costs_table2.iloc[:,all_costs_table2.columns.get_level_values(1)=='mean']
        mean_data = mean_data.droplevel(1, axis=1)
        std_data = all_costs_table2.iloc[:,all_costs_table2.columns.get_level_values(1)=='std']
        std_data = std_data.droplevel(1, axis=1)
        yerrors = std_data.to_numpy()
        #fig, ax = plt.subplots()
        ax = mean_data.transpose().plot(kind='bar', yerr=yerrors, alpha=0.5, error_kw=dict(ecolor='k'), 
            stacked = True,
            xlabel = 'time periods',
            ylabel = ylabel,
            #title = title,
            color = output.cost_var_colours
            )  
        #print(ax.get_xticklabels())
        # NOT WORKING WITH CATEGORICAL AXIS
        #ax.vlines(60,0,50)
        ax.axvline(x = 1.5, color = 'black',ls='--') 
        ax.text(-0.2, 0.95*ax.get_ylim()[1], "First stage", fontdict=None)
        ax.text(1.8, 0.95*ax.get_ylim()[1], "Second stage", fontdict=None)

        if filename=='investment':
            ax.legend(loc='upper right')  #upper left
        else:
            ax.legend(loc='lower right')  #upper left

        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        #https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.plot.html
        #ax.spines[['right', 'top']].set_visible(False)   #https://stackoverflow.com/questions/14908576/how-to-remove-frame-from-matplotlib-pyplot-figure-vs-matplotlib-figure-frame
        #fig = ax.get_figure()
        ax.get_figure().savefig(r"Data\\Figures\\"+run_identifier+"_costs_"+filename+".png",dpi=300,bbox_inches='tight')

    def calculate_emissions(output,base_data,domestic=True):
        output.total_yearly_emissions = {(t,s):0 for t in base_data.T_TIME_PERIODS for s in base_data.S_SCENARIOS} # in MTonnes CO2 equivalents

        x_flow = output.x_flow 
        b_flow = output.b_flow
        
        if domestic:
            x_flow = x_flow[(x_flow['from'].isin(base_data.N_NODES_NORWAY))&(x_flow['to'].isin(base_data.N_NODES_NORWAY))]
            b_flow = b_flow[(b_flow['from'].isin(base_data.N_NODES_NORWAY))&(b_flow['to'].isin(base_data.N_NODES_NORWAY))]

        for index,row in x_flow.iterrows():
            (i,j,m,r,f,p,t,s,value) = (row['from'],row['to'],row['mode'],row['route'],row['fuel'],row['product'],row['time_period'],row['scenario'],row['weight']) 
            output.total_yearly_emissions[(t,s)] += ((base_data.E_EMISSIONS[i,j,m,r,f,p,t]*SCALING_FACTOR_EMISSIONS/SCALING_FACTOR_WEIGHT)*(value*SCALING_FACTOR_WEIGHT))/(10**12) #   gCO2 / tonnes*km     *   tonnes/km     ->  in MTonnes CO2 equivalents
        for index,row in b_flow.iterrows():
            (i,j,m,r,f,v,t,s,value) = (row['from'],row['to'],row['mode'],row['route'],row['fuel'],row['vehicle_type'],row['time_period'],row['scenario'],row['weight'])
            output.total_yearly_emissions[(t,s)] += ((base_data.E_EMISSIONS[i,j,m,r,f, base_data.cheapest_product_per_vehicle[(m,f,t,v)], t]*SCALING_FACTOR_EMISSIONS/SCALING_FACTOR_WEIGHT)*(value*SCALING_FACTOR_WEIGHT))/(10**6*10**6) # in MTonnes CO2 equivalents

        output.total_emissions = pd.DataFrame.from_dict({'time_period': [t for (t,s) in output.total_yearly_emissions.keys()],	
                                                            'weight': list(output.total_yearly_emissions.values())	,
                                                            'scenario': [s for (t,s) in output.total_yearly_emissions.keys()]})
            
        # https://stackoverflow.com/questions/23144784/plotting-error-bars-on-grouped-bars-in-pandas
        output.emission_stats = output.total_emissions.groupby('time_period').agg(
            AvgEmission=('weight', np.mean),
            Std=('weight', np.std))
        output.emission_stats = output.emission_stats.fillna(0) #in case of a single scenario we get NA's

        #output.emission_stats['AvgEmission_perc'] = output.emission_stats['AvgEmission']/output.emission_stats.at[2020,'AvgEmission']*100 #OLD: 2020
        output.emission_stats['AvgEmission_perc'] = output.emission_stats['AvgEmission']/output.total_yearly_emissions[(base_data.T_TIME_PERIODS[0],base_data.S_SCENARIOS[0])]*100  #NEW: 2022
        #output.emission_stats['Std_perc'] = output.emission_stats['Std']/output.emission_stats.at[2020,'AvgEmission']*100 #OLD: 2020
        output.emission_stats['Std_perc'] = output.emission_stats['Std']/output.emission_stats.at[base_data.T_TIME_PERIODS[0],'AvgEmission']*100  #NEW: 2022
        #goals = list(base_data.EMISSION_CAP_RELATIVE.values())
        #output.emission_stats['Goal'] = goals
        #output.emission_stats['StdGoals'] = [0 for g in goals]       

        return output

    
    #---------------------------------------------------------#
    #       COST AND EMISSION TRADE-OFF
    #---------------------------------------------------------#
    print('--------------------------')
    for analysis in analyses:
        print('--------')
        print(analysis)
        print('--------')
        output = output[analysis]
        output = calculate_emissions(output,base_data,domestic=False)
        output.emission_stats = output.total_emissions.groupby('time_period').agg(
                AvgEmission=('weight', np.mean),
                Std=('weight', np.std))
        output.emission_stats = output.emission_stats.fillna(0) #in case of a single scenario we get NA's
        print('Total (average) emissions (in Million TonnesCo2):')
        print(round(sum(output.emission_stats['AvgEmission'])*SCALING_FACTOR_EMISSIONS/10**9,2)) #this becomes Million TonnesCO2         

        print('objective function value: ')
        print(round(output.ob_function_value*SCALING_FACTOR_MONETARY/10**9,2))
        
    #2000NOK per Tonne CO2 is this in line? Do the comparison for
