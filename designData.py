#!/usr/bin/env python
# -*- coding: utf-8 -*-3

import nanodesign as nd
import numpy as np
from sklearn.cluster import DBSCAN
import logging
import itertools
from Bio.SeqUtils import MeltingTemp  # compute melting temperatures
from Bio.Seq import Seq
from classes.crossover import Crossover
from classes.nicks import Nick
from statistics import mean


class DesignData(object):

    def __init__(self, json: str, name: str, seq: str):

        self.logger = logging.getLogger(__name__)
        self.name: str = name
        self.dna_structure, self.dna_structure_skips = self.init_design(json, seq)

        # strand, base
        self.strands: list = self.dna_structure.strands
        self.staples = self._get_staple()
        self.hps_base, self.hps_base_skips = self._init_hps(), self._init_hps_skips()
        self.scaf_bases = self._get_all_scaf_bases()

        # helix
        self.helices = self.dna_structure.structure_helices_map
        self.staple_helix_dict = self._get_helix_data()

        # domain
        self._init_domain_data()
        self.long_domains = self.get_staples_with_long_domains()
        self.staple_domains_melt_t: dict = self.staple_domains_melt_t()
        # NOTE: dictionary of staples and maximum melting temp of domains for each staple
        self.max_staple_melt_t = {key: max(value) for (key, value) in self.staple_domains_melt_t.items()}

        # crossover
        self._all_co_sets = self._get_all_connections()
        self.full_crossovers = self._create_full_crossover_list()
        self.endloops = self._create_endloops_list()
        self.half_crossovers = self._create_half_crossover_list()
        self.all_crossovers = self._create_all_crossover_list()
        self.full_scaff_position()
        self.stacks = self.get_stacks()

    def init_design(self, json, seq):
        converter = nd.converters.Converter(modify=True, logg=False)
        converter.read_cadnano_file(json, None, seq)
        converter.dna_structure.compute_aux_data()
        converter_skip = nd.converters.Converter(modify=False, logg=False)
        converter_skip.read_cadnano_file(json, None, seq)
        converter_skip.dna_structure.compute_aux_data()
        return converter.dna_structure, converter_skip.dna_structure

    def _close_strand(self, strand):
        """[closes the scaffold andmaking it a loop]

        Returns:
            [strand] -- [closed scaffold strand]
        """
        start = strand.tour[0]
        end = strand.tour[-1]
        start.up, end.down = end, start
        self.dna_structure.strands[start.strand].is_circular = True

        return strand

    def _get_staple(self) -> list:
        return [strand for strand in self.strands if not strand.is_scaffold]

    def _init_hps(self) -> dict:
        """[create a dictionary of bases positions and the bases itself for all bases in the structure excluding the skips]

        Returns:
            dict: [keys: position = (base.h, base.p, base.is_scaf), values: base object]
        """
        hps_base = dict()
        for strand in self.dna_structure.strands:
            hps_base.update({(base.h, base.p, base.is_scaf): base for base in strand.tour})
        return hps_base

    def _init_hps_skips(self) -> dict:
        """[create a dictionary of bases positions and the bases itself for all bases in the structure including the skips]

        Returns:
            dict: [keys: position = (base.h, base.p, base.is_scaf), values: base object]
        """
        hps_base_skips = dict()
        for strand in self.dna_structure_skips.strands:
            hps_base_skips.update({(base.h, base.p, base.is_scaf): base for base in strand.tour})
        return hps_base_skips

    def _get_base_from_hps(self, h, p, is_scaffold, dir=1):
        """[get the base object from its coordination: (h, p is_scaffold)]

        Arguments:
            h {[int]} -- [helix]
            p {[int]} -- [position]
            is_scaffold {bool} -- [scaffold = True or staple = False]

        Keyword Arguments:
            dir {int} -- [direction] (default: {1})

        Returns:
            [base] -- [base of the giver coordination]
        """

        if (h, p) in self.dna_structure.Dhp_skips:
            p += np.sign(dir)

        return self.hps_base.get((h, p, is_scaffold), None)

    def get_base_plus_minus(self, base):
        """[given a base, it returns the neighbour bases]

        Returns:
            [base_plus] -- [base with one position up along the helix]
            [base_minus] -- [base with on position down along the helix]
        """
        base_plus = self._get_base_from_hps(base.h, base.p + 1, base.is_scaf)
        base_minus = self._get_base_from_hps(base.h, base.p - 1, base.is_scaf, dir=-1)

        return base_plus, base_minus

    def _get_first_last_bases_of_strands(self):
        """
        Returns:
            [set]: [
                firstbases: a set of first bases of all the staples
                lastbases: a set of last bases of all the staples
                ]
        """

        first_bases = {staple.tour[0] for staple in self.staples}
        last_bases = {staple.tour[-1] for staple in self.staples}

        return first_bases, last_bases

    def get_lattice_type(self):
        if type(self.dna_structure.lattice) == nd.data.lattice.SquareLattice:
            return "Square"
        else:
            return "Honeycomb"

    def get_dimension(self):
        """[gets the dimension of the structure.]

        Returns:
            [tuple]: [
                a: max length of the columns in CadNano
                b: max length of the rows in Cadnano
                c: diffrence of min base postion in the struction and the max base position in Cadnano (structure's depth)
            ]
        NOTE: the values could be wrong for exotic designs
        """

        lattice_cols = [helix.lattice_col for helix in self.helices.values()]
        lattice_rows = [helix.lattice_row for helix in self.helices.values()]
        base_pos = [base.p for base in self.scaf_bases]

        a = max(lattice_cols) - min(lattice_cols) + 1
        b = max(lattice_rows) - min(lattice_rows) + 1
        c = max(base_pos) - min(base_pos) + 1

        return (a, b, c)

    def _get_all_scaf_bases(self) -> list:
        return [base for strand in self.strands for base in strand.tour if strand.is_scaffold]

    def get_staples_length(self) -> list:
        """[creates a list of staples length]

        Returns:
            list: [staples length]
        """
        return [len([base for base in staple.tour]) for staple in self.staples]

    def _init_domain_data(self) -> dict:
        """[creates a three dictionary of staples and their domains informations]

        Returns:
            dict -- domain_data:  [dictionary of staples and list of their domains]
            dict -- domain_lengths_data:  [dictionary of staples and list of their domains lengths]
            dict -- n_staples_domains:  [dictionary of staples and number of their domains]
        """
        self.domain_data = {staple: staple.domain_list for staple in self.staples}
        self.domain_lengths_data = {staple: [len(domain.base_list) for domain in domain]
                                    for staple, domain in self.domain_data.items()}
        self.n_staples_domains = {staple: len(self.domain_data[staple]) for staple in self.domain_data.keys()}

    def staple_domains_melt_t(self) -> dict:
        """[staples domain melting temperature.]

        Returns:
            dict: [key: staple. values: list of domains' melting temperature.]
        """
        staple_domains_melt_t = {}

        for staple, domains in self.domain_data.items():
            for domain in domains:
                if "N" not in domain.sequence:
                    # NOTE: using nearest neighbor for domain with length higher than 14
                    if len(domain.base_list) > 14:
                        staple_domains_melt_t.setdefault(staple, []).append(MeltingTemp.Tm_NN(
                            Seq(domain.sequence), Na=0, Mg=17.5))

                    # NOTE: using 'Wallace rule' for domain with length less than 14
                    else:
                        staple_domains_melt_t.setdefault(staple, []).append(MeltingTemp.Tm_Wallace(
                            Seq(domain.sequence)))

        return staple_domains_melt_t

    def get_alpha_value(self):
        """[alpha value : The ratio of number of staples having doamins with melting
        temperature higher than critical temperature to the number of all staples in the structure]

        Returns:
            [dict]: [alpha values of the structure for different critical temperatures]
        """

        T_crit = {40: int, 55: int, 70: int}

        def calculate(self, T_crit):
            """
            [calculates alpha value for a given critical temperature]
            """
            return sum([True for T in list(self.max_staple_melt_t.values()) if T >= T_crit]) / len(self.max_staple_melt_t)

        alpha_values = {T: calculate(self, T) for T in T_crit}

        return alpha_values

    def get_staples_with_long_domains(self) -> dict:
        """[long domain are domains with 14 or more bases]

        Returns:
            dict -- [staples : numbers of long_domains for the each staple]
        """
        return {staple: len(list(filter(lambda x: x >= 14, domain_length)))
                for staple, domain_length in self.domain_lengths_data.items()}

    def divide_domain_lengths(self) -> dict:
        """[divide staples having 0, 1, 2 or more long domains ]

        Returns:
            dict: [
                2_long_domains: two or more long domains,
                1_long_domains: having only one long domain,
                0_long_domains: having no long domain,
                co_rule_violation: unpaired domains with less than 5 bases]
        """
        data = dict()
        domain_unpaired = list()

        for staple, n_longs in self.long_domains.items():
            if n_longs >= 2:
                data.setdefault("2_long_domains", []).append(staple)
            elif n_longs == 1:
                data.setdefault("1_long_domains", []).append(staple)
            elif n_longs == 0:
                data.setdefault("0_long_domains", []).append(staple)

        for staple, domains in self.domain_data.items():
            domain_unpaired.extend([domain for domain in domains if domain.base_list[0].across is None])

            data.setdefault("co_rule_violation", []).extend(
                [domain for domain in domains if (domain not in domain_unpaired) and (len(domain.base_list) < 5)])

        return data

    def _get_helix_data(self) -> dict:
        """
        [creates a two dictionary with staple and helices that it passes through]

        Returns:
            dict: [
                staple_helix_dict: [staple: helices ID the staple passes through],

        """
        return {staple: {base.h for base in staple.tour} for staple in self.staples}

    def get_num_staple_helix(self):
        return [len(helix_ids) for helix_ids in self.staple_helix_dict.values()]

    def get_nicks(self) -> int:
        # order of nick is always (first base,last base)
        nicks = list()

        def create_nick(base, neighbor_base):
            bases = (base, neighbor_base)
            p = (base.p, neighbor_base.p)
            h = (base.h, neighbor_base.h)
            nick = Nick(bases, set(p), set(h))
            return nick

        first_bases, last_bases = self._get_first_last_bases_of_strands()
        for base in first_bases:
            base_plus, base_minus = self.get_base_plus_minus(base)
            if base_plus in last_bases:
                nicks.append(create_nick(base, base_plus))
            if base_minus in last_bases:
                nicks.append(create_nick(base, base_minus))

        return nicks

    def _create_full_crossover_list(self):
        self._get_full_co_list()
        return [Crossover('full', co, self.helices) for co in self._full_co_tuples]

    def _create_half_crossover_list(self):
        half_co_tuples = self._get_half_co()
        half_co = [Crossover('half', co, self.helices) for co in half_co_tuples]
        for co in half_co:
            if co.strand_typ == 'scaffold':
                self.logger.warning(
                    f"structure {self.name.strip('.json')} contains half scaffold crossovers!"
                )
                break

        # eliminating half scaffold crossovers
        return [co for co in half_co if co.strand_typ != 'scaffold']

    def _create_endloops_list(self):
        end_co_tuples = self._get_endloop()
        return [Crossover('end', co, self.helices)for co in end_co_tuples]

    def _create_all_crossover_list(self):
        return self.half_crossovers + self.endloops + self.full_crossovers

    def full_scaff_position(self):
        """[assign type to full crossover: position of the full scaffold crossover depending on
        the position suggested by cadnano]
        """
        for full in self.full_crossovers:
            if full.strand_typ == 'scaffold':
                sub_new = np.Infinity
                # find closest crossover
                # TODO: change to possibe staple co!!! or even just check p
                for co in self.all_crossovers:
                    if co.strand_typ == 'staple':

                        if co.h == full.h:
                            sub = (mean(full.p) - mean(co.p))

                            if abs(sub) <= abs(sub_new):
                                sub_new = sub

                if sub_new is np.Infinity:
                    full.scaff_full_type = 0
                    continue

                # calculate type
                if self.get_lattice_type() == 'Square':
                    mod = sub_new % 32

                    if 0 <= mod <= 11:
                        typ = 1
                    elif 21 <= mod < 32:
                        typ = 3
                    else:
                        typ = 2

                else:
                    mod = sub_new % 21
                    if 0 <= mod <= 11:
                        typ = 1
                    elif 11 < mod < 21:
                        typ = 3

                full.scaff_full_type = typ

    def _get_all_connections(self) -> list:
        """[get a list of connections but not as objects but as a tuple of the two bases connected via a crossover]

        Returns:
            list -- [list of all crossovers]
        """
        all_co_tuples = set()

        # NOTE: closing the scaffold
        for strand in self.strands:
            if strand.is_scaffold:
                self.strands[strand.id] = self._close_strand(strand)

        for strand in self.strands:
            for base in strand.tour:
                if self.dna_structure._check_base_crossover(base):
                    co_tuple = set()

                    if base.up.h != base.h:
                        co_tuple = (base, base.up)
                        all_co_tuples.add(tuple(set(co_tuple)))
                    elif base.down.h != base.h:
                        co_tuple = (base.down, base)
                        all_co_tuples.add(tuple(set(co_tuple)))

        return [set(co) for co in all_co_tuples]

    def _get_full_co_list(self) -> list:
        """[gets the full crossovers as tuples of bases]

        Returns:

            list -- [
                _full_co_tuples: get full co as a pack of two connections
                (representation: [Co[B,B],Co[B,B], all in lists)
                _full_co_list_seperate: seperately as individual connections
                (every Co in frozenset of two bases)
                    ]
        """
        self._full_co_sets_seperate = list()
        self._full_co_tuples = list()

        full_co_list = list()

        for co in self._all_co_sets:
            co_neighbours = dict()

            co_neighbours["plus"] = {self.get_base_plus_minus(base)[0] for base in co}
            co_neighbours["minus"] = {self.get_base_plus_minus(base)[1] for base in co}

            full_co_list.extend([frozenset([frozenset(co_neighbours[typ]), frozenset(co)])
                                 for typ in ["plus", "minus"] if co_neighbours[typ] in self._all_co_sets])

        """
        putting all full_co in a list configuration as [(Co(B,B),Co(B,B))]
        two parallel Co in a tuple and two bases also in a tuple
        """
        full_co_set = set(full_co_list)
        for full_set in full_co_set:

            self._full_co_tuples.append(tuple([tuple(co) for co in full_set]))
            self._full_co_sets_seperate.extend([co for co in full_set])

        # return full_co_sets_seperate, full_co_tuples

    def _get_endloop(self) -> list:
        # NOTE: we want to ensure bases has consistent type regardless of type

        self._end_co_sets = list()
        for co in self._all_co_sets:
            for base in co:
                base_plus, base_minus = self.get_base_plus_minus(base)

                is_none = (base_plus is None) or (base_minus is None)
                if (is_none) and (co not in self._end_co_sets):
                    self._end_co_sets.append(frozenset(co))

        return [tuple([tuple(end), None]) for end in self._end_co_sets]

    def _get_half_co(self) -> list:
        # NOTE: we want to ensure bases has consistent type regardless of type

        def condition(self, co):
            return (co not in self._end_co_sets) and (co not in self._full_co_sets_seperate)

        half_co_sets = [co for co in self._all_co_sets if condition(self, co)]
        half_co_tuples = [tuple([tuple(co), None]) for co in half_co_sets]

        return half_co_tuples

    def classify_crossovers(self):
        data = {"scaffold": dict(), "staple": dict()}
        types = {"full": self.full_crossovers,
                 "half": self.half_crossovers,
                 "end": self.endloops,
                 }

        for typ, crossovers in types.items():
            co_subsets = {"scaffold": {"": set(), "_h": set(), "_v": set()},
                          "staple": {"": set(), "_h": set(), "_v": set()}}

            for co in crossovers:
                strand = "scaffold" if co.strand_typ == 'scaffold' else "staple"
                co_subsets[strand][""].add(co)
                if co.orientation == "horizontal":
                    co_subsets[strand]["_h"].add(co)
                else:
                    co_subsets[strand]["_v"].add(co)

                for s, direction_sets in co_subsets.items():  # scaffold, staple
                    for dir in direction_sets:  # h, v
                        len_subset = len(co_subsets[s][dir])
                        data[s][typ + dir] = len_subset

        for strand in ["scaffold", "staple"]:
            data[strand]["co"] = data[strand]["half"] + data[strand]["full"]
            for typ in ["v", "h"]:
                data[strand][
                    "co_" + typ] = (data[strand]["half_" + typ] + data[strand]["full_" + typ])

        return data

    def get_insertion_deletion_density(self):
        data = {"del_density": 0,
                "ins_density": 0}
        base_ins = 0
        for strand in self.dna_structure_skips.strands:
            for base in strand.tour:
                if base.num_insertions != 0:
                    base_ins += 1

        data["del_density"] = len(self.dna_structure.Dhp_skips) / len(self.scaf_bases)
        data["ins_density"] = base_ins / len(self.scaf_bases)

        return data

    def get_stacks(self):
        same_pos = dict()
        stacks = dict()
        num = 0

        for full_coupled in itertools.combinations(self.full_crossovers, 2):
            if len(full_coupled[0].p) >= 3:
                co_1_pos = (tuple(full_coupled[0].p)[0], tuple(full_coupled[0].p)[-1])
            else:
                co_1_pos = tuple(full_coupled[0].p)

            if len(full_coupled[1].p) >= 3:
                co_2_pos = (tuple(full_coupled[1].p)[0], tuple(full_coupled[1].p)[-1])
            else:
                co_2_pos = tuple(full_coupled[1].p)

            subtract = np.abs(np.subtract(co_1_pos, co_2_pos))
            condition = np.sum(subtract)
            if condition < 4:
                for f in full_coupled:
                    try:
                        same_pos[co_1_pos].add(f)
                    except KeyError:
                        same_pos[co_1_pos] = set()
                        same_pos[co_1_pos].add(f)

        for key, co_list in same_pos.items():
            stacks.setdefault(key, [])
            h_list = [co.h for co in co_list]
            dummy_stacks = np.array(h_list)
            for j in range(int(np.log2(len(h_list)) + 2)):

                for coup in itertools.combinations(dummy_stacks, 2):
                    if len(coup[0].intersection(coup[1])) != 0:
                        dummy_stacks[np.where(dummy_stacks == coup[0])] = coup[0].union(coup[1])
                        dummy_stacks[np.where(dummy_stacks == coup[1])] = coup[0].union(coup[1])
                dummy_stacks = np.unique(np.array(dummy_stacks))

            for stack in dummy_stacks:
                if len(stack) < 3:
                    dummy_stacks[np.where(dummy_stacks == stack)] = set()
                else:
                    if stack not in stacks[key]:
                        stacks.setdefault(key, []).append(stack)
                        num += 1

        return stacks

    def get_stacks_lengths(self):
        return [(len(stack) - 1) for stacks in self.stacks.values() for stack in stacks]

    def get_co_density(self):
        """[calculate crossover density (number of crossovers is the structure divided by possible crossovers CadNano)]
        NOTE: the values for number of possible_co and co_desity are not exact but close to the true value
        """
        # TODO: possible_ co numbers are not exactly correct
        def is_ds(pos, hid):
            is_sc = (hid, pos, True) in self.hps_base_skips
            is_st = (hid, pos, False) in self.hps_base_skips
            # (hid, pos) in self.skips (note: list of (h,p) for all skips)
            is_skip = False

            return ((is_sc or is_st) or is_skip)

        def cleanup_co(co_list):
            n_ends = 0
            if not co_list:
                return 0, 0
            if len(co_list) == 1:
                return 1, 0
            if len(co_list) == 2 and co_list[0] != co_list[1]:
                return 2, 0

            if co_list[0] + 1 != co_list[1]:
                n_ends += 1
                co_list = co_list[1:]
            if co_list[-1] - 1 != co_list[-2]:
                n_ends += 1
                co_list = co_list[:-1]
            # TODO: devision by two is assumed for possible_full_co(two connections)
            return n_ends, len(co_list) // 2

        def neighbour_bases(strand_typ, helix):
            """[gives a list of all bases in the neighbouring helix to ckeck if there
            exist a base in the neighbouring helix to connect to the base that is a possible_co in the main helix]

            Args:
                strand_typ ([str]): [Scaffold or Staple]
                helix ([DnaStructureHelix]): [neighbouring helix]

            Returns:
                [list]: [list of all the bases in the neighbouring helix]

            """
            if strand_typ == 'scaffold':
                neighbour_bases = [base.p for base in helix.scaffold_bases]
            else:
                neighbour_bases = [base.p for base in helix.staple_bases]

            return neighbour_bases

        def orientation(typ, helix, helix_row):
            if typ == 'h':
                return helix_row == helix.lattice_row
            else:
                return helix_row != helix.lattice_row

        possible_crossovers = {"scaffold": {"co": 0, "co_h": 0, "co_v": 0},
                               "staple": {"co": 0, "co_h": 0, "co_v": 0}
                               }
        # part 1: number of possible crossovers
        helices = self.dna_structure_skips.structure_helices_map.values()

        for helix in helices:
            helix_row = helix.lattice_row

            for strand in ["scaffold", "staple"]:
                for typ in ["v", "h"]:

                    # NOTE: nanodesign crossoevers are actually connections
                    if strand == "scaffold":
                        p_co = helix.possible_scaffold_crossovers

                    else:
                        p_co = helix.possible_staple_crossovers

                    x = [co[1] for co in p_co if (is_ds(pos=co[1], hid=helix.id)
                                                  and orientation(typ, co[0], helix_row)
                                                  and (co[1] in neighbour_bases(strand, co[0])))]

                    end, co = cleanup_co(sorted(x))
                    # TODO: devision by two is assumed for counting each possible_co two times for a helix and its neighbour

                    possible_crossovers[strand]["co"] += co // 2
                    possible_crossovers[strand]["co_" + typ] += co // 2
                    # possible_crossovers[strand]["end"] += end

        # part2 get actual crossovers
        set_crossovers = self.classify_crossovers()

        co_density = dict()
        for strand in ["scaffold", "staple"]:
            co_density[strand] = dict()
            for typ, n_possible in possible_crossovers[strand].items():
                n_set = set_crossovers[strand][typ]
                if n_possible == 0:
                    co_density[strand][typ] = 0
                else:
                    co_density[strand][typ] = n_set / n_possible

        return possible_crossovers, co_density

    def get_blunt_ends(self):
        blunt_ends = set()
        first_bases, last_bases = self._get_first_last_bases_of_strands()

        for end in self.endloops:
            has_across = (end.bases[0][0].across is True) and (
                end.bases[0][1].across is True)
            if end.strand_typ == 'scaffold' and has_across:
                blunt_ends = {end.bases[0] for base in end.bases[0] if (
                    base.across in first_bases) or (base.across in last_bases)}

        return blunt_ends

    def get_loops(self):
        loops = list()
        for co in self.full_crossovers + self.half_crossovers:
            sub = np.inf
            if co.strand_typ == 'scaffold':
                stacks = tuple([
                    tuple([co.bases[0][0], co.bases[1][0]]),
                    tuple([co.bases[0][1], co.bases[1][1]])
                ])
                for stack in stacks:
                    if stack[0].across is None or stack[1].across is None:
                        continue
                    same_staple = (stack[0].across.strand
                                   == stack[1].across.strand)
                    sc = self.strands[stack[0].strand]
                    same_scaffold = (sc.id == stack[1].strand)
                    if same_staple and same_scaffold:
                        # NOTE: potentially (stack[0].residue -1) istead of tour(index)
                        sub_new = abs(sc.tour.index(stack[0])
                                      - sc.tour.index(stack[1])
                                      )
                        if sub_new > len(sc.tour) / 2:
                            sub_new = len(sc.tour) - sub_new
                        if sub_new < sub:
                            sub = sub_new

            else:  # staple
                for connection in co.bases:
                    if connection is None:  # NOTE: only 1 for half_co
                        continue
                    if connection[0].across is None or connection[1].across is None:
                        continue
                    sc = self.strands[connection[0].across.strand]
                    same_scaffold = (sc.id == connection[1].across.strand)
                    if same_scaffold:
                        base_1 = sc.tour.index(connection[0].across)
                        base_2 = sc.tour.index(connection[1].across)
                        sub_new = abs(base_1 - base_2)

                        if sub_new > len(sc.tour) / 2:
                            sub_new = len(sc.tour) - sub_new
                        if sub_new < sub:
                            sub = sub_new
            if not np.isinf(sub):
                loops.append(sub)

        return loops
