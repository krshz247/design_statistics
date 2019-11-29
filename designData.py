#!/usr/bin/env python
from nanodesign.converters import Converter
import nanodesign as nd
import numpy as np
#import ipdb  # use this for debugging instead of print() (ipdb.set_trace())
import re
import sys
import os
from pathlib import Path

class DesignData(object):

    def __init__(self, name: str):
        self.name: str = name
        self.dna_structure = self.init_design()
        self.all_strands: list = self.dna_structure.strands
        self.data: dict = {}
        self.all_bases: list = self.get_all_bases()
        self.hps_base: dict = self.init_hps()
        self.all_co_tuples_list: list = self.get_all_co_tuple()
        self.all_co_bases: list = self.get_all_co_bases()
        self.all_co_tuples_h, self.all_co_tuples_v = self.get_horozantal_vertical_co()
        self.full_co_list, self.full_co_list_v, self.full_co_list_h = self.get_full_co_list()
        self.end_co_set, self.end_co_set_v, self.end_co_set_h = self.get_endloop_co_list()
        self.half_co_list, self.half_co_list_v, self.half_co_list_h = self.get_half_co_list()
        self.scaf_co_bases, self.staple_co_bases = self.get_staple_scaffold_co_bases()
        self.helices_n: list = self.get_helix_per_staple()
        self.helix_dic: dict = self.init_helix_dict()
        self.first_bases, self.last_bases = self.get_first_last_bases_of_strands()
        self.helices = self.get_structure_helices()
        self.nicks: list = self.get_nicks()
         
    def compute_data(self) -> dict:
        data = {}
        
        data["Lattice type"] = self.get_lattice_type()
        data["n_staples"] = len(self.get_all_staple())
        
        staple_statistics = self.get_staple_length_statistics()
        for (key, stat) in staple_statistics.items():
            data[key] = stat
        
        avg_h_st_p, std_h_st_p, max_h_st_p, min_h_s_p = self.helices_staples_pass_statistics()
        data["avg_helices_staples_pass"] = avg_h_st_p 
        data["std_helices_staples_pass"] = std_h_st_p
        data["max_helices_a_staples_pass"] = max_h_st_p
        data["min_helices_staples_pass"] = min_h_s_p
        
        data["n_helices"] = len(self.get_structure_helices())
        data["n_skips"] = self.get_n_skips()
        data["n_nicks"] = len(self.nicks)
        data["n_co"] = self.get_total_n_co()
        
        avg_n_st_do, std_n_st_do, max_n_st_do, min_n_st_do = self.get_staple_domain_statistics()
        data["avg_n_staple_domain"] = avg_n_st_do 
        data["std_n_staple_domain"] = std_n_st_do
        data["max_n_staple_domain"] = max_n_st_do
        data["min_n_staple_domain"] = min_n_st_do
        
        n_st_l_do, n_st_s_do = self.get_n_staples_with_and_without_long_domains()
        data["n_staple_with_long_domains"] = n_st_l_do
        data["n_staple_with_no_long_domains"] = n_st_s_do
        
        (avg_n_l_do, std_n_l_do, max_n_l_do, min_n_l_do, n_st_with_2_long_do,
        n_st_with_one_long_do, n_st_with_no_long_do) = self.get_long_domains_statistic()
        data["n_staple_with_more_than_2_long_domains"] = n_st_with_2_long_do
        data["n_staple_with_one_long_domains"] = n_st_with_one_long_do
        data["n_staple_with_no_long_domains"] = n_st_with_no_long_do
        
        data["avg_n_long_domain_in_staples"] = avg_n_l_do
        data["std_n_long_domain_in_staples"] = std_n_l_do
        data["max_n_long_domain_in_staples"] = max_n_l_do
        data["min_n_long_domain_in_staples"] = min_n_l_do
        
        #scaf_co, staple_co = self.get_n_staple_scaffold_co()
        #data["scaf_co"] = scaf_co
        #data["staple_co"] = staple_co
        
        avg_n_st_co, std_n_st_co, max_n_st_co, min_n_st_co = self.staples_crossovers_statistics()
        data["avg_n_staples_co"] = avg_n_st_co
        data["std_n_staples_co"] = std_n_st_co
        data["max_n_co_of_a_staple"] = max_n_st_co
        data["min_n_co_of_a_staple"] = min_n_st_co
        
        full_co, half_co, endloop_co = self.get_n_co_types()
        data["n_all_full_co"] = full_co
        data["n_all_half_co"] = half_co
        data["n_all_endloops"] = endloop_co
        
        (full_scaf_co, full_staple_co, half_scaf_co, half_staple_co, end_scaf_co, end_staple_co,
        _,_,_,_,_,_,_,_,_,_)= self.get_n_scaf_staple_co_types()
        data["scaff_full_co"] = full_scaf_co
        data["staple_full_co"] = full_staple_co
        data["scaff_half_co"] = half_scaf_co
        data["staple_half_co"] = half_staple_co
        data["scaff_endloops"] = end_scaf_co
        data["staple_endloops"] = end_staple_co
        
        #bluntends = self.get_blunt_ends()
        #data["n_bluntends"] = len(bluntends)
        
        (scaf_co_density_v, scaf_co_density_h, st_co_density_v, st_co_density_h, 
         all_co_density_v, all_co_density_h, all_co_density_no_ends_v,
         all_co_density_no_ends_h) = self.get_co_density()
        data["scaf_co_density_v"] = scaf_co_density_v
        data["scaf_co_density_h"] = scaf_co_density_h
        data["st_co_density_v"] = st_co_density_v
        data["st_co_density_h"] = st_co_density_h
        data["all_co_density_v"] = all_co_density_v
        data["all_co_density_h"] = all_co_density_h
        data["all_co_density_noends_v"] = all_co_density_no_ends_v
        data["all_co_density_noends_h"] = all_co_density_no_ends_h
        
        self.data = data
        return self.data

    def init_design(self):
        file_name = "./Design Structures/" + self.name + ".json"
        seq_file = self.name + ".seq"
        seq_name = None
        converter = Converter(modify=True)
        converter.read_cadnano_file(file_name, None, "p8064")
        converter.dna_structure.compute_aux_data()
        #ipdb.set_trace()
        return converter.dna_structure

    def init_hps(self) -> dict:
        hps_base = {}
        for strand in self.all_strands:  
            for base in strand.tour:
                position = (base.h, base.p, base.is_scaf)
                hps_base[position] = base
        return hps_base
        
    def get_base_from_hps(self, h, p, is_scaffold, dir=1):
        if (h, p) in self.dna_structure.Dhp_skips:
            p += np.sign(dir) 
        return self.hps_base.get((h, p, is_scaffold), None) 

    def get_lattice_type(self):
        if type(self.dna_structure.lattice) == nd.data.lattice.SquareLattice:
            return "Square"
        else:
            return "Honeycomb"

    def get_all_bases(self) -> list:
        all_bases = []
        for strand in self.all_strands:
            for base in strand.tour: 
                all_bases.append(base)     
        return all_bases
        
    def get_staple_length_statistics(self):
        len_strands = []
        for strand in self.all_strands:
            if not strand.is_scaffold:
                tour_clean = [base for base in strand.tour]
                len_strands.append(len(tour_clean))
        return {
            "staple_length_avg": np.average(len_strands),
            "staple_length_std": np.std(len_strands),
            "min_staple_length": np.min(len_strands),
            "max_staple_length": np.max(len_strands),
        }
        
    def get_structure_size(self):
        
        return
    
    def get_structure_helices(self) -> int:
        helices = set()
        for strand in self.all_strands:
            if strand.is_scaffold:
                for base in strand.tour:
                    if self.dna_structure._check_base_crossover(base):
                        if base.h not in helices:
                            helices.add(base.h)
        return helices
                    
    def get_n_skips(self) -> int:
        return len(self.dna_structure.Dhp_skips)

    def get_staple_domain_statistics(self) -> list:
        n_st_domains = []
        for strand in self.all_strands:
            if not strand.is_scaffold:
                n_st_domains.append(len(strand.domain_list))

        return (np.average(n_st_domains), np.std(n_st_domains), 
                np.max(n_st_domains), np.min(n_st_domains) )     
    
    def get_n_staples_with_and_without_long_domains(self) -> int:
        long_st_domain = set()
        short_st_domain = set()
        for strand in self.all_strands:
            if not strand.is_scaffold:
                for domain in strand.domain_list:
                    if len(domain.base_list) >= 14:
                        long_st_domain.add(strand)
                if strand not in long_st_domain:
                    short_st_domain.add(strand)

        return len(long_st_domain), len(short_st_domain)
    
    def get_long_domains_statistic(self) -> int:
        long_st_domain = []
        n_long_domains = []
        n_strands_with_morethan_2_long_domians = []
        n_strands_with_one_long_domain = []
        n_strands_with_no_long_domain = []
        
        for strand in self.all_strands:
            if not strand.is_scaffold:
                for domain in strand.domain_list:
                    if len(domain.base_list) >= 14:
                        long_st_domain.append(strand)
                if len(long_st_domain) >= 2 :
                    n_strands_with_morethan_2_long_domians.append(strand)
                elif len(long_st_domain) == 1:
                    n_strands_with_one_long_domain.append(strand)
                elif len(long_st_domain) == 0:
                    n_strands_with_no_long_domain.append(strand)
                    
            n_long_domains.append(len(long_st_domain))
            long_st_domain = [] 
  
        return (np.average(n_long_domains), np.std(n_long_domains),
                np.max(n_long_domains), np.min(n_long_domains), 
                len(n_strands_with_morethan_2_long_domians),
                len(n_strands_with_one_long_domain), len(n_strands_with_no_long_domain))
    
    def get_all_staple(self) -> int:
        all_staples = []
        for strand in self.all_strands:
            if not strand.is_scaffold:
                all_staples.append(strand)
        return all_staples
    
    def get_helix_per_staple(self) -> list:
        helices_n = []
        for strand in self.all_strands:
            helices = set()
            if not strand.is_scaffold:
                for base in strand.tour:
                    if self.dna_structure._check_base_crossover(base):
                        if base.h not in helices:
                            helices.add(base.h)
                helices_n.append(len(helices))

        return helices_n
            
    def helices_staples_pass_statistics(self) -> int:
        return (np.average(self.helices_n), np.std(self.helices_n),
                np.max(self.helices_n), np.min(self.helices_n))
    
    def init_helix_dict(self) -> dict:
        helix_dic = {}
        helix_list = self.get_helix_per_staple()
        for strand, helices in zip(self.all_strands, helix_list):
            dic = {str(strand): helices}
            helix_dic.update(dic)

        return helix_dic
    
    def get_first_last_bases_of_strands(self) -> list:
        first_bases = set()
        last_bases = set()
        for strand in self.all_strands:
            if not strand.is_scaffold:
                first_bases.add(strand.tour[0])
                last_bases.add(strand.tour[-1])

        return first_bases, last_bases
    
    def get_nicks(self) ->int:
        nicks = []
        for base in self.first_bases:
            base_plus = self.get_base_from_hps(base.h, base.p + 1, base.is_scaf)
            base_minus = self.get_base_from_hps(base.h, base.p - 1, base.is_scaf, dir=-1)
            if base_plus in self.last_bases:
                nicks.append((base,base_plus))#order of nick is always (first,last)
            elif base_minus in self.last_bases:
                nicks.append((base,base_minus))
    
        return nicks
    
    def get_all_co_tuple(self) -> list:
        all_co_tuples = set()
        all_co_tuple_list = []
        for strand in self.all_strands:
            for base in strand.tour:
                if self.dna_structure._check_base_crossover(base):
                    co_tuple = set()
                    if base.up.h != base.h:
                        co_tuple.add(base.up)
                        co_tuple.add(base)
                        all_co_tuples.add(frozenset(co_tuple))
                        co_tuple = set()
                    elif base.down.h != base.h:
                        co_tuple.add(base.down)
                        co_tuple.add(base)
                        all_co_tuples.add(frozenset(co_tuple))
                        co_tuple = set()
        for co in all_co_tuples:
            all_co_tuple_list.append(co)

        return all_co_tuple_list
    
    def get_horozantal_vertical_co(self):
        all_co_tuples_h = set()
        all_co_tuples_v = set()
        helix_row = []
        map_id_helices = self.dna_structure.structure_helices_map
        for co_tuple in self.all_co_tuples_list:
            for base in co_tuple:
                helix_row.append(map_id_helices[base.h].lattice_row)
            #helix2_row = map_id_helices[co_tuple[1].helix].lattice_row
                #ipdb.set_trace()       
                
            if helix_row[0] == helix_row[1]:
                all_co_tuples_h.add(co_tuple)
            else:
                all_co_tuples_v.add(co_tuple)
            helix_row = []

        return all_co_tuples_h, all_co_tuples_v
        
    
    def get_all_co_bases(self):
        all_co_bases = []
        for strand in self.all_strands:
                for base in strand.tour:
                    if self.dna_structure._check_base_crossover(base):
                            all_co_bases.append(base)

        return all_co_bases
            
    def get_total_n_co(self) -> int:
        return len(self.all_co_bases)/2.
    
    def staples_crossovers_statistics(self) -> int:
        co_staple = []
        n_co_staples = []
        for strand in self.all_strands:
            if not strand.is_scaffold:
                for base in strand.tour:
                    if self.dna_structure._check_base_crossover(base):
                        co_staple.append(base)
                n_co_staples.append(len(co_staple)/2.)
                co_staple = []
        return (np.average(n_co_staples), np.std(n_co_staples),
                np.max(n_co_staples), np.min(n_co_staples))     
        
    def get_full_co_list(self) -> list:
        co_plus_tuples = []
        co_minus_tuples = []
        full_co_list = []
        full_co_list_v = []
        full_co_list_h = []
        for co in self.all_co_tuples_list:
            co_tuple_plus = set()
            co_tuple_minus = set()
            for base in co:
                base_plus = self.get_base_from_hps(base.h, base.p + 1, base.is_scaf)
                base_minus = self.get_base_from_hps(base.h, base.p - 1, base.is_scaf, dir=-1)
                co_tuple_plus.add(base_plus)
                co_tuple_minus.add(base_minus)
            #ipdb.set_trace()
            co_plus_tuples.append(frozenset(co_tuple_plus))    
            co_minus_tuples.append(frozenset(co_tuple_minus))
            
            if co_plus_tuples[0] in self.all_co_tuples_list:
                full_co_list.append(co)
                if co in self.all_co_tuples_h:
                    full_co_list_h.append(co)
                else:
                    full_co_list_v.append(co)
                    
            elif co_minus_tuples[0] in self.all_co_tuples_list:
                full_co_list.append(co)
                if co in self.all_co_tuples_h:
                    full_co_list_h.append(co)
                else:
                    full_co_list_v.append(co)
        
            co_plus_tuples = []
            co_minus_tuples = []

        #ipdb.set_trace()    
        return full_co_list, full_co_list_v, full_co_list_h
    
    def get_endloop_co_list(self) -> list:    
        end_co_set = set()
        end_co_set_h= set()
        end_co_set_v = set()
        #base_plus_list = []
        for co in self.all_co_tuples_list:   
            for base in co:
                base_plus = self.get_base_from_hps(base.h, base.p + 1, base.is_scaf)
                base_minus = self.get_base_from_hps(base.h, base.p - 1, base.is_scaf, dir=-1)
                #base_plus_list.append(base_plus)
                if (base_plus is None) or (base_minus is None):
                    end_co_set.add(co)
                    if co in self.all_co_tuples_h:
                        end_co_set_h.add(co)
                    else:
                        end_co_set_v.add(co)
        #ipdb.set_trace()
        return end_co_set, end_co_set_v, end_co_set_h
 
    def get_half_co_list(self) -> list:
        half_co_list = []
        half_co_list_h =[]
        half_co_list_v = []
        for co in self.all_co_tuples_list:
            if (co not in self.end_co_set) and (co not in self.full_co_list):
                half_co_list.append(co)
                if co in self.all_co_tuples_h:
                    half_co_list_h.append(co)
                else:
                    half_co_list_v.append(co)
        #ipdb.set_trace()        
        return half_co_list, half_co_list_v, half_co_list_h
    
    def get_n_co_types(self) -> int:
        return len(self.full_co_list)/2., len(self.half_co_list), len(self.end_co_set)
    
    def get_n_co_types_v_h(self) -> int:
        return (len(self.full_co_list_v)/2., len(self.half_co_list_v), len(self.end_co_set_v),
                len(self.full_co_list_h)/2., len(self.half_co_list_h), len(self.end_co_set_h))
    
    def get_staple_scaffold_co_bases(self):
        scaf_co_bases = []
        staple_co_bases = []
        
        for base in self.all_co_bases:
        #considering the skips in crossovers
            if base.is_scaf:
                scaf_co_bases.append(base)
            else:
                staple_co_bases.append(base)
                            
        return scaf_co_bases, staple_co_bases
    
    def get_n_staple_scaffold_co(self):
        return len(self.scaf_co_bases)/2., len(self.staple_co_bases)/2.
    
    def get_n_scaf_staple_co_types(self):
        full_scaf_co_set = set()
        full_staple_co_set = set()
        half_scaf_co_set = set()
        half_staple_co_set = set()
        end_scaf_co_set = set()
        end_staple_co_set = set()
        
        st_half_co_list_h = set()
        st_half_co_list_v = set()
        
        sc_full_co_list_h = set()
        sc_full_co_list_v = set()
        st_full_co_list_h = set()
        st_full_co_list_v = set()
        
        sc_end_co_list_h = set()
        sc_end_co_list_v = set()
        st_end_co_list_h = set()
        st_end_co_list_v = set()
        
        for co in self.full_co_list:
            for base in co:
                if base.is_scaf:
                    full_scaf_co_set.add(co)
                    if co in self.all_co_tuples_h:
                        sc_full_co_list_h.add(co)
                    else:
                        sc_full_co_list_v.add(co)
                
                else:
                    full_staple_co_set.add(co)
                    if co in self.all_co_tuples_h:
                        st_full_co_list_h.add(co)
                    else:
                        st_full_co_list_v.add(co)
                    
        for co in self.half_co_list:
            for base in co:
                if base.is_scaf:
                    half_scaf_co_set.add(co)
                    #we put it to zero by hand
                    half_scaf_co_set = set()
                else:
                    half_staple_co_set.add(co)
                    if co in self.all_co_tuples_h:
                        st_half_co_list_h.add(co)
                    else:
                        st_half_co_list_v.add(co)
                        
        for co in self.end_co_set:
            for base in co:
                if base.is_scaf:
                    end_scaf_co_set.add(co)
                    if co in self.all_co_tuples_h:
                        sc_end_co_list_h.add(co)
                    else:
                        sc_end_co_list_v.add(co)
                    
                else:
                    end_staple_co_set.add(co)
                    if co in self.all_co_tuples_h:
                        st_end_co_list_h.add(co)
                    else:
                        st_end_co_list_v.add(co)
                
                
        #ipdb.set_trace()         
        return (len(full_scaf_co_set)/2., len(full_staple_co_set)/2., len(half_scaf_co_set), 
                len(half_staple_co_set), len(end_scaf_co_set), len(end_staple_co_set),
                len(st_half_co_list_h), len(st_half_co_list_v), len(sc_full_co_list_h)/2,
                len(sc_full_co_list_v)/2, len(st_full_co_list_h)/2, len(st_full_co_list_v)/2,
                len(sc_end_co_list_h), len(sc_end_co_list_v), len(st_end_co_list_h),
                len(st_end_co_list_v))
                

    def get_co_density(self):
        def is_ds(pos, hid):
            is_sc = (hid, pos , True) in self.hps_base
            is_st = (hid, pos, False) in self.hps_base
            is_skip = False # (hid, pos) in self.skips (note: list of (h,p) for all skips)
            return ((is_sc and is_st) or is_skip)
        
        def cleanup_co(co_list):
            n_ends = 0
            if not co_list:
               return 0, 0
            if len(co_list) == 1:
                return 1, 0
            if len(co_list) == 2 and co_list[0] != co_list[1]:
                return 2, 0

            if co_list[0]+1 != co_list[1]:
                    n_ends += 1
                    co_list = co_list[1:]
            if co_list[-1]-1 != co_list[-2]:
                n_ends += 1
                co_list = co_list[:-1]
            return n_ends, len(co_list)/2
        

        helices = self.dna_structure.structure_helices_map.values()
        n_possible_co_st_v = 0
        n_possible_co_st_h = 0
        n_possible_co_sc_v = 0
        n_possible_co_sc_h = 0
        n_possible_end_co_st_v = 0
        n_possible_end_co_st_h = 0
        n_possible_end_co_sc_v = 0
        n_possible_end_co_sc_h = 0
        
        for helix in helices:
            helix_row = helix.lattice_row
            stple_co_h = [co[1] for co in helix.possible_staple_crossovers
                          if (is_ds(pos=co[1], hid=helix.id)
                              and (helix_row == co[0].lattice_row)
                              )
                          ]
            stple_co_h = sorted(stple_co_h)
            n_end_st_h, n_co_st_h = cleanup_co(stple_co_h)
            stple_co_v = [co[1] for co in helix.possible_staple_crossovers
                          if (is_ds(pos=co[1], hid=helix.id)
                              and (helix_row != co[0].lattice_row)
                              )
                          ]
            stple_co_v = sorted(stple_co_v)
            n_end_st_v, n_co_st_v = cleanup_co(stple_co_v)
            
            scaf_co_h = [co[1] for co in helix.possible_scaffold_crossovers
                          if (is_ds(pos=co[1], hid=helix.id)
                              and (helix_row == co[0].lattice_row)
                              )
                          ]
            scaf_co_h = sorted(scaf_co_h)
            n_end_sc_h, n_co_sc_h = cleanup_co(scaf_co_h)
            
            scaf_co_v = [co[1] for co in helix.possible_scaffold_crossovers
                          if (is_ds(pos=co[1], hid=helix.id)
                              and (helix_row != co[0].lattice_row)
                              )
                          ]
            scaf_co_v = sorted(scaf_co_v)
            n_end_sc_v, n_co_sc_v = cleanup_co(scaf_co_v)
    
            n_possible_co_st_v += (n_co_st_v)
            n_possible_co_st_h += (n_co_st_h)
            n_possible_end_co_st_v += n_end_st_v
            n_possible_end_co_st_h += n_end_st_h
            n_possible_co_sc_v += (n_co_sc_v)
            n_possible_co_sc_h += (n_co_sc_h)
            n_possible_end_co_sc_v += n_end_sc_v
            n_possible_end_co_sc_h += n_end_sc_h

        n_possible_co_st_v = (n_possible_co_st_v)/2  
        n_possible_co_st_h = (n_possible_co_st_h)/2
        n_possible_co_sc_v = (n_possible_co_sc_v)/2  
        n_possible_co_sc_h = (n_possible_co_sc_h)/2
        
        n_possible_end_co_st_v = (n_possible_end_co_st_v)/2
        n_possible_end_co_st_h = (n_possible_end_co_st_h)/2
        n_possible_end_co_sc_v = (n_possible_end_co_sc_v)/2
        n_possible_end_co_sc_h = (n_possible_end_co_sc_h)/2
        
        (full_scaf_co, full_staple_co, half_scaf_co, 
         half_staple_co, end_scaf_co, end_staple_co, st_half_co_h, 
         st_half_co_v, sc_full_co_h, sc_full_co_v, st_full_co_h, 
         st_full_co_v, sc_end_co_h, sc_end_co_v, st_end_co_h, 
         st_end_co_v) = self.get_n_scaf_staple_co_types()   
        
        scaf_co_density_v = (sc_full_co_v + half_scaf_co)/ (n_possible_co_sc_v)
        scaf_co_density_h = (sc_full_co_h + half_scaf_co)/ (n_possible_co_sc_h)
        
        st_co_density_v = (st_full_co_v + st_half_co_v) / (n_possible_co_st_v)
        st_co_density_h = (st_full_co_h + st_half_co_h) / (n_possible_co_st_h)
        
        all_co_density_v = ((sc_full_co_v + st_full_co_v + half_scaf_co + 
                          st_half_co_v +  st_end_co_v + sc_end_co_v) /
                        (n_possible_co_sc_v + n_possible_co_st_v + 
                         n_possible_end_co_sc_v + n_possible_end_co_st_v ))
            
        all_co_density_h = ((sc_full_co_h + st_full_co_h + half_scaf_co + 
                          st_half_co_h +  st_end_co_h + sc_end_co_h) /
                        (n_possible_co_sc_h + n_possible_co_st_h + 
                         n_possible_end_co_sc_h + n_possible_end_co_st_h ))
                           
        all_co_density_no_ends_v = (sc_full_co_v + st_full_co_v + half_scaf_co + 
                                    st_half_co_v) / (n_possible_co_sc_v + n_possible_co_st_h)
        all_co_density_no_ends_h = (sc_full_co_h + st_full_co_h + half_scaf_co + 
                                    st_half_co_h) / (n_possible_co_sc_h + n_possible_co_st_h)
    
        return (scaf_co_density_v, scaf_co_density_h, st_co_density_v, st_co_density_h, 
                all_co_density_v, all_co_density_h, all_co_density_no_ends_v, all_co_density_no_ends_h)
    
    def get_blunt_ends(self):
        blunt_ends = set()
        blunt_end = set()
        for co in self.end_co_set:
            for base in co:
                    for co_s in self.all_co_tuples_list:
                        for base_s in co_s:
                            if not base_s.is_scaf:
                                if (base.h == base_s.h) and (base.p == base_s.p):
                                    blunt_end.add(frozenset(co))
                                    blunt_end.add(frozenset(co_s))
                                    blunt_ends.add(frozenset(blunt_end)) 
        return blunt_ends
    
def export_data(data: dict, name: str) -> None:
    header = ", ".join(data.keys())
    data_str = ", ".join([str(i) for i in data.values()])
    try:
        os.mkdir("out")
    except FileExistsError:
        pass
    
    with open("./out/"+ name + "-designdata.csv", mode="w+") as out:
        out.write(header + "\n")
        out.write(data_str)
        out.write("\nEND")
    return

def main():
    #file  = open(Path("./txt_file.txt"), 'rt', encoding="utf8")
    #for line in file:
      #  if line.startswith('Project ='):
     #       name = line[9:-1].strip()
    #        break
    print("master, I am awaiting the name of your design")
    name = input()
    print("Thank you Sir")
    designData = DesignData(name=name)
    data = designData.compute_data()
    export_data(data=data, name=name)
    return

if __name__ == "__main__":
    main()

