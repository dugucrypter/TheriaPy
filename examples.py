import matplotlib.pyplot as plt
import numpy as np
from theriapy.containers import TheriakContainer
from theriapy.batch_plot import batch_plot_stacked_volumes

# Tested with Theriak-Domino v2025.06.05

# Bulk compositions
bulk0 = "SI(50.36)AL(30.54)FE(6.23)MG(2.46)CA(1.07)NA(4.62)K(4.73)O(?)H(2)"  # Metapelite TN205, De Capitani and Petrakakis 2010
bulk1 = "SI(65.44)AL(15.99)FE(4.97)MG(2.17)CA(4.25)NA(4.09)K(2.24)TI(0.78)O(?)H(6)"  # Random dacite
bulk2 = "SI(49.20)AL(16.70)FE(10.30)MG(5.40)CA(9.80)NA(3.10)K(0.70)TI(1.60)O(?)H(5)"  # Random basalt

# The database and theriak.ini files must be in the same folder as this script.
# Initialization (via pytheriak) requires:
# - the directory containing the Theriak-Domino executables
# - the database filename
# - the Theriak-Domino version
ther = TheriakContainer(programs_dir='path\to\Theriak-Domino\install\directory',
                        database='tcdb55c2d',
                        theriak_version='v2025.06.05'
                        )

# Number of steps along the P–T path
step_number = 15

# Pressure range: 4500–12000 bar
temps = np.linspace(520, 850, num=step_number).astype(int)

# Pressure graduating between 4500 and 8000 bars
press = np.linspace(4500, 12000, num=step_number).astype(int)

members_cfg = {
    "phen": ["PHNG_mu", "PHNG_pa", ],
    "bio": ["BIO_ann2", "BIO_obi", "BIO_east"],
    "chl": ["CHLR_daph", "CHLR_clin"],
    "opx": ["OPX_fm", "OPX_fs"],
    "omph": ["OMPH_di", "OMPH_jd", "OMPH_hed", "OMPH_om"],
    "pg": ["FSP_anc1", "FSP_abh"]
}

# Batch plot of phase volumes for multiple bulk compositions along the defined P–T path
batch_plot_stacked_volumes(ther,
                           bulks=[bulk0, bulk1, bulk2],
                           bulks_labels=["TN205", "Dacite", "Basalt"],
                           p_path=press, t_path=temps,
                           members_set=members_cfg,
                           normalize=True,
                           move_end_lists=[["pg", "quartz"]],
                           move_front_lists=[["LIQtc_h2oL"]]
                           )

# Compute the P–T path for bulk1 and extract the 95 % of the LIQtc solution composition at each step.
# Command added: removes 95% of the LIQtc component at every step.
states = ther.compute_ruled_pt_path(pressures=press,
                                    temps=temps,
                                    bulk=bulk1,
                                    command="remove_sol LIQtc_ 95",
                                    is_fluid=True) # if the phase to add/remove is a fluid

# Plot the element budgets of the LIQtc_h2oL solution along the path (vs temperature)
states.set_members(members_cfg)
states.plot_path_phase_elts("LIQtc_h2oL",
                            valx=temps,
                            with_fluids=True) # if the phase to show is a fluid

plt.show()