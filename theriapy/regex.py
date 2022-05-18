import re

#https://stackoverflow.com/questions/47982949/how-to-parse-complex-text-files-using-python
def list_numbers_in_line(line):
    numbers = re.findall('([0-9]+\.[0-9]+)[^w_-]', line)
    list_numbers = [float(i) for i in numbers]
    return list_numbers

def names_in_line(line):
    p = re.compile('(\w*[a-zA-Z:_-]+\.*\w*)')
    matches = p.search(line)
    return matches

def elts_in_header(line):
    res = re.findall('  ([A-Z]+)  ', line)
    matches = [e for e in res]
    return matches


class RegExFinder:
    _reg_vols_dens = re.compile(' (volumes and densities of stable phases:)')
    _h2o_stable_phases = re.compile(' (H2O content of stable phases:)')
    _ref_elts_in_phases = re.compile(' (elements in stable phases:)')

    def __init__(self, line):
        self.volumes_densities = self._reg_vols_dens.match(line)
        self.h2o_content = self._h2o_stable_phases.match(line)
        self.elements_in_phases = self._ref_elts_in_phases.match(line)
