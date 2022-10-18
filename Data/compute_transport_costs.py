#PRELIMINARIES
#imports
import pandas as pd
import os

#set working directory
os.chdir('//home.ansatt.ntnu.no/egbertrv/Documents/GitHub/AIM_Norwegian_Freight_Model') #uncomment this for stand-alone testing of this fille

#--------------
#SETS AND LISTS
#--------------

#SETS

#Note: I ordered the sets in the same way as is implied by the excel file Costs.xlsx
#So we obtain exactly the same output (in the same order) as in that file. 
#I did this to avoid any errors due to potential hardcoding
#The order of sets may not align with the order used in the other python files.

T_TIME_PERIODS = [2020, 2025, 2030, 2040, 2050]

M_MODES = ["Road", "Sea", "Rail"]

M_MODES_DATA = ["Road", "Sea"] #modes with cost data from Jonas

M_MODES_RAIL_DATA = ["Rail"] #modes with no data from Jonas, but other data

F_FUEL = ["Diesel", "Ammonia", "Hydrogen", "Battery electric", "Electric train (CL)", "LNG", "MGO",
               'Biogas', 'Biodiesel', 'Biodiesel (HVO)', 'Battery train', "HFO"]

FM_FUEL = {"Road": ["Diesel",  "Battery electric", "Hydrogen", 'Biodiesel', 'Biogas'],
                "Sea": [ "HFO", "MGO", "LNG", "Hydrogen", "Ammonia", 'Biodiesel (HVO)', 'Biogas',],
                "Rail": ["Diesel", "Electric train (CL)", "Hybrid", "Battery train", "Hydrogen", 'Biodiesel']} 

#fuels per mode in order of transport cost dependence (HARDCODED)
FM_FUEL_ORDERED = {"Road": ["Diesel", "Hydrogen", "Battery electric", 'Biodiesel', 'Biogas'],
                "Sea": ["Hydrogen", "Ammonia", "HFO", "MGO", "LNG", 'Biodiesel (HVO)', 'Biogas'],
                "Rail": ["Electric train (CL)", "Diesel", "Hybrid", "Battery train", "Hydrogen", 'Biodiesel']} 

#fuels per mode for which we have explicit cost data from Jonas
FM_FUEL_DATA = {"Road": ["Diesel", "Hydrogen"], #, 'Biodiesel'],
                "Sea": ["HFO", "Hydrogen", "Ammonia"], #, 'Biodiesel (HVO)'], 
                "Rail": []} #mode->fuels with cost data

#fuels per mode for which we have explicit rail cost data from other sources
FM_FUEL_RAIL_DATA = {"Road": [],
                "Sea": [],
                "Rail": ["Electric train (CL)"]} 

P_PRODUCTS = ['Dry bulk', 'General cargo', 'Fish', 'Other thermo', 'Industrial goods', 'Timber', 'Wet bulk']

V_VEHICLES = ["Dry bulk truck", "Articulated semi, containers", "Termo truck", "Articulated semi closed", "Timber truck with hanger", "Tank truck distance", 
              "System trains (dry bulk)", "Combi trains", "Timber trains", "System trains (wet bulk)",
              "Dry bulk 9000 dwt", "Container lo/lo 8500 dwt", "Break bulk Lo/lo, 2500dwt", "Tanker vessel 17000 dwt"]

MV_VEHICLES = {"Road": ["Dry bulk truck", "Articulated semi, containers", "Termo truck", "Articulated semi closed", "Timber truck with hanger", "Tank truck distance"],
               "Rail": ["System trains (dry bulk)", "Combi trains", "Timber trains", "System trains (wet bulk)"],
               "Sea": ["Dry bulk 9000 dwt", "Container lo/lo 8500 dwt", "Break bulk Lo/lo, 2500dwt", "Tanker vessel 17000 dwt"]}


#LISTS

#list of mode-fuels (in standard order)
MF_LIST = []
for m in M_MODES:
    for f in FM_FUEL[m]:
        MF_LIST.append((m,f))

#list of mode-fuels (in order of transport cost dependency)
MF_LIST_ORDERED = []
for m in M_MODES:
    for f in FM_FUEL_ORDERED[m]:
        MF_LIST_ORDERED.append((m,f))

#list of mode-fuels for which we have explicit cost data from Jonas
MF_LIST_DATA = []
for m in M_MODES_DATA:
    for f in FM_FUEL_DATA[m]:
        MF_LIST_DATA.append((m,f))

#list of mode-fuels for which we have explicit cost data from other sources (for rail)
MF_LIST_RAIL_DATA = []
for m in M_MODES_RAIL_DATA:
    for f in FM_FUEL_RAIL_DATA[m]:
        MF_LIST_RAIL_DATA.append((m,f))




#---------------
#TRANSPORT COSTS
#---------------


#BASE COSTS

#load explicit transport cost data (excluding fuel station investment cost) from Jonas
df_base_costs = pd.read_excel(r'Data/transport_costs_emissions_source.xlsx', sheet_name='base_costs', skiprows=14) #base costs for Road, Sea, based on Jonas' data
df_rail_costs = pd.read_excel(r'Data/transport_costs_emissions_source.xlsx', sheet_name='base_costs', skiprows=26) #base costs for Rail, based on other data

