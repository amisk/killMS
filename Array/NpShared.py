#!/usr/bin/env python
"""
killMS, a package for calibration in radio interferometry.
Copyright (C) 2013-2017  Cyril Tasse, l'Observatoire de Paris,
SKA South Africa, Rhodes University

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
#import sharedarray.SharedArray as SharedArray
import SharedArray
from killMS.Other import ModColor
import numpy as np
from killMS.Other import MyLogger
log=MyLogger.getLogger("NpShared")
from killMS.Other import ClassTimeIt


def zeros(*args,**kwargs):
    return SharedArray.create(*args,**kwargs)
    
def ToShared(Name,A):

    try:
        a=SharedArray.create(Name,A.shape,dtype=A.dtype)
    except:
        print>>log, ModColor.Str("File %s exists, delete it..."%Name)
        DelArray(Name)
        a=SharedArray.create(Name,A.shape,dtype=A.dtype)

    a[:]=A[:]
    return a

def DelArray(Name):
    try:
        SharedArray.delete(Name)
    except:
        pass

def ListNames():
    
    T=ClassTimeIt.ClassTimeIt("   SharedToDico")
    
    ll=list(SharedArray.list())
    return [AR.name for AR in ll]
    
def DelAll(key=None):
    ll=ListNames()
    for name in ll:
        if key!=None:
            if key in name: DelArray(name)
        else:
            DelArray(name)

def GiveArray(Name):
    try:
        return SharedArray.attach(Name)
    except:
        return None


def DicoToShared(Prefix,Dico,DelInput=False):
    DicoOut={}
    print>>log, ModColor.Str("DicoToShared: start [prefix = %s]"%Prefix)
    for key in Dico.keys():
        if type(Dico[key])!=np.ndarray: continue
        #print "%s.%s"%(Prefix,key)
        ThisKeyPrefix="%s.%s"%(Prefix,key)
        print>>log, ModColor.Str("  %s -> %s"%(key,ThisKeyPrefix))
        ar=Dico[key]
        Shared=ToShared(ThisKeyPrefix,ar)
        #T.timeit("getarray %s"%ThisKeyPrefix)
        DicoOut[key]=Shared
        if DelInput:
            del(Dico[key],ar)
            
    if DelInput:
        del(Dico)
    print>>log, ModColor.Str("DicoToShared: done")

    return DicoOut


def SharedToDico(Prefix):
    print>>log, ModColor.Str("SharedToDico: start [prefix = %s]"%Prefix)
    T=ClassTimeIt.ClassTimeIt("   SharedToDico")
    T.disable()
    Lnames=ListNames()
    T.timeit("0: ListNames")
    keys=[Name for Name in Lnames if Prefix in Name]
    if len(keys)==0: return None
    DicoOut={}
    T.timeit("1")
    for Sharedkey in keys:
        key=Sharedkey.split(".")[-1]
        print>>log, ModColor.Str("  %s -> %s"%(Sharedkey,key))
        Shared=GiveArray(Sharedkey)
        DicoOut[key]=Shared
    T.timeit("2a")
    print>>log, ModColor.Str("SharedToDico: done")


    return DicoOut

class SharedDicoDescriptor():
    def __init__(self,prefixName,Dico):
        self.prefixName=prefixName
        self.DicoKeys=Dico.keys()


def SharedObjectToDico(SObject):
    if SObject==None: return None
    Prefix=SObject.prefixName
    Fields=SObject.DicoKeys
    print>>log, ModColor.Str("SharedToDico: start [prefix = %s]"%Prefix)
    T=ClassTimeIt.ClassTimeIt("   SharedToDico")
    T.disable()

    DicoOut={}
    T.timeit("1")
    for field in Fields:
        Sharedkey="%s.%s"%(Prefix,field)
        #print>>log, ModColor.Str("  %s -> %s"%(Sharedkey,key))
        Shared=GiveArray(Sharedkey)
        DicoOut[field]=Shared
    T.timeit("2a")
    print>>log, ModColor.Str("SharedToDico: done")


    return DicoOut


#########################

def PackListArray(Name,LArray):
    DelArray(Name)

    NArray=len(LArray)
    ListNDim=[len(LArray[i].shape) for i in range(len(LArray))]
    NDimTot=np.sum(ListNDim)
    # [NArray,NDim0...NDimN,shape0...shapeN,Arr0...ArrN]

    dS=LArray[0].dtype
    TotSize=0
    for i in range(NArray):
        TotSize+=LArray[i].size


    S=SharedArray.create(Name,(1+NArray+NDimTot+TotSize,),dtype=dS)
    S[0]=NArray
    idx=1
    # write ndims
    for i in range(NArray):
        S[idx]=ListNDim[i]
        idx+=1

    # write shapes
    for i in range(NArray):
        ndim=ListNDim[i]
        A=LArray[i]
        S[idx:idx+ndim]=A.shape
        idx+=ndim

    # write arrays
    for i in range(NArray):
        A=LArray[i]
        S[idx:idx+A.size]=A.ravel()
        idx+=A.size


def UnPackListArray(Name):
    S=GiveArray(Name)

    NArray=np.int32(S[0].real)
    idx=1

    # read ndims
    ListNDim=[]
    for i in range(NArray):
        ListNDim.append(np.int32(S[idx].real))
        idx+=1

    # read shapes
    ListShapes=[]
    for i in range(NArray):
        ndim=ListNDim[i]
        shape=np.int32(S[idx:idx+ndim].real)
        ListShapes.append(shape)
        idx+=ndim

    # read values
    ListArray=[]
    for i in range(NArray):
        shape=ListShapes[i]
        size=np.prod(shape)
        A=S[idx:idx+size].reshape(shape)
        ListArray.append(A)
        idx+=size
    return ListArray

