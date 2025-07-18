#  Copyright 2022 Feedzai
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import pandas as pd
import numpy as np
import copy
import altair as alt
from timeshap.plot.utils import multi_plot_wrapper


def plot_feat_barplot(feat_data: pd.DataFrame,
                      top_x_feats: int = 15,
                      plot_features: dict = None
                      ):
    """Plots local feature explanations

    Parameters
    ----------
    feat_data: pd.DataFrame
        Feature explanations

    top_x_feats: int
        The number of feature to display.

    plot_features: dict
        Dict containing mapping between model features and display features
    """
    feat_data = copy.deepcopy(feat_data)
    if plot_features:
        plot_features['Pruned Events'] = 'Pruned Events'
        print(feat_data)
        print(plot_features)
        feat_data['Feature'] = feat_data['Feature'].apply(lambda x: plot_features[x])

    feat_data['sort_col'] = feat_data['Shapley Value'].apply(lambda x: abs(x))

    if top_x_feats is not None and feat_data.shape[0] > top_x_feats:
        sorted_df = feat_data.sort_values('sort_col', ascending=False)
        cutoff_contribution = abs(sorted_df.iloc[4]['Shapley Value'])
        feat_data = feat_data[np.logical_or(feat_data['Explanation'] >= cutoff_contribution, feat_data['Explanation'] <= -cutoff_contribution)]

    a = alt.Chart(feat_data).mark_bar(size=15, thickness=1).encode(
        y=alt.Y("Feature", axis=alt.Axis(title="Feature", labelFontSize=15,
                                         titleFontSize=15, titleX=-61),
                sort=alt.SortField(field='sort_col', order='descending')),
        x=alt.X('Shapley Value', axis=alt.Axis(grid=True, title="Shapley Value",
                                            labelFontSize=15, titleFontSize=15),
                scale=alt.Scale(domain=[-0.1, 0.4])),
    )

    line = alt.Chart(pd.DataFrame({'x': [0]})).mark_rule(
        color='#798184').encode(x='x')

    feature_plot = (a + line).properties(
        width=190,
        height=225
    )
    return feature_plot


def plot_global_feat(feat_data: pd.DataFrame,
                     top_x_feats: int = 12,
                     threshold: float = None,
                     plot_features: dict = None,
                     plot_parameters: dict = None,
                     **kwargs
                     ):
    """ Plots global feature plots

    Parameters
    ----------
    feat_data: pd.DataFrame
        Feature explanations to plot

    top_x_feats: int
        The number of feature to display.

    threshold: float
        The minimum absolute importance that a feature needs to have to be displayed

    plot_features: dict
        Dict containing mapping between model features and display features

    plot_parameters: dict
        Dict containing optional plot parameters
            'height': height of the plot, default 280
            'width': width of the plot, default 288
            'axis_lims': plot Y domain, default [-0.2, 0.6]
            'FontSize': plot font size, default 13
    """
    def plot(feat_data, top_x_feats, threshold, plot_features, plot_parameters):
        avg_df = feat_data.groupby('Feature').mean()['Shapley Value']
        if threshold is None and len(avg_df) >= top_x_feats:
            sorted_series = avg_df.abs().sort_values(ascending=False)
            threshold = sorted_series.iloc[top_x_feats-1]
        if threshold:
            avg_df = avg_df[np.logical_or(avg_df <= -threshold, avg_df >= threshold)]
        feat_data = feat_data[feat_data['Feature'].isin(avg_df.index)][['Shapley Value', 'Feature']]

        if threshold:
            # Related to issue #43; credit to @edpclau
            avg_df = pd.concat([avg_df, pd.Series([0], index=['(...)'])],axis=0)
            feat_data = pd.concat([feat_data,
                                   pd.DataFrame({'Feature': '(...)',
                                                 'Shapley Value': -0.6, },
                                                index=[0])], ignore_index=True, axis=0)

        feat_data['type'] = 'Shapley Value'

        for index, value in avg_df.items():
            if index == '(...)':
                # Related to issue #43; credit to @edpclau
                feat_data = pd.concat([feat_data,
                                       pd.DataFrame({'Feature': index,
                                                     'Shapley Value': None,
                                                     'type': 'Mean'},
                                                    index=[0])],
                                      ignore_index=True,
                                      axis=0)
            else:
                # Related to issue #43; credit to @edpclau
                feat_data = pd.concat([feat_data,
                                       pd.DataFrame({'Feature': index,
                                                     'Shapley Value': value,
                                                     'type': 'Mean'},
                                                    index=[0])],
                                      ignore_index=True,
                                      axis=0)

        sort_features = list(avg_df.sort_values(ascending=False).index)
        if plot_features:
            plot_features = copy.deepcopy(plot_features)
            plot_features['Pruned Events'] = 'Pruned Events'
            plot_features['(...)'] = '(...)'
            feat_data['Feature'] = feat_data['Feature'].apply(lambda x: plot_features[x])
            sort_features = [plot_features[x] for x in sort_features]

        if plot_parameters is None:
            plot_parameters = {}
        height = plot_parameters.get('height', 280)
        width = plot_parameters.get('width', 288)
        axis_lims = plot_parameters.get('axis_lim', [-0.2, 0.6])
        fontsize = plot_parameters.get('FontSize', 13)

        global_feats_plot = alt.Chart(feat_data).mark_point(stroke='white',
                                                             strokeWidth=.6).encode(
            x=alt.X('Shapley Value', axis=alt.Axis(title='Shapley Value', grid=True),
                    scale=alt.Scale(domain=axis_lims)),
            y=alt.Y('Feature:O',
                    sort=sort_features,
                    axis=alt.Axis(labelFontSize=fontsize, titleX=-51)),
            color=alt.Color('type',
                            scale=alt.Scale(domain=['Shapley Value', 'Mean'],
                                            range=["#618FE0", '#d76d58']),
                            legend=alt.Legend(title=None, fillColor="white",
                                              symbolStrokeWidth=0, symbolSize=50,
                                              orient="bottom-right")),
            opacity=alt.condition(alt.datum.type == 'Mean', alt.value(1.0),
                                  alt.value(0.1)),
            size=alt.condition(alt.datum.type == 'Mean', alt.value(70),
                               alt.value(30)),
        ).properties(
            width=width,
            height=height
        )
        return global_feats_plot

    return multi_plot_wrapper(feat_data, plot, (top_x_feats, threshold, plot_features, plot_parameters))
