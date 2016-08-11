import numpy as np
from sklearn import cluster

from sklearn.utils.extmath import logsumexp
from sklearn.base import BaseEstimator
from scipy.interpolate import interp2d

from scipy.stats import multivariate_normal
from numpy.random import multivariate_normal as multivariate_sample

from bruges.reflection import zoeppritz_rpp as rpp

EPS = np.finfo(float).eps
from scipy import linalg

def IG(g,m,c,vp_av,dvp):
    I = .5*(dvp/vp_av)*(1 + g)
    G = (I/(1+g))*(1 - 4*((vp_av-c)/(vp_av*m))*((2./m)+ g*(vp_av-c)/(vp_av*m)))
        
    return I,G

def ava(upperRock, lowerRock, theta):
    
    return rpp(lowerRock[0], lowerRock[1], lowerRock[2],
               upperRock[0], upperRock[1], upperRock[2],
               theta)
    
def shueyIG(upperRock, lowerRock):
    
    vp1,vs1,rho1 = upperRock.sample()
    vp2,vs2,rho2 = lowerRock.sample()
    
    dvp = vp2-vp1
    dvs = vs2-vs1
    drho = rho2-rho1
    
    vpav = (vp1+vp2)/2.0
    vsav = (vs1+vs2)/2.0
    rhoav = (rho1 + rho2)/2.0
    
    I = (1/2.0)*((dvp/vpav) + (drho/rhoav))
    G = (1./2.)*(dvp/vpav) - 2*((vsav/vpav)**2)*((2*dvs/vsav)+(drho/rhoav))
    
    return I,G

class Rock:
    def __init__(self,vp, vs, rho, vp_std=100, vs_std=100, rho_std=100):
        
        self.vp = vp
        self.vs = vs
        self.rho = rho
        self.vp_std = vp_std
        self.vs_std = vs_std
        self.rho_std = rho_std
    
    def sample(self):
         
        cov = np.array([[self.vp_std**2,.2,.2],[.2,self.vs_std**2,.2],[.2,.2,self.rho_std**2]])
        
        return multivariate_sample([self.vp, self.vs, self.rho], cov)
    
class mudLine:
    
    def __init__(self, c=1360.0, g=.25, m=1.16, vp=3000, 
                 c_sig=136., g_sig=0.025, m_sig=.116, 
                 vp_sig=1000.0, dvp_sig=1000.0, n=100000):
        
        self.c = c
        self.g = g
        self.m = m
        self.vp = vp
        
        self.c_sig = c_sig
        self.g_sig = g_sig
        self.m_sig = m_sig
        self.vp_sig = vp_sig
        self.dvp_sig = dvp_sig

        self.n = n

        self.distribution_(n)
        
    
  
    def get_vp(self):
        return self.vp + np.random.uniform()*self.vp_sig
    
   
    def get_g(self):
        return self.g + np.random.randn()*self.g_sig
    
   
    def get_m(self):
        return self.m + np.random.randn()*self.m_sig
    
  
    def get_c(self):
        return self.c + np.random.randn()*self.c_sig
    
   
    def get_dvp(self):
        return np.random.uniform(-self.dvp_sig,self.dvp_sig)
    
        
    def sample(self,vp_av, dvp):
        """ 
        Returns a sample from the distribution
        given corresponding to vp_av and dvp
        """
        
        dvp = float(dvp)
        vp_av = float(vp_av)
        g = self.get_g()
        m = self.get_m()
        c = self.get_c()
        
       
        I,G = IG(g,m,c,vp_av, dvp)
        
        return I,G
    

    def set_pdf(self, X):
        """
        Likelihood of measuring I and G in given the montecarlo distribution
        """

        x = self.Iedges
        y = self.Gedges
        
        z = self.P
        f = interp2d(x, y, z, 'linear') 

        # interpolate requires one value at a time or sorted values :(
        pdf = np.apply_along_axis(lambda x: f(x[0],x[1]),1,X)

        self.pdf = pdf.ravel()


       
    def distribution_(self, n):
        """
        param n: The number of distribution points to generate
        
        Returns the entire monte carlo generated distribution.
        """
        
        I = np.zeros(n)
        G = np.zeros(n)
        
        for i in range(n):
            dvp = self.get_dvp() 
            vp_av = self.get_vp()
            g = self.get_g()
            m = self.get_m()
            c = self.get_c()
        
            I[i], G[i] = IG(g,m,c,vp_av, dvp)
            
   

        H, xedges, yedges = np.histogram2d(G, I, bins=50,
                                           range=[[-1,1],[-1,1]])

        binsize  = np.diff(xedges)*np.diff(yedges)

        # normalize by the bin width to get a pdf.
        H /= (n*binsize)

        

        self.P = H + EPS
        self.Iedges = (xedges[:-1] + xedges[1:])/2.0
        self.Gedges = (yedges[:-1] + yedges[1:])/2.0
        self.binsize = binsize[0]
        

    @property
    def mudline(self):

        dvp = self.get_dvp() 
        vp_av = self.get_vp()
        g = self.get_g()
        m = self.get_m()
        c = self.get_c()

        def G(I):
            return (I/(1+g)) * (1 - 4*((vp_av-c)/(vp_av*m))*((2./m) +
                                g*(vp_av-c)/(vp_av*m)))
        return G
        

        
