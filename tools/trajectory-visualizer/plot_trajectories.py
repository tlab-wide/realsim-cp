import os
import glob
import argparse
import pandas as pd
import matplotlib.pyplot as plt


def load_trajectories(folder):
    """
    Load all CSV files and use ONLY the first 3 columns:
    timestamp, pos_x, pos_y (by column order, not name).
    """
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))

    if not files:
        raise FileNotFoundError(f"No CSV files found in {folder}")

    trajectories = []

    for i, file in enumerate(files):
        # Read only first 3 columns by position
        df = pd.read_csv(file, usecols=[0, 1, 2])

        # Force column names for safety
        df.columns = ["timestamp", "pos_x", "pos_y"]

        trajectories.append((i + 1, os.path.basename(file), df))

    return trajectories


def plot_all_trajectories(trajectories):
    """
    Plot ALL trajectories in one single figure.
    """
    plt.figure(figsize=(10, 8))
    cmap = plt.cm.get_cmap("tab10", len(trajectories))

    for index, name, df in trajectories:
        plt.plot(
            df["pos_x"],
            df["pos_y"],
            color=cmap(index - 1),
            linewidth=1.5,
            label=f"{index}: {name}"
        )

    plt.xlabel("pos_x")
    plt.ylabel("pos_y")
    plt.title("All Vehicle Trajectories (Single Figure)")
    plt.legend(fontsize=8)
    plt.grid(True)
    plt.axis("equal")
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Plot all vehicle trajectories in ONE figure")
    parser.add_argument(
        "--folder",
        "-f",
        required=True,
        help="Folder containing the CSV trajectory files"
    )

    args = parser.parse_args()

    trajectories = load_trajectories(args.folder)
    plot_all_trajectories(trajectories)


if __name__ == "__main__":
    main()
