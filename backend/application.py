import os
from flask import Flask, jsonify, url_for, make_response, request
from flask_restful import Api, Resource, reqparse
from reflection import zoeppritz_rpp as rpp
import numpy as np
from numpy.linalg import lstsq as ls
from numpy.random import normal, uniform, randn, multivariate_normal
from AvoGMM import Rock
from scipy.signal import tukey, kaiser
from sklearn.decomposition import PCA

from numpy import histogram2d


import h5py
import numpy as np
np.random.seed(seed=10)


app = Flask(__name__)
api = Api(app)


files = {"reflection": 'reflection.hdf5',
         "migrated": 'seismic.hdf5',
         "poorly_processed": 'poor_process.hdf5'}
         
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




class Datasets(Resource):

    def get(self):

        return jsonify({"datasets":files.keys()})


    
class Features(Resource):

    def get(self, dataset):

        datafile = files[dataset]
        
        with h5py.File(datafile, 'r') as f:
    
            features = [key for key in f["features"].keys()
                        if key not in ["x", "z"]]

        return jsonify({"features":features})
    
        
class FeatureData(Resource):

    def get(self, dataset, feature):

        datafile = files[dataset]

        np.random.seed(seed=10)
    
        with h5py.File(datafile, 'r') as f:

            data = f["features"][feature][:]
            ind_data =  f["features"]["IG"][:]
            ind_data = ind_data * ind_data
            ind_data = np.sum(ind_data/np.amax(ind_data),1) < .02
     
            points = ind_data.size /1.5
            # subsample the small points
            small_ind = np.random.choice(np.where(ind_data)[0],
                                         points, replace=False)
            all_ind = set(np.arange(data.shape[0]))
            ind = list(all_ind - set(small_ind))
      
            data = data[ind, :]

        xmin, ymin = np.amin(data, 0)
        xmax, ymax = np.amax(data, 0)
        
        xy = array2dict(data)

        return jsonify({'data': xy,
                        'xmin': float(xmin),
                        'ymin': float(ymin),
                        'xmax': float(xmax),
                        'ymax': float(ymax)})

class ImageData(Resource):

    def get(self, dataset):

        datafile = files[dataset]
        
        with h5py.File(datafile, 'r') as f:

            # zero offset reflectivity
            ref = np.abs(np.sum(f["adcig"]["data"],2))
            #ref = ref.reshape(f["reflection"].attrs.get("shape"))

        return jsonify({
            "max": float(np.amax(ref)),
            "min": float(np.amin(ref)),
            "data": ref[:,:].T.tolist()})

class MaskData(Resource):

    def post(self, dataset, features):

        x1,x2,y1,y2 = [np.float(i) for i in request.get_json()["bounds"]]
        datafile = files[dataset]
        with h5py.File(datafile, 'r') as f:

            shape = f["reflection"].attrs["shape"]
            data = f["features"][features][:]
            feat1 = data[:,0]
            feat2 = data[:,1]

            
            index = np.where(np.logical_and(np.logical_and(feat1 > x1, feat1 < x2),
                                            np.logical_and(feat2 > y1, feat2 < y2)))[0]
            
            xfeat = f["features"]["x"][:][index]
            zfeat = f["features"]["z"][:][index]
            xref = f["reflection"]["x"][:]
            zref = f["reflection"]["z"][:]


        mask = np.zeros(np.prod(shape))

        for x,z in zip(xfeat.tolist(), zfeat.tolist()):
            mask[np.where(np.logical_and(xref == x, zref == z))[0]] = 1.0


        return jsonify({"data": mask.reshape(shape).T.tolist()})



