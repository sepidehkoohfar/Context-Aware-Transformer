# coding=utf-8
# Copyright 2021 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3

from Utils import base, utils
from data.electricity import ElectricityFormatter
import pandas as pd

DataFormatter = ElectricityFormatter
DataTypes = base.DataTypes
InputTypes = base.InputTypes


class WatershedFormatter(DataFormatter):
    """Defines and formats data_set for the electricity dataset.
        Note that per-entity z-score normalization is used here, and is implemented
        across functions.
        Attributes:
        column_definition: Defines input and data_set type of column used in the
          experiment.
        identifiers: Entity identifiers used in experiments.
        """

    _column_definition = [
        ('id', DataTypes.REAL_VALUED, InputTypes.ID),
        ('hours_from_start', DataTypes.REAL_VALUED, InputTypes.TIME),
        ('Conductivity', DataTypes.REAL_VALUED, InputTypes.TARGET),
        ('TempC', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('Nitrate_mg', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('Q', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('pH', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('ODOPerCent', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('day_of_week', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('hour', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('hours_from_start', DataTypes.REAL_VALUED, InputTypes.KNOWN_INPUT),
        ('categorical_id', DataTypes.CATEGORICAL, InputTypes.STATIC_INPUT),
    ]

    def split_data(self, df, valid_boundary=1107, test_boundary=1607):
        """Splits data_set frame into training-validation-test data_set frames.
        This also calibrates scaling object, and transforms data_set for each split.
        Args:
          df: Source data_set frame to split.
          valid_boundary: Starting year for validation data_set
          test_boundary: Starting year for test data_set
        Returns:
          Tuple of transformed (train, valid, test) data_set.
        """

        print('Formatting train-valid-test splits.')

        index = df['days_from_start']
        train = df.loc[index < valid_boundary]
        valid = df.loc[(index >= valid_boundary - 7) & (index < test_boundary)]
        test = df.loc[index >= test_boundary - 7]

        self.set_scalers(train)

        return (self.transform_inputs(data) for data in [train, valid, test])

    def format_covariates(self, covariates):
        """Reverts any normalisation to give predictions in original scale.
        Args:
          predictions: Dataframe of model predictions.
        Returns:
          Data frame of unnormalised predictions.
        """

        if self._real_scalers is None:
            raise ValueError('Scalers have not been set!')

        column_names = covariates.columns

        df_list = []
        for identifier, sliced in covariates.groupby('identifier'):
            sliced_copy = sliced.copy()
            real_scalers = self._real_scalers[identifier]

            for i in range(48):
                df_inner_list = []
                inds = []
                for j in range(10):
                    ind = 48*j + i
                    inds.append(ind)
                    col = column_names[ind]
                    df_inner_list.append(sliced_copy[col])
                sliced_df = pd.concat(df_inner_list, axis=1)
                sliced_copy[column_names[inds]] = real_scalers.inverse_transform(sliced_df)

            df_list.append(sliced_copy)

        output = pd.concat(df_list, axis=0)

        return output

    def get_fixed_params(self):
        """Returns fixed model parameters for experiments."""

        fixed_params = {
            'total_time_steps': 9 * 24,
            'num_encoder_steps': 7 * 24,
            'num_epochs': 50,
            'early_stopping_patience': 5,
            'multiprocessing_workers': 5
        }

        return fixed_params

    def get_default_model_params(self):
        """Returns default optimised model parameters."""

        model_params = {
            'hidden_layer_size': [16, 32],
            'minibatch_size': [256],
            'num_heads': 8,
            'stack_size': [1],
        }

        return model_params

    def get_num_samples_for_calibration(self):
        """Gets the default number of training and validation samples.
        Use to sub-sample the data_set for network calibration and a value of -1 uses
        all available samples.
        Returns:
          Tuple of (training samples, validation samples)
        """
        return 128000, 16384