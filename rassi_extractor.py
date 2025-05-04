import re
import os
import argparse

def extract_energy_data_from_output(output_file):
    energy_data = {}
    with open(output_file, 'r') as file:
        capture_energy = False
        for line in file:
            if re.match(r"^\s*SO\s+State", line):
                capture_energy = True
                continue
            if "Weights of the five most important spin-orbit-free states" in line:
                break
            if capture_energy:
                parts = line.split()
                if len(parts) >= 4 and parts[0].isdigit():
                    try:
                        state = int(parts[0])
                        energy_cm1 = float(parts[3])
                        energy_data[state] = energy_cm1
                    except ValueError:
                        pass
    return energy_data

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
                        transitions.append((state_from, state_to, osc_strength, ax, ay, az, total_a))
                    except ValueError:
                        pass
    return transitions

def map_transitions(energy_data, transitions, output_file, trunc=False):
    with open(output_file, 'w') as file:
        file.write(
            "State From   State To   Energy Difference (cm⁻¹)   "
            "Osc. Strength       Ax (sec⁻¹)        Ay (sec⁻¹)        "
            "Az (sec⁻¹)        Total A (sec⁻¹)\n"
        )
        # If truncating, only keep transitions where state_from == 1
        to_process = transitions if not trunc else [t for t in transitions if t[0] == 1]
        for state_from, state_to, osc_strength, ax, ay, az, total_a in to_process:
            if state_from in energy_data and state_to in energy_data:
                energy_diff = energy_data[state_to] - energy_data[state_from]
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
        help="Also write a truncated file with only From-state=1 transitions"
    )
    args = parser.parse_args()

    base = os.path.splitext(os.path.basename(args.output_file))[0]
    full_out = f"{base}_extracted_data.txt"
    trunc_out = f"{base}_extracted_data_trunc.txt"

    energy_data = extract_energy_data_from_output(args.output_file)
    transitions = extract_transition_data_from_output(args.output_file)

    map_transitions(energy_data, transitions, full_out, trunc=False)
    print(f"Full mapped transitions saved to {full_out}")

    # truncated table of just transitions from the GS
    if args.trunc:
        map_transitions(energy_data, transitions, trunc_out, trunc=True)
        print(f"Truncated (From=1) transitions saved to {trunc_out}")

if __name__ == "__main__":
    main()