class AvoGMM(BaseEstimator):
    """
    Fits a AVO crossplot data using a mixing model of gaussians and
    AVO distribution function.

    Parameters
    ----------
    n_gaussians: int, optional
        Number of gaussian processes to mix

    n_iter: int, optional
        Number of iterations to perform in each initialization.

    n_init: int, optional
        Number of reinitializations of the algorithm.
    """
    
    def __init__(self, avoDist, n_gaussians=1, n_iter=100, n_init=1,
                 tol=1e-3,min_covar=1e-3, verbose=False, bias=None):

        self.n_gaussians = n_gaussians
        self.n_iter = n_iter
        self.n_init = n_init

        self.weights_ = np.ones(n_gaussians + 1)/(n_gaussians + 1)

        self.avoDist = avoDist

        self.tol = tol

        self.verbose = verbose
        self.min_covar = min_covar
        self.bias = bias
        self.random_state = None

        if bias is None:
            self.bias = np.ones(self.weights_.size)
        

    def init_components(self, X):
        """
        Uses k-means to initialize the cluster parameters
        """
        
        # Use k-means to initialize the data
        n_components = self.n_gaussians + 1

        if not hasattr(self, 'means_'):
            self.means_ = cluster.KMeans(
            n_clusters=self.n_gaussians,
                random_state=self.random_state).fit(X).cluster_centers_
    
        if not hasattr(self, 'weights_'):
            np.tile(1.0 / n_components, n_components)

        if not hasattr(self, 'covars_'):

            # Covariance matrix
            cv = np.cov(X.T) + self.min_covar*np.eye(X.shape[1])
            self.covars_ = np.tile(cv, (self.n_gaussians, 1, 1))


    def fit(self, X):

        self._fit(X)
        return self

    def fit_predict(self, X):

        pdf = self._fit(X)
        return pdf.argmax(axis=1)
    
    def _fit(self, X):

        # The avo pdf is constant
        self.avoDist.set_pdf(X)

        max_log_prob = -np.infty
        
        for init in range(self.n_init):

            self.init_components(X)
    
            current_log_likelihood = None
            
            # reset self.converged_ to False
            self.converged_ = False

            for i in range(self.n_iter):

                prev_log_likelihood = current_log_likelihood

                # Get the pdfs for the current iteration
                multivariate_pdfs = _step_pdf(X, self.means_,
                                              self.covars_, self.avoDist)


                # Get the a posteriori p(k|X,theta)
                pk_xt = _step_aposteriori(self.weights_, multivariate_pdfs)

                # Update the weights (alpha)
                self.weights_ = _alpha_mstep(pk_xt, self.bias)

                # Update the means (ignore the last dimension of the dist)
                self.means_ = _mu_mstep(X, pk_xt[:,:-1])

                # Update the covariances
                self.covars_ = _covar_mstep(X, pk_xt[:,:-1], self.means_)

                # Get the new pdfs
                new_pdfs = _step_pdf(X, self.means_, self.covars_,
                                    self.avoDist)

                # Update the log likelihood
                current_log_likelihood = _step_log_likelihood(
                    self.weights_, pk_xt, new_pdfs)
                    
                if prev_log_likelihood is not None:
                    change = abs(current_log_likelihood - prev_log_likelihood)
                    if self.verbose > 1:
                        print('\t\tChange: ' + str(change))
                    if change < self.tol:
                        self.converged_ = True
                        if self.verbose > 0:
                            print('\t\tEM algorithm converged.')
                        break

                if current_log_likelihood > max_log_prob:
                    
                    max_log_prob = current_log_likelihood
                    best_params = {'weights': self.weights_,
                                   'means': self.means_,
                                   'covars': self.covars_}
                    if self.verbose > 1:
                        print('\tBetter parameters were found.')

        self.covars_ = best_params['covars']
        self.means_ = best_params['means']
        self.weights_ = best_params['weights']

        

        return new_pdfs
        
                
def _step_pdf(X, means, covars, dist):
    """
    Calculates the pdfs for the input array and current parameter estimates.

    Input
    ------
    X: array(n_samples, n_features)
       Input data
    means: array(n_gaussian)
           The means of each gaussian cluster
    covariance: array(n_gaussian, n_features, n_features)
           Co-variance matrices for each gaussian cluster
    dist: Additional distribution independent of the means and covariances.
          ie. A monte Carlo sampled distribution

    Output:
    
    p(X|theta): array(n_samples, n_clusters)
    """

    pdfs = [multivariate_normal(mean, covar).pdf(X) for mean, covar in
                   zip(means,covars)]

    pdfs.append(dist.pdf)
    
    # cast into a np array
    return np.array(pdfs).T
    


    

    
