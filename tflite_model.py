# tflite_model.py
from kivy.utils import platform
import numpy as np
from PIL import Image, ImageOps

if platform == 'android':
    from jnius import autoclass, cast  # type: ignore

    File = autoclass('java.io.File')
    Interpreter = autoclass('org.tensorflow.lite.Interpreter')
    TensorBuffer = autoclass('org.tensorflow.lite.support.tensorbuffer.TensorBuffer')
    DataType = autoclass('org.tensorflow.lite.DataType')
    ByteBuffer = autoclass('java.nio.ByteBuffer')

    class TensorFlowModel:
        def __init__(self, model_path, num_threads=1, use_gpu=False):
            self.model_path = model_path
            self.num_threads = num_threads
            self.use_gpu = use_gpu
            self.interpreter = None
            self.input_shape = None
            self.output_shape = None
            self.output_type = None

        def load(self):
            model_file = File(self.model_path)
            self.interpreter = Interpreter(model_file)

            input_tensor = self.interpreter.getInputTensor(0)
            self.input_shape = list(input_tensor.shape())

            output_tensor = self.interpreter.getOutputTensor(0)
            self.output_shape = list(output_tensor.shape())
            self.output_type = output_tensor.dataType()

            self.interpreter.allocateTensors()

        def get_input_shape(self):
            return self.input_shape

        def pred(self, x):
            x = np.ascontiguousarray(x)
            input_buffer = ByteBuffer.wrap(x.tobytes())

            output_buffer = TensorBuffer.createFixedSize(
                self.output_shape, self.output_type
            )
            out_bb = output_buffer.getBuffer()
            out_bb.rewind()

            self.interpreter.run(input_buffer, out_bb)

            return np.array(output_buffer.getFloatArray()).reshape(self.output_shape)

else:
    from ai_edge_litert.interpreter import Interpreter  # type: ignore

    class TensorFlowModel:
        def __init__(self, model_path, num_threads=1, use_gpu=False):
            self.model_path = model_path
            self.interpreter = Interpreter(model_path=model_path)

        def load(self):
            self.interpreter.allocate_tensors()

        def get_input_shape(self):
            return self.interpreter.get_input_details()[0]['shape']

        def pred(self, x):
            in_det = self.interpreter.get_input_details()[0]
            if x.dtype != in_det['dtype']:
                x = x.astype(in_det['dtype'])

            self.interpreter.set_tensor(in_det['index'], x)
            self.interpreter.invoke()
            out = self.interpreter.get_tensor(
                self.interpreter.get_output_details()[0]['index']
            )
            return out