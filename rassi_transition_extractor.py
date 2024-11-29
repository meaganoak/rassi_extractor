#!/usr/bin/env python

import argparse
import os
import re
import numpy as np

parser = argparse.ArgumentParser(description='Extract state energies and intensities')
parser.add_argument("file", help='OpenMolcas .out file containing RASSI intensities')
parser.add_argument('-n', '--nanometers', help='Calculate in nanometers, default is wavenumbers', action='store_true')
parser.add_argument('-t', '--types', nargs='+', choices=['velocity', 'length', 'total', 'dipole', 'complex'], default=['dipole'],
                    help='Specify the transition types to parse. Options: velocity, length, total, dipole, and complex. Default is dipole.')
args = parser.parse_args()

output_types = "_".join(args.types)  # Join selected types with underscores
output = f'Extracted_{os.path.splitext(os.path.basename(args.file))[0]}_{output_types}_Data.txt'

transition_type_map = {
    'velocity': '++ Velocity transition strengths (SO states):',
    'length': '++ Length and velocity gauge comparison (SO states):',
    'total': '++ Total transition strengths for the second-order expansion of the wave vector (SO states):',
    'dipole': '++ Dipole transition strengths (SO states):',
    'complex': '++ Complex transition dipole vectors (SO states):'
}

rassi_start = False
rassi_energies = []
parsing = False
intensities = []
energy_diff = []
dict1 = {}
dict2 = {}
Data = []

with open(args.file) as f:
    for line in f:
        # Check if the RASSI module is present
        if "Start Module: rassi" in line:
            date = ''
            parsing = False
            rassi_start = True
            line = line.split(maxsplit=5)
            line = line[-1]
            date = ' '.join(line.split(' ')[:-1])

        # If we are inside the RASSI section
        if rassi_start:
            states = [x for x in range(1, len(rassi_energies) + 1)]

            # Extract state energies
            if 'SO-RASSI' in line and 'Total energy' in line:
                line = " ".join(line.split()).replace('::', '')
                line = line.split(':')[-1].strip()
                rassi_energies.append(line)

            # Identify the start of the intensity data section for the transition type
            if any(transition_type_map[t] in line for t in args.types):
                parsing = True

            # Process intensity data
            if parsing:
                line = line.replace('below threshold', '0.00000000E-00')
                line = " ".join(line.split()) + '\n'
                intensities.append(line)

                # Check for end of the section
                if '++' in line and not any(transition_type_map[t] in line for t in args.types):
                    parsing = False


# Clean up
if intensities:
    intensities = [item for item in intensities if item.strip() != '']
    intensities = [item for item in intensities if "++" not in item]
    intensities = [item for item in intensities if "--" not in item and "for osc." not in item and "Einstein" not in item and "Re" not in item]

# Read intensity data into a numpy array
if 'complex' in args.types:
    int_arr = np.genfromtxt(
        intensities,
        dtype=None,
        delimiter=' ',
        usecols=(0, 1, 2, 3, 4, 5, 6, 7),
    )
    int_arr = np.column_stack([int_arr['f0'], int_arr['f1'], int_arr['f2'], int_arr['f3'], int_arr['f4'], int_arr['f5'], int_arr['f6'], int_arr['f7']])

else:
    int_arr = np.genfromtxt(
        intensities,
        dtype=None,
        delimiter=' ',
        usecols=(0, 1, 2)
    )
    int_arr = np.column_stack([int_arr['f0'], int_arr['f1'], int_arr['f2']])

rassi_E_dict = {state: energy for state, energy in zip(states, rassi_energies)}

# Calculate energy differences
units = 'nm' if args.nanometers else 'cm-1'
conversion_factor = 1 if args.nanometers else 10000000

if len(rassi_energies) != 0:
    key_list = list(rassi_E_dict)
    for x in rassi_E_dict:
        for y in rassi_E_dict:
            Difference = (float(rassi_E_dict[y]) - float(rassi_E_dict[x]))
            if int(x) < int(y) and int(x) < 10:
                wndiff = ((4.3597482E-18 * Difference / (6.62607015E-34 * 299792458)) / 100)
                nmdiff = (1 / wndiff) * conversion_factor if wndiff != 0 else 0
                evdiff = Difference * 27.211324570273
                energy_diff.append(f"{x} to {y}:{format(evdiff, '.8f')}")

# Populate dictionaries with extracted data
for x in range(np.shape(int_arr)[0]):
    key = f"{int(int_arr[x, 0])} to {int(int_arr[x, 1])}"
    dict1[key] = float(int_arr[x, 2])

for line in energy_diff:
    key, value = line.split(':')
    dict2[key] = float(value)

# Prepare data
if 'complex' in args.types:
    for row in int_arr:
        from_state, to_state, real_dx, imag_dx, real_dy, imag_dy, real_dz, imag_dz = row

        # Retrieve the energy difference from dict2
        energy_diff_value = dict2.get(f'{int(from_state)} to {int(to_state)}', 0)

        # Append formatted data
        Data.append(
            f"{int(from_state):<10} {int(to_state):<10} {energy_diff_value:<15.8f} "
            f"{real_dx:<15.8f} {imag_dx:<15.8f} "
            f"{real_dy:<15.8f} {imag_dy:<15.8f} "
            f"{real_dz:<15.8f} {imag_dz:<15.8f}"
        )
else:
    for key, value in dict1.items():
        if key in dict1 and key in dict2:
            from_state, to_state = key.split(' to ')
            Data.append(
                f"{from_state:<10} {to_state:<10} {dict2[key]:<15.8f} {value:<15.8f}"
            )

# Write to the output file
with open(output, 'w') as f_out:
    if 'complex' in args.types:
        f_out.write(
            f"{'Initial':<10} {'Final':<10} {'Energy (' + units + ')':<20} "
            f"{'Real_dx':<15} {'Imag_dx':<15} {'Real_dy':<15} {'Imag_dy':<15} {'Real_dz':<15} {'Imag_dz':<15}\n"
        )
    else:
        f_out.write(
            f"{'Initial':<10} {'Final':<10} {'Energy (' + units + ')':<20} {'Oscillator Strength':<20}\n"
        )
    for item in Data:
        f_out.write(item + '\n')

print(f"Data has been written to {output}")
