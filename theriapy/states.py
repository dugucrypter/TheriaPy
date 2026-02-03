from itertools import cycle
import pandas as pd
from pandas import DataFrame
import matplotlib as mpl
from matplotlib import pyplot as plt
from theriapy.bulk import name_ox_to_el, molar_mass, ratio_el_to_ox
from theriapy.df_tools import add_nosort

default_colors = mpl.rcParams['axes.prop_cycle'].by_key()['color']
color_cycle = cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])


def merge_preserving_order(lista, listb):
    seen = set()
    listc = []

    for x in lista:
        if x not in seen:
            listc.append(x)
            seen.add(x)

    for x in listb:
        if x not in seen:
            listc.append(x)
            seen.add(x)

    return listc


def assign_colors(list_cols, label_to_style, custom_cmap=None):
    """
    Ensures each label has a color in label_to_style
    """

    if label_to_style is None:
        label_to_style = {}
    if custom_cmap is None:
        custom_cmap = plt.get_cmap("tab20")
    if len(list_cols) > custom_cmap.N:
        raise Exception("The number of phase is above the available colors in cmap.")

    # existing colors already used
    used_colors = [
        style["color"]  #
        for style in label_to_style.values()
        if "color" in style.keys() and style["color"] is not None
    ]

    for label in list_cols:
        if label in label_to_style.keys() and label_to_style[label].get("color") is not None:
            continue
        for i in range(custom_cmap.N):
            color = custom_cmap(i)
            if color not in used_colors:
                break
        label_to_style[label] = {"color": color, }
        used_colors.append(color)
    return label_to_style