class PCADemo(Resource):

    def get(self):
    
        ff = float(request.args.get('fudge_factor', 0.0))

        np.random.seed(10)

        vp_av = 2900.0
        shale = Rock(3240, 1620, 2340, 50.,50.,50.)
        brineSand = Rock(2590, 1060, 2210, 200., 200., 200.)
        gasSand = Rock(2540, 1620, 2090, 20., 20., 20.)

        theta = np.arange(0,30)
        ref = np.zeros((100,theta.size))


        M1 = .05 * ff
        M2 =2*ff

        for i in range(25):
    
            tuk1 = tukey(theta.size, alpha=M1)
            tuk2 = tukey(theta.size, alpha=M2)
            tuk  = np.concatenate([tuk1[:tuk1.size/2], tuk2[tuk2.size/2:]])
            vp1, vs1, rho1 = shale.sample()
            vp2, vs2, rho2 = brineSand.sample()
            ref[i, :] = rpp(vp2, vs2, rho2, vp1, vs1, rho1, theta) * tuk

        M1 = .4 * ff
        M2 = 5*ff
        for i in np.arange(25,50):
            tuk1 = tukey(theta.size, alpha=M1)
            tuk2 = tukey(theta.size, alpha=M2)
            tuk  = np.concatenate([tuk1[:tuk1.size/2], tuk2[tuk2.size/2:]])
            vp1, vs1, rho1 = brineSand.sample()
            vp2, vs2, rho2 = shale.sample()
            ref[i, :] = rpp(vp2, vs2, rho2, vp1, vs1, rho1, theta) * tuk
        
        M1 = .1 * ff
        M2 = 1.5*ff

        for i in np.arange(50, 75):
            vp1, vs1, rho1 = shale.sample()
            vp2, vs2, rho2 = gasSand.sample()
        
            tuk1 = tukey(theta.size, alpha=M1)
            tuk2 = tukey(theta.size, alpha=M2)
            tuk  = np.concatenate([tuk1[:tuk1.size/2], tuk2[tuk2.size/2:]])
            ref[i, :] = rpp(vp2, vs2, rho2, vp1, vs1, rho1, theta) * tuk

            
        M1 = 0.1 * ff
        M2 = 3*ff
        for i in np.arange(75,100):
            vp1, vs1, rho1 = gasSand.sample()
            vp2, vs2, rho2 = shale.sample()
        
            tuk1 = tukey(theta.size, alpha=M1)
            tuk2 = tukey(theta.size, alpha=M2)
            tuk  = np.concatenate([tuk1[:tuk1.size/2], tuk2[tuk2.size/2:]])
            ref[i, :] = rpp(vp2, vs2, rho2, vp1, vs1, rho1, theta) * tuk
    
        ref = np.nan_to_num(ref)

        I = np.kron(np.eye(100), np.ones((theta.size,1)))
        S = np.kron(np.eye(100), np.sin(theta * np.pi/180).reshape(theta.size, 1))
        shuey = np.hstack([I,S])

        d = ref.flatten()
        ig, res, rank, s = ls(shuey, d)

        ig_new = np.zeros((100,2))
        ig_new[:,0] = ig[:100]
        ig_new[:,1] = ig[100:]

        pca = PCA(n_components=2)
        comp = pca.fit_transform(ref)

        coefs = pca.components_

        if np.mean(coefs[0,:]) < 0:
            coefs[0,:] *= -1
            comp[:,0] *=-1
        
        if coefs[1,15] < 0:
            coefs[1,:] *= -1
            comp[:,1] *=-1
            
        i = np.ones(theta.size) * .5
        g = np.sin(theta * np.pi / 180.0)**2
        shuey_i = np.zeros((theta.size,2))
        shuey_i[:,0] = theta
        shuey_i[:,1] = i*.5

        shuey_g = np.zeros((theta.size,2))
        shuey_g[:,0] = theta
        shuey_g[:,1] = g

        c1 = np.zeros((theta.size,2))
        c1[:,0] = theta
        c1[:,1] = coefs[0, :]
        
        c2 = np.zeros((theta.size,2))
        c2[:,0] = theta
        c2[:,1] = coefs[1, :]

        curves = [array2dict(zip(theta, curve)) for curve in ref]

        # payload
        payload = {"ig": array2dict(ig_new),
                   "pc": array2dict(comp),
                   "pc_ylim": float(np.amax(np.abs(comp[:,1]))),
                   "pc_xlim": float(np.amax(np.abs(comp[:,0]))),
                   "ig_ylim": float(np.amax(np.abs(ig_new[:,1]))),
                   "ig_xlim": float(np.amax(np.abs(ig_new[:,0]))),
                    "i": array2dict(shuey_i),
                    "g": array2dict(shuey_g),
                    "c1": array2dict(c1),
                    "c2": array2dict(c2),
                    "curves": curves
                  }
            
        return jsonify(payload)
        
api.add_resource(FeatureData, '/feature_data/<string:dataset>/<string:feature>',
                 endpoint='feature_data')
api.add_resource(ImageData, '/image_data/<string:dataset>',
                 endpoint='image_data')
api.add_resource(PCADemo, '/pca_demo', endpoint='pca_demo')
api.add_resource(MaskData, '/mask_data/<string:dataset>/<string:features>',
                 endpoint='mask_data')
api.add_resource(Features, '/features/<string:dataset>', endpoint='/features')
api.add_resource(Datasets, '/datasets', endpoint='/datasets')

if __name__ == '__main__':
    
    app.run(debug=True)
