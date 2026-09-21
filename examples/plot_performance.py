from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    data = pd.read_csv(Path("equity.csv"), parse_dates=True, index_col=0).sort_index()
    fig = plt.figure()
    fig.patch.set_facecolor("white")

    ax1 = fig.add_subplot(311, ylabel="Portfolio value, %")
    data["equity_curve"].plot(ax=ax1, color="blue", lw=2.0)
    ax1.grid(True)

    ax2 = fig.add_subplot(312, ylabel="Period returns, %")
    data["returns"].plot(ax=ax2, color="black", lw=2.0)
    ax2.grid(True)

    ax3 = fig.add_subplot(313, ylabel="Drawdowns, %")
    data["drawdown"].plot(ax=ax3, color="red", lw=2.0)
    ax3.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