class States:
    def __init__(self, members=None):
        self.states = []
        self.list_current_elements = []
        self.list_all_elements = []
        self.members = None

    def add_state(self, state, list_elements):
        self.states.append(state)
        self.list_current_elements.append(list_elements)
        for el in list_elements:
            if el not in self.list_all_elements:
                self.list_all_elements.append(el)

    def set_members(self, members):
        self.members = members

    def print(self, verbose=True):
        for idx, st in self.states:
            print("Pressure", st.pressure, "Temperature", st.temperature)
            print([mineral.name for mineral in
                   [*st.mineral_assemblage, *st.fluid_assemblage]])

    @staticmethod
    def df_move_end(df, move_end_lists):
        for li in move_end_lists:
            for col_to_move in li:
                if col_to_move in df.columns:
                    df = df[[col for col in df.columns if col != col_to_move] + [col_to_move]]
        return df

    @staticmethod
    def df_move_front(df, move_front_lists):
        for li in move_front_lists:
            for col_to_move in li:
                if col_to_move in df.columns:
                    df = df[[col_to_move] + [col for col in df.columns if col != col_to_move]]
        return df

    def get_vols_df(self, normalize=False, normalize_to_solids=False, liq_phases=None):
        df = pd.DataFrame()
        list_phases = []
        for i in range(len(self.states)):
            st = self.states[i]
            for phase in st.mineral_assemblage:
                df.loc[i, phase.name] = phase.vol
                if phase.name not in list_phases:
                    list_phases.append(phase.name)
            for fluid in st.fluid_assemblage:
                df.loc[i, fluid.name] = fluid.vol
                if fluid.name not in list_phases:
                    list_phases.append(fluid.name)
        df = df.fillna(0)

        if normalize:
            if normalize_to_solids is True:
                phases_to_sum = [pha for pha in list_phases if pha not in liq_phases]
                sub_total = df[phases_to_sum].sum(axis=1)
                df_norm = df.div(sub_total, axis=0) * 100
                return df_norm
            else:
                df = df.div(df.sum(axis=1), axis=0) * 100
                return df
        return df

    def plot_path_stacked_volumes(self, valx, title=None, ignore=None, normalize=False, normalize_to_solids=False,
                                  liq_phases=None,
                                  xtitle="Phase volumes",
                                  shrink=None, shrink_part=0.95, ticks_style=None, nbins=12, cmap=None,
                                  move_front_lists=None, move_end_lists=None,
                                  label_to_style=None, return_polycols=False):
        if ignore is None:
            ignore = []
        if shrink is None:
            shrink = []
        move_front_lists = [] if move_front_lists is None else move_front_lists
        move_end_lists = [] if move_end_lists is None else move_end_lists

        xlabels = [str(e) for e in valx]

        df = self.get_vols_df(normalize=normalize, normalize_to_solids=normalize_to_solids, liq_phases=liq_phases)

        if self.members:
            # Merge end-members to their solution
            for sol, poles in self.members.items():
                # keep only poles that exist in df
                valid_poles = [p for p in poles if p in df.columns]
                if valid_poles:
                    if sol not in df.columns:
                        df[sol] = 0
                        # add the sum of poles to sol
                    df[sol] += df[valid_poles].sum(axis=1)
                    df = df.drop(columns=valid_poles)

            # Shrink fluid in diagram
            for solut in shrink:
                if solut in df.columns:
                    memb = df[solut].min()
                    df[solut] = df[solut] - memb * shrink_part

            df = df.drop(columns=ignore, errors="ignore")

        # Sort columns
        df = self.df_move_front(df, move_front_lists)
        df = self.df_move_end(df, move_end_lists)

        list_cols = list(df.columns)
        data = df.T.values.tolist()  # [row for row in df.values]

        # Colors
        label_to_style = assign_colors(
            list_cols=list_cols,
            label_to_style=label_to_style,
            custom_cmap=cmap  # None or a Colormap
        )
        colors = [label_to_style[lab]["color"] for lab in list_cols]

        # Plot stacked lines
        self.stack_fig, self.stack_ax = plt.subplots(figsize=(6, 4))
        self.stack_fig.canvas.manager.set_window_title(title)
        self.stack_ax.set_title(title)
        polycols = self.stack_ax.stackplot(xlabels, data, labels=list_cols, colors=colors, linewidth=0.5,
                                           edgecolor="face")

        # Ticks
        if ticks_style == 'vertical':
            self.stack_ax.tick_params(axis='x', labelrotation=90)
            self.stack_fig.subplots_adjust(bottom=0.145)
        elif ticks_style == 'adjust':
            nt = len(xlabels)
            if nt > nbins:
                step = 1 + nt // nbins
                self.stack_ax.set_xticks(xlabels)
                self.stack_ax.set_xticklabels(
                    [lab if i % step == 0 else "" for i, lab in enumerate(xlabels)]
                )

        # Plot customization
        self.stack_ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        if shrink:
            xtitle = xtitle + " - shrinked volumes :" + str(shrink)
        self.stack_ax.set_xlabel(xtitle)
        ytitle = "Vol (%)" if normalize else "Vol"
        self.stack_ax.set_ylabel(ytitle)
        self.stack_fig.subplots_adjust(right=0.84)
        self.stack_ax.margins(x=0)

        if return_polycols:
            return polycols, list_cols
        else:
            handle, label = self.stack_ax.get_legend_handles_labels()
            return df, handle, label

    def plot_path_phase_elts(self, phase, valx, title=None, ignore=['O', ], save=None, ticks_style=None,
                             with_fluids=False,
                             verbose=True):
        if ignore is None:
            ignore = []
        xlabels = [str(e) for e in valx]

        mol_df = DataFrame(columns=self.list_all_elements)
        for i in range(len(self.states)):
            state = self.states[i]
            not_stable = True
            for miner in state.mineral_assemblage:
                if phase == miner.name:
                    not_stable = False
                    if verbose:
                        print(list(zip(self.list_current_elements[i], miner.composition_moles)))
                    mol_df.loc[len(mol_df)] = dict(zip(self.list_current_elements[i], miner.composition_moles))
                    break
            if with_fluids:
                for fluid in state.fluid_assemblage:
                    if phase == fluid.name:
                        not_stable = False
                        if verbose:
                            print(list(zip(self.list_current_elements[i], fluid.composition_moles)))
                        mol_df.loc[len(mol_df)] = dict(zip(self.list_current_elements[i], fluid.composition_moles))
            if not_stable:
                mol_df.loc[len(mol_df)] = 0

        if isinstance(save, str):
            dfs = mol_df.copy()
            dfs.insert(0, "index", valx)
            dfs.to_csv(save)
            print("File saved at", save)

        # Plot lines
        if not title:
            title = "Elements in " + str(phase)
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.canvas.manager.set_window_title(title)
        ax.set_title(title)
        for col in mol_df.columns:
            if col not in ignore:
                ax.plot(xlabels, mol_df[col], marker="o", label=col)
        if ticks_style == 'vertical':
            ax.tick_params(axis='x', labelrotation=90)
            fig.subplots_adjust(bottom=0.145)
        elif ticks_style == 'adjust':
            nt = len(xlabels)
            if nt > 12:
                step = 1 + nt // 12
                ax.set_xticks(xlabels)
                ax.set_xticklabels(
                    [lab if i % step == 0 else "" for i, lab in enumerate(xlabels)]
                )

        # Plot customization
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        fig.subplots_adjust(right=0.84)

    def save_phases_vol(self, filepath):
        df = self.get_vols_df()
        df.T.to_excel(filepath, sheet_name="Vols")

    def get_phase_molar_comp(self, phase, verbose=0):
        df = pd.DataFrame(index=range(len(self.states)), )
        if verbose:
            print("Get phase molar comp :", phase)
        for i in range(len(self.states)):
            df.loc[i, 'index'] = i
            cols = self.list_current_elements[i]
            st = self.states[i]
            phase_names = [mineral.name for mineral in st.mineral_assemblage]
            if phase in phase_names:
                idx = phase_names.index(phase)
                vals = st.mineral_assemblage[idx].composition_moles
                df.loc[i, cols] = vals
            else:
                df.loc[i] = 0
        df.fillna(0)
        return df

    def get_phase_comp_oxides(self, phase, normalize=True):
        df = self.get_phase_molar_comp(phase)
        ox_df = pd.DataFrame()
        elt_cols = list(df.columns)
        elt_cols.remove('index')

        elt_cols_wo_O = elt_cols.copy()
        elt_cols_wo_O.remove('O')

        el_to_ox = {v: k for k, v in name_ox_to_el.items()}
        for elt in elt_cols_wo_O:
            ox_df[el_to_ox[elt]] = df[elt] * molar_mass[elt] / ratio_el_to_ox[elt]

        final_df = ox_df.fillna(0)  # copy and fillna
        if normalize:
            final_df = ox_df.div(ox_df.sum(axis=1), axis=0).mul(100)

        return final_df

    def get_solution_comp_oxides(self, solution, normalize=True):
        members = [memb for memb in list(self.members[solution]) if '_' in memb]
        mol_df = pd.DataFrame()
        for phase in members:
            df = self.get_phase_molar_comp(phase)
            df = df.drop(columns="index", errors="ignore")
            mol_df = add_nosort(mol_df, df)

        ox_df = pd.DataFrame()
        cols = list(mol_df.columns)
        cols.remove("O")
        el_to_ox = {v: k for k, v in name_ox_to_el.items()}
        for elt in cols:
            ox_df[el_to_ox[elt]] = mol_df[elt] * molar_mass[elt] / ratio_el_to_ox[elt]

        final_df = ox_df.copy()
        if normalize:
            final_df = ox_df.div(ox_df.sum(axis=1), axis=0).mul(100)

        return final_df
