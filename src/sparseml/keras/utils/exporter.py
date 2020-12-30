"""
Export Keras models to the local device.
"""

from typing import List, Any
import os
import onnx
from tensorflow.keras import Model

from sparseml.utils import (
    create_parent_dirs,
    clean_path,
    tensors_export,
)

try:
    import keras2onnx

    keras2onnx_import_error = None
except Exception as keras2onnx_error:
    keras2onnx_import_error = keras2onnx_error


__all__ = ["ModelExporter"]


DEFAULT_ONNX_OPSET = 11


class ModelExporter(object):
    """
    An exporter for exporting Keras models into ONNX format
    as well as numpy arrays for the input and output tensors.

    :param model: the module to export
    :param output_dir: the directory to export the module and extras to
    """

    def __init__(
        self, model: Model, output_dir: str,
    ):
        self._model = model
        self._output_dir = clean_path(output_dir)

    def export_onnx(
        self,
        name: str = "model.onnx",
        opset: int = DEFAULT_ONNX_OPSET,
        doc_string: str = "",
    ):
        """
        Export an ONNX file for the current model.

        :param name: name of the onnx file to save
        :param opset: onnx opset to use for exported model. Default is 11
        :param doc_string: optional doc string for exported ONNX model
        """
        if keras2onnx_import_error is not None:
            raise keras2onnx_import_error

        model_name = self._model.name or name.split(".onnx")[0]
        onnx_model = keras2onnx.convert_keras(
            self._model, name=model_name, target_opset=opset, doc_string=doc_string
        )

        onnx_path = os.path.join(self._output_dir, name)
        create_parent_dirs(onnx_path)
        onnx.save(onnx_model, onnx_path)

    def export_keras(self):
        """
        Export the model Keras files to the output_dir/keras directory
        """
        keras_path = os.path.join(self._output_dir, "keras")
        self._save_keras(keras_path)

    def export_h5(self, name: str = "model.h5"):
        """
        Export the Keras model as a single HDF5 file in the output_dir/keras
        directory

        :param name: name to export file with. default is model.h5
        """
        if not name.endswith(".h5"):
            name += ".h5"
        h5_path = os.path.join(self._output_dir, "keras", name)
        self._save_keras(h5_path)

    def _save_keras(self, file_path: str):
        create_parent_dirs(file_path)
        self._model.save(file_path)

    def export_samples(
        self,
        sample_batches: List[Any],
        sample_labels: List[Any] = None,
        exp_counter: int = 0,
    ):
        """
        Export a set list of sample batches as inputs and outputs through the model.

        :param sample_batches: a list of the sample batches to feed through the module
            for saving inputs and outputs
        :param sample_labels: an optional list of sample labels that correspond to the
            the batches for saving
        :param exp_counter: the counter to start exporting the tensor files at
        """
        inputs_dir = os.path.join(self._output_dir, "_sample-inputs")
        outputs_dir = os.path.join(self._output_dir, "_sample-outputs")
        labels_dir = os.path.join(self._output_dir, "_sample-labels")

        for batch, lab in zip(
            sample_batches,
            sample_labels if sample_labels else [None for _ in sample_batches],
        ):
            out = self._model.predict(batch)

            exported_input = tensors_export(
                batch,
                inputs_dir,
                name_prefix="inp",
                counter=exp_counter,
                break_batch=True,
            )
            if isinstance(out, dict):
                new_out = []
                for key in out:
                    new_out.append(out[key])
                out = new_out
            exported_output = tensors_export(
                out,
                outputs_dir,
                name_prefix="out",
                counter=exp_counter,
                break_batch=True,
            )

            if lab is not None:
                exported_label = tensors_export(
                    lab, labels_dir, "lab", counter=exp_counter, break_batch=True
                )

            assert len(exported_input) == len(exported_output)
            exp_counter += len(exported_input)