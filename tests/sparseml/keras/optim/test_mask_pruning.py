# Copyright (c) 2021 - present / Neuralmagic, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pytest
import tensorflow as tf

from sparseml.keras.optim import MaskedLayer, UnstructuredPruningMaskCreator
from tests.sparseml.keras.optim.mock import DenseLayerCreator, MockPruningScheduler


@pytest.mark.parametrize(
    "layer_lambda, pruning_scheduler, mask_creator, expected_mask",
    [
        (
            # Weight of a dense layer of shape (3, 4)
            DenseLayerCreator(
                "dense",
                np.array(
                    [[0.9, 0.1, 0.2, 0.5], [0.3, 0.5, 0.8, 0.9], [0.4, 0.6, 0.7, 0.9]]
                ),
            ),
            MockPruningScheduler([(1, 0.25), (2, 0.5)]),
            UnstructuredPruningMaskCreator(),
            # List of expected mask, each corresponding to one of the
            # above update step in the MockPruningScheduler
            [
                # Expected mask at time step 1, 25% sparsity
                np.array(
                    [
                        [1, 0, 0, 1],
                        [0, 1, 1, 1],
                        [1, 1, 1, 1],
                    ]
                ),
                # Expected mask at time step 2, 50% sparsity
                np.array(
                    [
                        [1, 0, 0, 0],
                        [0, 0, 1, 1],
                        [0, 1, 1, 1],
                    ]
                ),
            ],
        )
    ],
)
def test_mask_update_explicit(
    layer_lambda, pruning_scheduler, mask_creator, expected_mask
):
    if tf.__version__ < "2":
        pytest.skip("Test needs to be fixed to run with tensorflow_v1 1.x")
    layer = layer_lambda()
    masked_layer = MaskedLayer(layer, pruning_scheduler, mask_creator)
    update_steps = list(pruning_scheduler.step_and_sparsity_pairs.keys())
    for idx, update_step in enumerate(update_steps):
        tf.keras.backend.batch_set_value([(masked_layer.global_step, update_step)])
        masked_layer.mask_updater.conditional_update(training=True)
        mask = tf.keras.backend.get_value(masked_layer.masks[0])
        assert np.allclose(mask, expected_mask[idx])
