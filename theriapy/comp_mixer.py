import pandas as pd


def prepare_df(df, index='Phase'):
    n_df = pd.DataFrame(df)
    n_df.columns = n_df.iloc[0]
    n_df = n_df[1:]
    n_df.set_index(index, inplace=True)
    return n_df


def remove_phase(phase, compo, prop, data_comp):
    df_comp = prepare_df(data_comp)
    new_comp = compo.copy()
    extracted_comp = {}
    if phase in df_comp.index:
        for elt in df_comp.columns:
            if elt not in ('E',):
                extracted_comp[elt] = prop * df_comp[elt][phase]
                new_comp[elt] = max(0, compo[elt] - prop * df_comp[elt][phase])

    return new_comp, extracted_comp


def remove_solution(solution, compo, prop, data_comp):
    df_comp = prepare_df(data_comp)
    new_comp = compo.copy()
    extracted_comp = {}
    for name in df_comp.index:
        if name.find(solution) != -1:
            for elt in df_comp.columns:
                if elt not in ('E',):
                    extracted_comp[elt] = prop * df_comp[elt][name]
                    new_comp[elt] = max(0, compo[elt] - prop * df_comp[elt][name])
    return new_comp, extracted_comp


def add_phase(phase, compo, prop, data_comp):
    return remove_phase(phase, compo, -prop, data_comp)


def add_solution(phase, compo, prop, data_comp):
    return remove_solution(phase, compo, -prop, data_comp)


def phase_threshold_vol(phase, compo, limit, data_vol_d, data_comp):
    df_vol_d = prepare_df(data_vol_d)

    if phase in df_vol_d.index:
        vol_phase = df_vol_d['volume[ccm]'][phase]
        vol_total = df_vol_d['volume[ccm]'].sum() - df_vol_d['volume[ccm]']["Total"]
        vol_without_phase = df_vol_d['volume[ccm]'].sum() - df_vol_d['volume[ccm]']["Total"] - vol_phase
        part_phase = vol_phase / vol_total

        if part_phase > limit:
            vol_extracted = vol_phase - limit * vol_without_phase / (1 - limit)
            new_comp, resid = remove_phase(phase, compo, vol_extracted / vol_phase, data_comp)
            return new_comp

    return compo


def sum_compositions(*lcompos):
    sum_compo = {}
    elts = []

    for compo in lcompos:
        for elt in compo.keys():
            if elt in elts:
                sum_compo[elt] = sum_compo[elt] + compo[elt]
            else:
                sum_compo[elt] = compo[elt]
                elts.append(elt)

    return sum_compo


def remove_composition(compo_a, compo_b):
    subs_comp = compo_a.copy()
    elts_a = compo_a.keys()

    for elt in compo_b.keys():
        if elt in elts_a:
            subs_comp[elt] = max(0, compo_a[elt] - compo_b[elt])

    return subs_comp
