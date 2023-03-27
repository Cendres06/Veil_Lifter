#Visuel pour 23 éléments ok
#à améliorer pour les 170 éléments que j'ai (choisir les 20+ fréquents ?)

"""
===============================================
Creating a timeline with lines, dates, and text
===============================================

How to create a simple timeline.

Timelines can be created with a collection of dates and text.

https://matplotlib.org/stable/gallery/lines_bars_and_markers/timeline.html
"""

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates

##############################################################################
# Next, we'll create a stem plot with some variation in levels as to
# distinguish even close-by events. We add markers on the baseline for visual
# emphasis on the one-dimensional nature of the time line.
#
# For each event, we add a text label via `~.Axes.annotate`, which is offset
# in units of points from the tip of the event line.
#
# Note that Matplotlib will automatically plot datetime inputs.

def plot_timeline(names,dates,title="Origine des entités nommées",names_difference=False):
    # Choose some nice levels
    levels = np.tile([-5, 5,-3, 3, -1, 1],
                    int(np.ceil(len(dates)/6)))[:len(dates)]

    # Create figure and plot a stem plot with the date
    fig, ax = plt.subplots(figsize=(8.8, 4), constrained_layout=True)
    ax.set(title=title)

    ax.vlines(dates, 0, levels, color="tab:red",linestyles='dotted')  # The vertical stems.
    ax.plot(dates, np.zeros_like(dates), "-o",
            color="k", markerfacecolor="w")  # Baseline and markers on it.

    # annotate lines
    for d, l, r in zip(dates, levels, names):
        color='black'
        if names_difference and r in names_difference:
            color='red'
        ax.annotate(r, xy=(d, l),
                    xytext=(-3, np.sign(l)*3), textcoords="offset points",
                    color=color,
                    horizontalalignment="right",
                    verticalalignment="bottom" if l > 0 else "top")

    # format xaxis with 4 month intervals
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    # remove y axis and spines
    ax.yaxis.set_visible(False)
    ax.spines[["left", "top", "right"]].set_visible(False)

    ax.margins(y=0.1)
    plt.show()


#############################################################################
#
# .. admonition:: References
#
#    The use of the following functions, methods, classes and modules is shown
#    in this example:
#
#    - `matplotlib.axes.Axes.annotate`
#    - `matplotlib.axes.Axes.vlines`
#    - `matplotlib.axis.Axis.set_major_locator`
#    - `matplotlib.axis.Axis.set_major_formatter`
#    - `matplotlib.dates.MonthLocator`
#    - `matplotlib.dates.DateFormatter`