def _step_aposteriori(alpha, pdf):
    """
    Calculates the a posterior for an EM step
    p(l|x_t,theta) = alpha * p(x_t|theta)/sum_k(alpha_k*p(x_t|theta_k))

    Parameters
    ----------
    alpha: array(n_clusters)
           The apriori weighting of each cluster
    pdf: array(n_samples, n_clusters)
         The likelihoods of each sample.

    Returns
    -------
    p(k|x, theta) array(n_samples, n_clusters) The a posteriori distribution.
    
    """

    # sum(alpha_i*p(x_t|mu_i,sig_i))
    normalizer = np.dot(pdf,alpha.T)

    # alpha_i*p(xt|mu_i, sig_i)
    numerator = alpha * pdf

    # p(k|xi, theta_g)
    p_t = (numerator.T / normalizer.T).T

    return p_t



def _alpha_mstep(p_k, bias):
    """
    Calculates the alpha term maximization for the update

    alpha_k = 1/N sum_t(p(k,|x_t, theta)

    Input
    -----
    p_k: array(nsamples, n_clusters)
          The a posteriori distribution p(k|x, theta)

    Output
    ------
    alpha_new: array(n_clusters)
               The updated cluster weightings
    """

    alphas = np.mean(p_k,0)
    alphas *= bias
    alphas /= np.sum(alphas)

    return alphas

    
def _mu_mstep(X, p_k):
    """
    Calculates the mean update for each cluster.

    mu_new = sum_t(Xt*p(l|x_t,theta))/sum_t(p(l|x_t,theta))

    Inputs
    ---------
    p_k: array(nsamples, n_clusters)
          The a posteriori distribution p(k|x, theta)
    X: array(n_samples, n_features)
       Data array

    Returns
    --------
    mu_new: array(n_gaussians)
            The new mu estimates for the gaussian mixtures
    """

    return (np.dot(X.T, p_k) / np.sum(p_k,0)).T




def _covar_mstep(X, p_k, mu_new):
    """
    Calculates the new covariances matrices for the next step.
    sig_new_k = sum_t(p_k*(xt-mu_new)(xt-mu_new).T)/sum_t(p_k)

    Inputs
    ---------
    p_k: array(nsamples, n_clusters)

            The a posteriori distribution p(k|x, theta)
    X: array(n_samples, n_features)
        Data array

    mu_new: array(n_clusters)
        Updated means for each cluster.

    Outputs
    ---------
    covars: array(n_clusters, n_features, n_features)
    """

    n_gaussians = p_k.shape[1]
    n_features = mu_new.shape[1]
    
    cv = np.empty((n_gaussians, n_features, n_features))

    for i, mu in enumerate(mu_new):

        post = p_k[:,i]
        diff = X - mu

        cv[i] = np.dot(post*diff.T, diff) / (post.sum() + EPS)

    return cv
        

def _step_log_likelihood(alpha_new, p_k, pX_new):
    """
    Calculates the new maximum likelihood

    """

    alpha_term = np.sum(np.dot(np.log(alpha_new+EPS), p_k.T).T,0)
    theta_term = np.sum(np.log(pX_new + EPS)*p_k)

    return alpha_term + theta_term

def _step_log_likelihood_test():

    covars, mu, alphas, p_k, X, dist = _covar_mstep_test()

    new_pdf = _step_pdf(X, mu, covars, dist)

    return _step_log_likelihood(alphas, p_k, new_pdf)

def _step_pdf_test():

    X = np.random.randn(1000,2)

    means = [[.5,-.5],[1.5,2],[1.,2],[.5,.2]]
    cv = np.cov(X.T) + np.eye(X.shape[1])
    covars = np.tile(cv, (4, 1,1))

    dist = mudLine(c=1360.0, g=.25, m=1.16,vp=3000, 
                c_sig=136.,g_sig=0.025,m_sig=.116, 
                vp_sig=1000.0, dvp_sig=1000.0)

    dist.set_pdf(X)
    
    return _step_pdf(X, means, covars, dist), X, dist

def _step_aposteriori_test():

    pdf, X, dist = _step_pdf_test()

    alphas = np.ones(pdf.shape[1])/pdf.shape[1]

    return _step_aposteriori(alphas, pdf), alphas, X, dist

def _alpha_mstep_test():

    p_k, alphas, X, dist = _step_aposteriori_test()

    return _alpha_mstep(p_k), p_k, X, dist

def _mu_mstep_test():

    # ignore the last pdf as it is constant
    alphas,p_k,  X, dist = _alpha_mstep_test()

    return _mu_mstep(X,p_k[:,:-1]), alphas, p_k,X, dist

def _covar_mstep_test():

    mu, alphas, p_k, X, dist = _mu_mstep_test()

    return _covar_mstep(X, p_k[:,:-1], mu), mu, alphas, p_k, X, dist
