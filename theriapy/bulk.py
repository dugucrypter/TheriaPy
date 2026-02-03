import re
from collections import defaultdict
import numpy as np


name_ox_to_el = {
    'SiO2': 'SI',
    'TiO2': 'TI',
    'Al2O3': 'AL',
    'FeO': 'FE',
    'MnO': 'MN',
    'MgO': 'MG',
    'CaO': 'CA',
    'Na2O': 'NA',
    'K2O': 'K',
    'P2O5': 'P',
    'H2O' : 'H'
}

molar_mass = {
    "O" : 15.9994,
    "SI": 28.0855,
    "TI": 47.867,
    "AL": 26.98154,
    "FE": 55.845,
    "MG" : 24.305,
    "MN" : 54.93805,
    "CA" : 40.078,
    "NA" : 22.98977,
    "K" : 39.0983,
    "H" : 1.00794
}

ratio_el_to_ox = {
    "SI": 0.467434921,
    "TI": 0.599342898,
    "AL": 0.529250712,
    "FE": 0.777304842,
    "MG": 0.603035897,
    "MN": 0.774457638,
    "CA": 0.714690767,
    "NA": 0.741857476,
    "K": 0.830147777,
    "H": 0.111898344
}

def adjust_bulk_to_100(formula):
    # Extract elements and their values, keep "O(?)"
    elements = re.findall(r'([A-Z]{1,2})\(([\d.]+|\?)\)', formula)

    # Extract numeric values (ignore "O(?)")
    values = []
    current_sum = 0.0
    for element, value in elements:
        if value != '?':
            values.append(float(value))
            current_sum += float(value)
        else:
            values.append('?')  # Mark the position of "O(?)"

    # Apply the normalization factor to numeric values
    normalization_factor = 100 / current_sum
    normalized_values = [
        value * normalization_factor if value != '?' else '?'
        for value in values
    ]

    # Rebuild the string with normalized values, keep"O(?)"
    normalized_bulk = ''.join(
        f"{elements[i][0]}({normalized_values[i]:.3f})"
        if normalized_values[i] != '?'
        else f"{elements[i][0]}(?)"
        for i in range(len(elements))
    )

    print("result:", normalized_bulk)
    return normalized_bulk


def composition_dict_to_str(compo):
    compo_str = ""
    for key, val in compo.items():
        compo_str = compo_str + key + "(" + str(val) + ")"
    return compo_str


# From pytheriak example (02)
def bulk_from_compositionalvector(composition: list | np.ndarray, element_list: list | np.ndarray):
    bulk = ""
    for moles, element in zip(composition, element_list):
        bulk += element
        bulk += "(" + str(moles) + ")"
    return bulk


def bulk_to_oxides(bulk, normalize=True):
    d = defaultdict(float)

    for el, val in re.findall(r'([A-Z]+)\(([-+]?\d*\.?\d+)\)', bulk):
        d[el] += float(val)

    comp = dict(d)
    res = {}
    comp.pop("O")
    el_to_ox = {v: k for k, v in name_ox_to_el.items()}
    for elt in comp:
        res[el_to_ox[elt]] = comp[elt] * molar_mass[elt] / ratio_el_to_ox[elt]

    total = sum(res.values())
    if normalize :
        # Normalize to 100
        normalized = {k: v / total * 100 for k, v in res.items()}
        return normalized
    return total

