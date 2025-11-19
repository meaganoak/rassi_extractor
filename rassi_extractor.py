import re
import os
import argparse

def extract_energy_data_from_output(output_file):
    energy_data = {}
    with open(output_file, 'r') as file:
        capture_energy = False
        for line in file:
            # Start of SO energy table
            if re.match(r"^\s*SO\s+State", line):
                capture_energy = True
                continue

            # End of SO energy table
            if "Weights of the five most important spin-orbit-free states" in line:
                break

            if capture_energy:
                parts = line.split()

                # skip empty lines
                if not parts:
                    continue

                # only lines starting with a state number
                if not parts[0].isdigit():
                    continue

                try:
                    state = int(parts[0])
                    # Column 3 is cm^-1, based on your file
                    energy_cm1 = float(parts[3])
                    energy_data[state] = energy_cm1
                except (ValueError, IndexError):
                    continue

    return energy_data

def convert_energy(value_eV, unit="eV"):
    if unit == "eV":
        return value_eV
    elif unit == "cm-1":
        return value_eV * 8065.54429
    else:
        raise ValueError(f"Unsupported energy unit: {unit}")


def detect_degeneracy(energy_data, threshold=0.0):
    """Return True if SO states 1 and 2 are degenerate within threshold (cm-1)."""
    if 1 in energy_data and 2 in energy_data:
        return abs(energy_data[2] - energy_data[1]) <= threshold
    return False


def extract_transition_data_from_output(output_file):
    transitions = []
    with open(output_file, 'r') as file:
        capture_transition = False
        for line in file:
            if "Dipole transition strengths (SO states)" in line:
                capture_transition = True
                continue
            if "Velocity transition strengths (SO states)" in line:
                break
            if capture_transition:
                parts = line.split()
                if len(parts) >= 7 and parts[0].isdigit() and parts[1].isdigit():
                    try:
                        state_from = int(parts[0])
                        state_to   = int(parts[1])
                        osc_strength = float(parts[2])
                        ax = float(parts[3])
                        ay = float(parts[4])
                        az = float(parts[5])
                        total_a = float(parts[6])
                        transitions.append(
                            (state_from, state_to, osc_strength, ax, ay, az, total_a)
                        )
                    except ValueError:
                        pass
    return transitions


def map_transitions(energy_data, transitions, output_file, trunc=False, trunc_states=None, unit="eV"):
    with open(output_file, 'w') as file:
        file.write(
            "State From   State To   Energy Difference {(unit})   "
            "Osc. Strength       Ax (sec-1)        Ay (sec-1)        "
            "Az (sec-1)        Total A (sec-1)\n"
        )

        if not trunc:
            to_process = transitions
        else:
            to_process = [t for t in transitions if t[0] in trunc_states]

        for state_from, state_to, osc_strength, ax, ay, az, total_a in to_process:
            if state_from in energy_data and state_to in energy_data:
                energy_diff_eV = energy_data[state_to] - energy_data[state_from]
                energy_diff = convert_energy(energy_diff_eV, unit)
                file.write(
                    f"{state_from:<12}{state_to:<12}"
                    f"{energy_diff:<28.2f}"
                    f"{osc_strength:<18.8E}"
                    f"{ax:<18.8E}"
                    f"{ay:<18.8E}"
                    f"{az:<18.8E}"
                    f"{total_a:<18.8E}\n"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Extract energy & transition data from OpenMolcas output; "
                    "produce full and (optionally) truncated tables."
    )
    parser.add_argument("output_file", help="Path to the OpenMolcas output file")
    parser.add_argument(
        "--trunc", action="store_true",
        help="Write truncated file with transitions from state 1, "
             "or states 1 and 2 if degenerate"
    )
    parser.add_argument(
    "--units", choices=["eV", "cm-1"], default="eV",
    help="Units for energy output tables: eV (default), or cm-1"
    )
    args = parser.parse_args()

    base = os.path.splitext(os.path.basename(args.output_file))[0]
    full_out = f"{base}_extracted_data.txt"
    trunc_out = f"{base}_extracted_data_trunc.txt"

    energy_data = extract_energy_data_from_output(args.output_file)
    transitions = extract_transition_data_from_output(args.output_file)

    # Full mapping
    map_transitions(energy_data, transitions, full_out, trunc=False)
    print(f"Full mapped transitions saved to {full_out}")

    # Truncated mapping
    if args.trunc:
        degenerate = detect_degeneracy(energy_data, threshold=0.0)

        if degenerate:
            trunc_states = [1, 2]
            print("Degeneracy detected: including transitions from states 1 AND 2.")
        else:
            trunc_states = [1]

        map_transitions(energy_data, transitions, trunc_out, trunc=True, trunc_states=trunc_states, unit=args.units)
        print(f"Truncated transitions saved to {trunc_out}")


if __name__ == "__main__":
    main()

