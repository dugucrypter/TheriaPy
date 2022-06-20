import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from theriapy.theriapy import Theriapy

# Tested with Theriak-Domino v11.03.2020

# Bulk composition, TN205, De Capitani and Petrakakis 2010
compo = {
    "SI": 50.36,
    "AL": 30.54,
    "FE": 6.23,
    "MG": 2.46,
    "CA": 1.07,
    "NA": 4.62,
    "K": 4.73,
    "O": 160.965 + 30,  # +30 (O) for 60 (H)
    "H": 60
}

# Initialization with the directory of Theriak-Domino programs and the working directory (which contains THERIN and databases).
thepy = Theriapy(therdom_dir='path\to\Theriak-Domino\install\directory',
                 working_dir="path\to\working\directory",
                 db="Jun92d.bs", execution_time=1, verbose=True, show_output=False)

# Number of steps
step_number = 20

# Temperature graduating between 520 and 620 °C
temps = np.linspace(520, 620, num=step_number).astype(int)

# Pressure graduating between 4500 and 17000 bars
press = np.linspace(4500, 17000, num=step_number).astype(int)

# --- Some configs for matplotlib plotting
# --- A dictionary to store volumes data for graphic plotting
res_vol = {}

# --- The variable containing volume in the return data
var_volume = "volume[ccm]"

# --- Phases to ignore as volume
to_ignore = ["Total", "STEAM", "water", "H", "O", "HYDROGEN"]


# Calculation loop for each step, with different T and P values
for i in range(step_number):
    # Return tables of volumes and densities; H2O in stable phases; elements in stable phases
    data_vol_d, data_h2o_compo, data_compo = thepy.compute_step(compo, temps[i], press[i])

    # From here, bulk composition can be modified for the next iteration.
    # This modification can be done according to the existing phases and
    # their composition, that are available from the variables data_vol_d,
    # data_h2o_compo, data_compo

    # --- Here, we organize volumes data for matplotlib plotting

    # --- Building a dataFrame
    df_vol = pd.DataFrame(data_vol_d)
    df_vol.columns = df_vol.iloc[0]
    df_vol = df_vol.loc[1:, ["Phase", var_volume]]

    for ind in df_vol.index:
        phase, val = df_vol['Phase'][ind], df_vol[var_volume][ind]
        if phase in res_vol.keys():
            if val != 0:
                res_vol[phase].append(val)
            else:
                res_vol[phase].append(0)
        elif phase not in to_ignore:
            if val != 0:
                res_vol[phase] = [0] * i
                res_vol[phase].append(val)
            else:
                res_vol[phase] = [0] * (i + 1)
print("End of the loop.")


# --- Complete missing values in res_vol dataFrame
for key, val in res_vol.items():
    if len(val) < step_number:
        rest = [0] * (step_number - len(val))
        val.extend(rest)
        res_vol[key] = val

# --- Normalize volumes to 100
NORM = True
if NORM:
    for i in range(step_number):
        total = sum([res_vol[key][i] for key in res_vol.keys()])
        for key in res_vol.keys():
            res_vol[key][i] = 100 * res_vol[key][i] / total

# --- Plotting
fig, ax = plt.subplots()
lx = temps
vals = []
labels = []

for key, val in res_vol.items():
    vals.append(val)
    labels.append(key)
ax.stackplot(lx, *vals, labels=labels)
ax.set_xlabel("Temperatures")
ax.set_ylabel("Vol (%)")
fig.legend()

plt.show()
