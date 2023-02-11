# -*- coding: utf-8 -*-
"""
Created on Fri Jul 29 10:24:04 2022

@author: steffejb
"""

#import mpisppy.utils.sputils as sputils
from TranspModelClass import TranspModel
#import mpisppy.scenario_tree as scenario_tree
import copy
from Data.settings import *
import pickle

def scenario_creator(scenario_name, **kwargs):
    
    base_data = kwargs.get('base_data')
    fix_first_time_period = kwargs.get('fix_first_time_period')
    x_flow_base_period_init = kwargs.get('x_flow_base_period_init')
    risk_info = kwargs.get('risk_info')

    fix_first_stage = kwargs.get('fix_first_stage')
    output_EV = kwargs.get('first_stage_variables')

    NoBalancingTrips = kwargs.get('NoBalancingTrips')
    last_time_period = kwargs.get('last_time_period')

    base_data.update_scenario_dependent_parameters(scenario_name)
    
    #deepcopy is slower than repetitively constructing the models.
    #model_instance = TranspModel(data=base_data) #OLD
    model_instance = TranspModel(data=base_data, risk_info=risk_info)
    model_instance.NoBalancingTrips = NoBalancingTrips
    model_instance.last_time_period = last_time_period
    model_instance.construct_model()
    if fix_first_time_period: 
        model_instance.fix_variables_first_time_period(x_flow_base_period_init)
    if fix_first_stage:
        model_instance.fix_variables_first_stage(output_EV)
    model = model_instance.model
    
    first_stage = base_data.T_TIME_FIRST_STAGE 
    first_stage_yearly = base_data.T_YEARLY_TIME_FIRST_STAGE
    #OLD: RISK-NEUTRAL

    """
    sputils.attach_root_node(model, sum(model.StageCosts[t] for t in first_stage),
                                         [model.x_flow[:,:,:,:,:,:,t] for t in first_stage]+
                                         [model.b_flow[:,:,:,:,:,:,t] for t in first_stage]+ 
                                         [model.h_path[:,:,t] for t in first_stage]+
                                         [model.h_path_balancing[:,:,t] for t in first_stage]+
                                         [model.q_transp_amount[:,:,t] for t in first_stage]+
                                         [model.y_charge[:, :, :, :, :, t] for t in first_stage]+
                                         [model.epsilon_edge[:,:,:,:,t] for t in first_stage]+
                                         [model.upsilon_upg[:,:,:,:,:,t] for t in first_stage]+ 
                                         [model.nu_node[:,:,:,t] for t in first_stage]+
                                         [model.z_emission[t] for t in first_stage] + 
                                         [model.total_emissions[t] for t in first_stage] 
                                         )
    """                                     
    #new: risk-averse
    sputils.attach_root_node(model, model.FirstStageCosts + risk_info.cvar_coeff * model.CvarAux,   #risk-averse first-stage objective part: c*x + \lambda * u
                                         [model.x_flow[:,:,:,:,:,:,t] for t in first_stage]+
                                         [model.b_flow[:,:,:,:,:,:,t] for t in first_stage]+ 
                                         [model.h_path[:,:,t] for t in first_stage]+
                                         [model.h_path_balancing[:,:,t] for t in first_stage]+
                                         [model.q_transp_amount[:,:,t] for t in first_stage]+
                                         [model.q_mode_total_transp_amount[:,t] for t in first_stage]+
                                         [model.q_aux_transp_amount[:,:,t_y] for t_y in first_stage_yearly] +
                                         [model.y_charge[:, :, :, :, :, t] for t in first_stage]+
                                         [model.epsilon_edge[:,:,:,:,t] for t in first_stage]+
                                         [model.upsilon_upg[:,:,:,:,:,t] for t in first_stage]+ 
                                         [model.nu_node[:,:,:,t] for t in first_stage]+
                                         [model.z_emission[t] for t in first_stage] + 
                                         [model.total_emissions[t] for t in first_stage] +
                                         #[model.StageCosts[t] for t in first_stage] +
                                         [model.FirstStageCosts] +
                                         [model.CvarAux] +  # this is also a first-stage variable; CvarPosPart is not: depends on scenario                                         
                                         [model.TranspOpexCost[t] for t in first_stage] + 
                                         [model.TranspCO2Cost[t] for t in first_stage] + 
                                         [model.TranspOpexCostB[t] for t in first_stage] + 
                                         [model.TranspCO2CostB[t] for t in first_stage] + 
                                         [model.TransfCost[t] for t in first_stage] + 
                                         [model.EdgeCost[t] for t in first_stage] + 
                                         [model.NodeCost[t] for t in first_stage] + 
                                         [model.UpgCost[t] for t in first_stage] + 
                                         [model.ChargeCost[t] for t in first_stage] 
                                         )



    
    
    

    ###### set scenario probabilties if they are not assumed equal######
    scenario_nr = base_data.scenario_information.scen_name_to_nr[scenario_name]
    model._mpisppy_probability = base_data.scenario_information.probabilities[scenario_nr]

    return model


def scenario_denouement(rank, scenario_name, scenario):
    pass

def option_settings_ef():   
    options = {}
    options["solvername"] = "gurobi"
    options["solver_options"] = {'MIPGap':MIPGAP,
                                'Method':2, #https://www.gurobi.com/documentation/10.0/refman/method.html#parameter:Method
                                }  # 'TimeLimit':600 (seconds)
    #["NumericFocus"] = 3 , 0 is automatic, 1 is low precision but fast #  https://www.gurobi.com/documentation/9.5/refman/numericfocus.html
    # "ScaleFlag" = 2  , geometric mean scaling  https://www.gurobi.com/documentation/10.0/refman/scaleflag.html#parameter:ScaleFlag
    # https://www.gurobi.com/documentation/10.0/refman/objscale.html#parameter:ObjScale
    # https://www.gurobi.com/documentation/10.0/refman/parameters.html
    
    return options

def option_settings_ph():   
    options = {}
    options["solvername"] = "gurobi"
    options["asynchronousPH"] = False
    options["PHIterLimit"] = 2
    options["defaultPHrho"] = 1
    options["convthresh"] = 0.0001
    options["subsolvedirectives"] = None
    options["verbose"] = False
    options["display_timing"] = True
    options["display_progress"] = True
    options["iter0_solver_options"] = None
    options["iterk_solver_options"] = None
    #options["NumericFocus"] = 3  #  https://www.gurobi.com/documentation/9.5/refman/numericfocus.html
    
    return options

