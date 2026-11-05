import numpy as np
# EPSG:3035 ETRS89-LAEA (GRS80), Snyder (1987) ellipsoidal formulas
a=6378137.0; f=1/298.257222101; e2=2*f-f*f; e=np.sqrt(e2)
lat0=np.radians(52.0); lon0=np.radians(10.0); X0=4321000.0; Y0=3210000.0
def q(phi):
    s=np.sin(phi)
    return (1-e2)*(s/(1-e2*s*s) - (1/(2*e))*np.log((1-e*s)/(1+e*s)))
qp=q(np.pi/2); Rq=a*np.sqrt(qp/2)
b1=np.arcsin(q(lat0)/qp)
D=a*(np.cos(lat0)/np.sqrt(1-e2*np.sin(lat0)**2))/(Rq*np.cos(b1))
def fwd(lon,lat):
    lon=np.radians(lon); lat=np.radians(lat)
    beta=np.arcsin(q(lat)/qp)
    B=Rq*np.sqrt(2/(1+np.sin(b1)*np.sin(beta)+np.cos(b1)*np.cos(beta)*np.cos(lon-lon0)))
    x=B*D*np.cos(beta)*np.sin(lon-lon0)
    y=(B/D)*(np.cos(b1)*np.sin(beta)-np.sin(b1)*np.cos(beta)*np.cos(lon-lon0))
    return X0+x, Y0+y   # (E, N)