#load exchange rate EUR to NOK
df_eur_to_nok = pd.read_excel(r'Data/transport_costs_emissions_source.xlsx', sheet_name='EUR_TO_NOK')
EUR_TO_NOK = df_eur_to_nok['EUR to NOK'][0]


#base_costs: costs for mode-fuels for which we have explicit cost data from Jonas
#indices: [mf][ti]
base_costs = [[0 for i in range(len(T_TIME_PERIODS))] for j in range(len(MF_LIST_DATA))] 
for index, row in df_base_costs.iterrows():
    for mf in range(len(MF_LIST_DATA)):
        if MF_LIST_DATA[mf] == (row['Mode'], row['Fuel']):
            for ti in range(len(T_TIME_PERIODS)): #ti: time index
                base_costs[mf][ti] = row[T_TIME_PERIODS[ti]] * EUR_TO_NOK

#rail costs: costs for mode-fuels for which we have explicit cost data from other sources (rail-electric)
#indices: [mf][vi] (mode-fuel, vehicle)
rail_costs = [[0 for i in range(sum(len(MV_VEHICLES[m]) for m in M_MODES_RAIL_DATA))] for j in range(len(MF_LIST_RAIL_DATA))] 
for index, row in df_rail_costs.iterrows():
    for mf in range(len(MF_LIST_RAIL_DATA)):
        if MF_LIST_RAIL_DATA[mf] == (row['Mode'], row['Fuel']):
            m = row['Mode']
            for vi in range(len(MV_VEHICLES[m])):
                if MV_VEHICLES[m][vi] == row['Vehicle type']:
                    rail_costs[mf][vi] = row['Cost/Tkm'] * EUR_TO_NOK



#RELATIVE COST FACTORS

#load relative cost factor data
df_cost_factors = pd.read_excel(r'Data/transport_costs_emissions_source.xlsx', sheet_name='cost_factors', skiprows=2)

#extract relative fuels and relative cost factors
f_rel = [("") for mf in range(len(MF_LIST))]
cost_factor = [[0 for i in range(len(T_TIME_PERIODS))] for j in range(len(MF_LIST))]
for index, row in df_cost_factors.iterrows():
    for mf in range(len(MF_LIST)):
        if MF_LIST[mf] == (row['Mode'], row['Fuel']):
            m = MF_LIST[mf][0]
            f = MF_LIST[mf][1]
            f_rel[mf] = row["Relative to"]
            for ti in range(len(T_TIME_PERIODS)):
                cost_factor[mf][ti] = row[T_TIME_PERIODS[ti]]
            


#TRANSPORT COSTS PER KM (from Jonas)

#transport costs per km
costs_per_km = [[0 for i in range(len(T_TIME_PERIODS))] for j in range(len(MF_LIST))] #costs per km in NOK

#first compute costs per km for mode-fuels with explicit cost data
for mf in range(len(MF_LIST)):
    m = MF_LIST[mf][0]
    f = MF_LIST[mf][1]
    if (m in M_MODES_DATA and f in FM_FUEL_DATA[m]):
        #find mf in base_costs matrix
        mf_base = -1
        for mf2 in range(len(MF_LIST_DATA)):
            if MF_LIST_DATA[mf2] == MF_LIST[mf]:
                mf_base = mf2
                print("mf_base = ", mf_base)
        for ti in range(len(T_TIME_PERIODS)):               
            costs_per_km[mf][ti] = base_costs[mf_base][ti]
        
        
    
#next compute costs per km for mode-fuels with only relative costs w.r.t. other mode-fuel
for mf_ord in range(len(MF_LIST_ORDERED)):
    mode = MF_LIST_ORDERED[mf_ord][0]
    fuel = MF_LIST_ORDERED[mf_ord][1]
    #find corresponding "normal" mf
    mf = -1
    for mf1 in range(len(MF_LIST)):
        if MF_LIST[mf1] == MF_LIST_ORDERED[mf_ord]:
            mf = mf1
    if mode in M_MODES_DATA:
        if MF_LIST[mf] not in MF_LIST_DATA:
            #find index of relative mf
            mf_rel = -1
            for mf2 in range(len(MF_LIST)):
                if (mode == MF_LIST[mf2][0] and f_rel[mf] == MF_LIST[mf2][1]):
                    mf_rel = mf2
            for ti in range(len(T_TIME_PERIODS)):               
                costs_per_km[mf][ti] = costs_per_km[mf_rel][ti] * cost_factor[mf][ti]    #ti: time index   
    


#VEHICLE INFORMATION

#load product-vehicle connections   
df_prod_to_vehicle = pd.read_excel(r'Data/transport_costs_emissions_source.xlsx', sheet_name='prod_to_vehicle')

#map mode-product to vehicles
mp_to_vehicle = [["" for p in range(len(P_PRODUCTS))] for m in range(len(M_MODES))] #(m,p) indices to vehicle name

