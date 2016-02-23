from flask import Flask, jsonify, url_for, make_response, request
from flask.ext.restful import Api, Resource, reqparse
import h5py
import numpy as np
app = Flask(__name__)
api = Api(app)

def array2dict(data):

    return [{'x': float(x), 'y': float(y)} for x, y in data]


# for CORS (cross origin)
@app.after_request
def after_request(response):
    
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers',
                         'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods',
                         'GET,PUT,POST,DELETE')

    return response


class Options(Resource):

    def get(self):
        
        with h5py.File('exp2.hdf5', 'r') as f:
    
            features = [key for key in f["features"].keys()
                        if key not in ["x", "z"]]

        return jsonify({"features": features})

        
class FeatureData(Resource):

    def get(self, feature):

        with h5py.File('exp2.hdf5', 'r') as f:

            data = f["features"][feature][:]

        xmin, ymin = np.amin(data, 0)
        xmax, ymax = np.amax(data, 0)
        
        xy = array2dict(data)

        return jsonify({'data': xy,
                        'xmin': float(xmin),
                        'ymin': float(ymin),
                        'xmax':float(xmax),
                        'ymax': float(ymax)})

class ImageData(Resource):

    def get(self):

        with h5py.File('exp2.hdf5', 'r') as f:

            # zero offset reflectivity
            ref = np.abs(f["reflection"]["rpp"][:,0])
            ref = ref.reshape(f["reflection"].attrs.get("shape"))

        return jsonify({
            "max": float(np.amax(ref)),
            "min": float(np.amin(ref)),
            "data": ref[:,:].T.tolist()})

class MaskData(Resource):

    def post(self):

        index = request.get_json()["index"]
        with h5py.File('exp2.hdf5', 'r') as f:

            shape = f["reflection"].attrs["shape"]
            xfeat = f["features"]["x"][index]
            zfeat = f["features"]["z"][index]
            xref = f["reflection"]["x"][:]
            zref = f["reflection"]["z"][:]


        mask = np.zeros(np.prod(shape))

        for x,z in zip(xfeat.tolist(), zfeat.tolist()):
            mask[np.where(np.logical_and(xref == x, zref == z))[0]] = 1.0


        return jsonify({"data": mask.reshape(shape).T.tolist()})


api.add_resource(FeatureData, '/feature_data/<string:feature>',
                 endpoint='feature_data')
api.add_resource(ImageData, '/image_data',
                 endpoint='image_data')
api.add_resource(MaskData, '/mask_data', endpoint='mask_data')
api.add_resource(Options, '/options',
                 endpoint='options')

if __name__ == '__main__':
    
    app.run(debug=True)
