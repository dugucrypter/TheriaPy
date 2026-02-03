import re
from dataclasses import dataclass
import numpy as np
from pytheriak import wrapper
from theriapy.bulk import bulk_from_compositionalvector
from theriapy.states import States


@dataclass
class Command:
    order: str  # e.g. "remove"
    phase: str  # e.g. "LIQ_"
    percent: float  # e.g. 95


def parse_command(s: str) -> Command:
    # split on any non-alphanumeric/% and normalize to upper
    parts = [p for p in re.findall(r"[A-Za-z0-9_]+", s)]
    if len(parts) < 3:
        raise ValueError(f"Expected 3 tokens (order, fluid, percent), got: {parts}")
    order, phase, percent = parts[:3]
    return Command(order=order, phase=phase, percent=float(percent))


class TheriakContainer:
    def __init__(self, programs_dir, database, theriak_version):
        self.theriak = wrapper.TherCaller(programs_dir=programs_dir,
                                          database=database,
                                          theriak_version=theriak_version)

    def minimisation(self, pressure, temperature, bulk, return_failed_minimisation=True):
        rock, element_list = self.theriak.minimisation(int(pressure), int(temperature), bulk,
                                                       return_failed_minimisation=return_failed_minimisation)
        return rock, element_list

    def compute_pt_path(self, pressures, temps, bulks, verbose=1):

        if len(temps) != len(pressures):
            raise Exception("Temperature list and pressure list have different sizes")

        states = States()
        for i in range(len(temps)):
            rock, el_lis = self.minimisation(int(pressures[i]), int(temps[i]), bulks[i])
            states.add_state(rock, el_lis)
            if verbose:
                print(int(temps[i]), int(pressures[i]), ":", [mineral.name for mineral in rock.mineral_assemblage])

        return states

    def compute_ruled_pt_path(self, pressures, temps, bulk, command, is_fluid=False, verbose=1):

        if len(temps) != len(pressures):
            raise Exception("Temperature list and pressure list have different sizes")
        command = parse_command(command)

        states = States()
        current_bulk = bulk
        for i in range(len(temps)):
            rock, el_lis = self.minimisation(int(pressures[i]), int(temps[i]), current_bulk)
            states.add_state(rock, el_lis)

            # Update bulk
            mineral_names = [mineral.name for mineral in rock.mineral_assemblage]
            fluid_names = [fluid.name for fluid in rock.fluid_assemblage]
            current_bulk_arr = np.array(rock.bulk_composition_moles)
            if verbose:
                print("P :", int(pressures[i]), ", T :", int(temps[i]))
                print("Command :", command.order, command.phase, )

            # Check if an end-member of the solution exists
            if is_fluid :
                is_sol_stable = len([fluid for fluid in fluid_names if fluid.startswith(command.phase)]) > 0
            else :
                is_sol_stable = len([mineral for mineral in mineral_names if mineral.startswith(command.phase)]) > 0

            if not is_sol_stable:
                print("Phase not stable.")

            elif is_sol_stable and command.order == "add_sol":
                # Add a proportion of the solution
                if is_fluid :
                    sol_idx = fluid_names.index(
                        [fluid for fluid in fluid_names if fluid.startswith(command.phase)][0])
                    sol_moles = rock.fluid_assemblage[sol_idx].composition_moles
                else :
                    sol_idx = mineral_names.index(
                        [mineral for mineral in mineral_names if mineral.startswith(command.phase)][0])
                    sol_moles = rock.mineral_assemblage[sol_idx].composition_moles

                ratio = command.percent / 100.0
                new_bulk_arr = current_bulk_arr + [x * ratio for x in sol_moles]
                current_bulk = bulk_from_compositionalvector(new_bulk_arr, el_lis)
                if verbose:
                    print("New bulk composition : ", current_bulk)

            elif is_sol_stable and command.order == "remove_sol":
                if is_fluid:
                    sol_idx = fluid_names.index(
                        [fluid for fluid in fluid_names if fluid.startswith(command.phase)][0])
                    sol_moles = rock.fluid_assemblage[sol_idx].composition_moles
                else :
                    sol_idx = mineral_names.index(
                        [mineral for mineral in mineral_names if mineral.startswith(command.phase)][0])
                    sol_moles = rock.mineral_assemblage[sol_idx].composition_moles
                ratio = command.percent / 100.0
                new_bulk_arr = current_bulk_arr - [x * ratio for x in sol_moles]
                current_bulk = bulk_from_compositionalvector(new_bulk_arr, el_lis)
                if verbose:
                    print("New bulk composition : ", current_bulk)

        return states

    def find_phase_apparition_temp(self, bulk, pressure, phase, tmin=0, tmax=1200, tol=1, verbose=0):

        found_temp = None

        while (tmax - tmin) > tol:
            if verbose:
                print("Interval reduced to ", tmin, "-", tmax, "°C")
            tmid = (tmin + tmax) // 2  # integer midpoint
            rock, element_list = self.minimisation(pressure, tmid, bulk, True)
            phase_names = [ph.name for ph in rock.mineral_assemblage]
            if phase in phase_names:
                # Phase appears → search in lower interval
                found_temp = tmid
                if verbose:
                    print("Phase stable at T =", tmid)
                tmax = tmid
            else:
                if verbose:
                    print("Phase not stable at T = ", tmid)
                # Phase absent → search within a smaller range
                tmin = tmid

        # Ensure we return an int
        return int(found_temp) if found_temp is not None else int(tmax)

    def get_fluid(self, bulk, pressure, temperature, fluid):
        rock, element_list = self.theriak.minimisation(pressure, temperature, bulk, return_failed_minimisation=True)
        fluid_names = [fluid.name for fluid in rock.fluid_assemblage]
        if fluid in fluid_names:
            index = fluid_names.index(fluid)
            return rock.fluid_assemblage[index], element_list

    def get_rock_volume(self, bulk, temperature, pressure, fluids_in=True):
        rock, element_list = self.theriak.minimisation(pressure, temperature, bulk, return_failed_minimisation=True)
        vol = 0
        for mineral in rock.mineral_assemblage:
            vol = vol + mineral.vol
        if fluids_in:
            for fluid in rock.fluid_assemblage:
                vol = vol + fluid.vol
        return vol


class RockContainer:
    def __init__(self, rock, list_elements):
        self.rock = rock
        self.list_elements = list_elements
        self.mineral_names = [mineral.name for mineral in rock.mineral_assemblage]
        self.mineral_index = {el: i for i, el in enumerate(self.mineral_names)}
        self.mineral_modes = [mineral.vol_percent for mineral in rock.mineral_assemblage]
        self.mineral_composition_apfu = [mineral.composition_apfu for mineral in rock.mineral_assemblage]