for index, row in df_prod_to_vehicle.iterrows():
    for m in range(len(M_MODES)):
        for p in range(len(P_PRODUCTS)):
            if (row['Mode'] == M_MODES[m] and row['Product group'] == P_PRODUCTS[p]):
                mp_to_vehicle[m][p] = row['Vehicle type']

#load vehicle capacities                
df_vehicle_capacity = pd.read_excel(r'Data/transport_costs_emissions_source.xlsx', sheet_name='vehicle_cap')

#vehicle capacities
veh_cap = [0.0 for v in range(len(V_VEHICLES))]

for index, row in df_vehicle_capacity.iterrows():
    for v in range(len(V_VEHICLES)):    
        if row['Vehicle'] == V_VEHICLES[v]:
            veh_cap[v] = row['Capacity (tonnes)']


#COST PER TKM (note: here the code is messy for rail)

#cost per Tkm for all mode-fuel, product, time combinations (in NOK)
costs = [[[0 for ti in range(len(T_TIME_PERIODS))] for pi in range(len(P_PRODUCTS))] for mf in range(len(MF_LIST))]

for mf_ord in range(len(MF_LIST_ORDERED)): #make sure we pass through the mfs in the right order
    #find mf (non-ordered index)
    mf = -1
    for mf1 in range(len(MF_LIST)):
        if MF_LIST[mf1] == MF_LIST_ORDERED[mf_ord]:
            mf = mf1
    #print(mf)
    mf_rail = -1
    for mf_r in range(len(MF_LIST_RAIL_DATA)):
        if MF_LIST[mf_r] == MF_LIST_ORDERED[mf_ord]:
            mf_rail = mf_r
    mode = MF_LIST[mf][0]
    fuel = MF_LIST[mf][1]
    for mi in range(len(M_MODES)):
        if M_MODES[mi] == mode:
            m = mi
    #print("m=",m)
    if mode in M_MODES_DATA:
        for pi in range(len(P_PRODUCTS)):
            vehicle = mp_to_vehicle[m][pi]
            veh_index = -1
            for vi in range(len(V_VEHICLES)):
                if V_VEHICLES[vi] == vehicle:
                    veh_index = vi
            
            for ti in range(len(T_TIME_PERIODS)):               
                costs[mf][pi][ti] = costs_per_km[mf][ti] / veh_cap[veh_index]
    elif mode in M_MODES_RAIL_DATA:
        for pi in range(len(P_PRODUCTS)):
            vehicle = mp_to_vehicle[m][pi]
            veh_index_rail = -1
            for vi_r in range(len(MV_VEHICLES["Rail"])): #hardcoded "Rail"
                if MV_VEHICLES["Rail"][vi_r] == vehicle:
                    veh_index_rail = vi_r
            if fuel in FM_FUEL_RAIL_DATA[mode]: #costs known explicitly
                for ti in range(len(T_TIME_PERIODS)): 
                    costs[mf][pi][ti] = rail_costs[mf_rail][veh_index_rail] * cost_factor[mf][ti]    
            else: #(costs not known explicitly, only relatively)
                #find index of relative mf
                mf_rel = -1
                for mf2 in range(len(MF_LIST)):
                    if (mode == MF_LIST[mf2][0] and f_rel[mf] == MF_LIST[mf2][1]):
                        mf_rel = mf2
                for ti in range(len(T_TIME_PERIODS)): 
                    #compute costs
                    costs[mf][pi][ti] = costs[mf_rel][pi][ti] * cost_factor[mf][ti]
            


#---------
#EMISSIONS
#---------


#TODO: COMPUTE EMISSIONS


#------
#OUTPUT
#------

df_out = pd.DataFrame(columns=["Mode", "Product group", "Vehicle type", "Fuel", "Year", "Cost (NOK/Tkm)"])

for t in range(len(T_TIME_PERIODS)):
    for m in range(len(M_MODES)):
        for p in range(len(P_PRODUCTS)):
            for f in range(len(FM_FUEL[M_MODES[m]])):
                #find mf
                mf = -1
                for mf1 in range(len(MF_LIST)):
                    if MF_LIST[mf1][0] == M_MODES[m] and MF_LIST[mf1][1] == FM_FUEL[M_MODES[m]][f]:
                        mf = mf1
                #define entry
                entry = pd.DataFrame.from_dict({
                    "Mode": [M_MODES[m]],
                    "Product group": [P_PRODUCTS[p]],
                    "Vehicle type": [mp_to_vehicle[m][p]],
                    "Fuel": [FM_FUEL[M_MODES[m]][f]],
                    "Year": [T_TIME_PERIODS[t]],
                    "Cost (NOK/Tkm)": [costs[mf][p][t]]
                    })
                #add row to dataframe
                df_out = pd.concat([df_out, entry], ignore_index=True)
                
file_name = "Data/transport_costs_processed.xlsx"

df_out.to_excel(file_name)




#TODO: READ DATA IN PYTHON MODEL FROM NEW FILE

















