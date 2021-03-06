# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.

from plotly.graph_objs import Pie, Figure, Data
from plotly.offline import iplot

import remotespark.utils.configuration as conf


class PieGraph(object):
    @staticmethod
    def render(df, encoding, output):
        if encoding.x is None:
            with output:
                print("\n\n\nPlease select an X axis.")
                return

        values, labels = PieGraph._get_x_values_labels(df, encoding)
        max_slices_pie_graph = conf.max_slices_pie_graph()

        with output:
            # There's performance issues with a large amount of slices.
            # 1500 rows crash the browser.
            # 500 rows take ~15 s.
            # 100 rows is almost automatic.
            if len(values) > max_slices_pie_graph:
                print("There's {} values in your pie graph, which would render the graph unresponsive.\n"
                      "Please select another X with at most {} possible values."
                      .format(len(values), max_slices_pie_graph))
            else:
                data = [Pie(values=values, labels=labels)]

                fig = Figure(data=Data(data))
                iplot(fig, show_link=False)

    @staticmethod
    def display_logarithmic_x_axis():
        return False

    @staticmethod
    def display_logarithmic_y_axis():
        return False

    @staticmethod
    def display_x():
        return True

    @staticmethod
    def display_y():
        return False

    @staticmethod
    def _get_x_values_labels(df, encoding):
        series = df.groupby([encoding.x]).size()
        return series.values.tolist(), series.index.tolist()
