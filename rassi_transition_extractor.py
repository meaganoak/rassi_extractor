#! /usr/bin/env python

import argparse
import os
import re
import numpy as np

parser = argparse.ArgumentParser(
    description='Extract state energies and intensities')
parser.add_argument("file",
                    help='OpenMolcas .out file containing RASSI intensities')
parser.add_argument('-n', '--nanometers',
                    help='Calculate in nanometers, default is wavenumbers',
                    action='store_true')
args = parser.parse_args()  # Parse command line arguments


# Define output file name based on the input file name
output = 'Extracted_{}_Data.txt'.format(os.path.splitext(str(args.file))[0])

#Initialize variables
rassi_start = False
rassi_energies = []  # List to store energies
parsing = False
intensities = []  # List to store intensities
energy_diff = []  # List to store energy differences
dict1 = {}  # Dictionary to store intensities
dict2 = {}  # Dictionary to store energy differences
Data = []  # List to store final data

# Open the specified file for reading
with open(args.file) as f:
    for line in f:
        # Check if the RASSI module is present
        if "Start Module: rassi" in line:
            date = ''
            parsing = False
            rassi_start = True
            line = line.split(maxsplit=5)
            line = line[-1]
            date = ' '.join(line.split(' ')[:-1])  # Extract date

        # If we are inside the RASSI section
        if rassi_start:
            states = [x for x in range(1, len(rassi_energies) + 1)]  # Create state list
            # Extract state energies from the relevant line
            if 'SO-RASSI' in line and 'Total energy' in line:
                line = " ".join(line.split()).replace('::', '')  # Clean up line
                line = line.split(':')[-1].strip()  # Get energy value
                rassi_energies.append(line)  # Append energy to the list

#print("Final RASSI energies:", rassi_energies)

            # Identify the start of the intensity data section
            if '++ Velocity transition strengths (SO states)' in line:
                parsing = True

            # Process intensity data
            if parsing:
                line = line.replace('below threshold', '0.00000000E-00')  # Replace threshold indicator
                line = " ".join(line.split()) + '\n'  # Clean up line
                intensities.append(line)  # Append line to intensities list

                # Check if we have reached the next "++" string (marking the end of the section)
                if '++ Length and velocity gauge comparison (SO states)' in line:  # Check if "++" is encountered
                    parsing = False  # End parsing when we reach the second "++"



#Process intensities if any have been added
                if intensities:
                    intensities = [item for item in intensities if item.strip() != '']  # Remove empty lines
                    intensities = [item for item in intensities if "++" not in item]  # Remove the "++" markers
                    intensities = [item for item in intensities if "--" not in item and "for osc." not in item and "Einstein" not in item]  # Filter out unwanted lines

# Print the final RASSI intensities after processing the whole file
#print("Final RASSI intensities:", intensities)

    # Read intensity data into a numpy array
    int_arr = np.genfromtxt(
        intensities,
        dtype=None,
        delimiter=' ',
        usecols=(0, 1, 4)  # Extract specific columns
    )

    # Stack the columns into a single array for easier processing
    int_arr = np.column_stack([int_arr['f0'],
                               int_arr['f1'],
                               int_arr['f2']])
            

                # Create a dictionary for the extracted energies
    rassi_E_dict = {
        state: energy
        for state, energy
        in zip(states, rassi_energies)
    }

                # Calculate differences in energy
    if args.nanometers:
        units = 'nm'
        if len(rassi_energies) != 0:
            key_list = [key for key in rassi_E_dict]
            ground_state = int(key_list[0])
            for x in rassi_E_dict:
                for y in rassi_E_dict:
                    Difference = (
                        float(rassi_E_dict[y])
                        - float(rassi_E_dict[x])
                    )

                    if int(x) < int(y) and int(x) < 10:
                        wndiff = (
                            (4.3597482E-18 * Difference
                             / (6.62607015E-34 * 299792458))
                            / 100
                        )

                        if wndiff == 0:
                            nmdiff = 0
                        else:
                            nmdiff = (1 / wndiff) * 10000000
                        energy_diff.append(
                            str(x)
                            + ' to '
                            + str(y)
                            + ':'
                            + str(format(nmdiff, '.8f'))
                        )

    else:
        units = 'cm-1'
        if len(rassi_energies) != 0:
            key_list = [key for key in rassi_E_dict]
            ground_state = int(key_list[0])
            for x in rassi_E_dict:
                for y in rassi_E_dict:
                    Difference = (
                        float(rassi_E_dict[y])
                        - float(rassi_E_dict[x])
                    )

                    if int(x) < int(y) and int(x) < 10:
                        wndiff = (
                            (4.3597482E-18 * Difference
                             / (6.62607015E-34 * 299792458))
                            / 100
                        )

                        energy_diff.append(
                            str(x)
                            + ' to '
                            + str(y)
                            + ':'
                            + str(format(wndiff, '.8f'))
                        )

            # Check for any missing data and update section status
            if (len(rassi_energies) == 0 or len(intensities) == 0):
                rassi_sections.update({date: 'failed'})
            else:
                # Populate dictionaries with extracted data
                for x in range(np.shape(int_arr)[0]):
                    key = (
                        str(int(int_arr[x, 0]))
                        + ' to '
                        + str(int(int_arr[x, 1]))
                    )

                    value = int_arr[x, 2]  # Extract intensity value
                    dict1[key] = float(value)  # Store intensity

                for line in energy_diff:
                    key, value = line.split(':')
                    dict2[key] = float(value)  # Store energy difference

                # Prepare data for output
                for key, value in dict1.items():
                    if key in dict1 and key in dict2:
                        Data.append(
                            str(dict2[key])
                            + '      '
                            + str(dict1[key])
                            + '     '
                            )

# Write the final Data list to the output file
with open(output, 'w') as f_out:
#    f_out.write("Fr State  To State  Energy (" + units + ")   Oscillator Strength\n")
    f_out.write("Energy (" + units + ")   Oscillator Strength\n")
    for item in Data:
        f_out.write(item + '\n')  # Write each entry followed by a newline

print(f"Data has been written to {output}")
